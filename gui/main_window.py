"""
gui/main_window.py — Root QMainWindow.

Unified audio pipeline (no Vosk):
  MicStream → shared queue → VadManager thread
    ↓ utterance captured
  Route by current state:
    IDLE     → Groq Whisper → check wake phrase → LISTENING
    LISTENING → Groq Whisper → validate → intent → LLM/action → TTS
"""

from __future__ import annotations
from pathlib import Path
from queue import Queue, Empty
from threading import Thread, Timer

from PySide6.QtCore import Qt, Slot, Signal, QObject
from PySide6.QtGui import QFont, QFontDatabase, QPalette, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSystemTrayIcon, QMenu, QStyle
)
from loguru import logger

from core.config_loader import config
from core.event_bus import bus, Events
from core.state_machine import sm, State
from core.session_manager import session

from audio.mic_stream import MicStream
from audio.vad_manager import VadManager
from audio.wake_listener import WakeDetector

from speech.whisper_stt import WhisperSTT
from speech.transcript_validator import TranscriptValidator
from speech.tts_engine import TTSThread
from speech.response_formatter import format_for_speech

from brain.intent_router import router
from brain.memory_manager import memory

from actions.conversation import conversation

from gui.auth_window import AuthWindow
from gui.console_window import ConsoleWindow
from gui.admin_window import AdminWindow
from gui.memory_window import MemoryWindow
from gui.widgets.status_bar import StatusBarWidget
from gui.enroll_dialog import EnrollDialog
from gui.confirmation_dialog import ConfirmationDialog

from services.action_dispatcher import dispatcher
from services.confirmation_service import confirmation_service
from services.session_guard import session_guard


class _Signals(QObject):
    """Cross-thread Qt signal carrier — all signals emitted on Qt thread."""
    state_changed    = Signal(str)
    user_transcript  = Signal(str)
    aura_response    = Signal(str)
    activity_update  = Signal(str)
    countdown_start  = Signal(int)
    countdown_stop   = Signal()


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AURA  —  v1.0  Phase 1")
        self.setMinimumSize(900, 660)
        self.resize(1100, 720)

        self._signals = _Signals()
        self._audio_queue: Queue[bytes] = Queue(maxsize=300)
        self._active_timer: Timer | None = None
        self._active_timeout = config.get("session.active_window_timeout", 300) # Increased from 30 to 300

        # Initialised in _start_pipeline()
        self._stt: WhisperSTT | None = None
        self._wake: WakeDetector | None = None
        self._validator = TranscriptValidator()
        self._tts: TTSThread | None = None
        self._mic: MicStream | None = None
        self._vad: VadManager | None = None
        self._active_dialog: ConfirmationDialog | None = None
        self._scheduler_timer: QTimer | None = None
        self._pending_notifications: list[dict] = []
        self._last_triggered_notif: dict | None = None
        self._last_media_cmd_time = 0.0

        self._load_theme()
        self._build_ui()
        self._setup_tray_icon()
        self._wire_signals()

    # ── Theme & UI ────────────────────────────────────────────────────────────

    def _load_theme(self):
        qss_path = Path(__file__).parent / "theme.qss"
        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        self.setFont(QFont("Segoe UI", 11))

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Top bar ────────────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setObjectName("top_bar")
        top_bar.setFixedHeight(52)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 16, 0)
        top_layout.setSpacing(8)

        brand = QLabel("AURA")
        brand.setObjectName("brand_label")
        ver = QLabel("v1 · Phase 1")
        ver.setObjectName("version_label")

        top_layout.addWidget(brand)
        top_layout.addWidget(ver)
        top_layout.addStretch()

        self._nav_console = self._make_nav_btn("CONSOLE", 1)
        self._nav_admin   = self._make_nav_btn("SETTINGS", 2)
        self._nav_memory  = self._make_nav_btn("MEMORY", 3)
        for btn in (self._nav_console, self._nav_admin, self._nav_memory):
            top_layout.addWidget(btn)

        # ── Screen stack ───────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._auth        = AuthWindow()
        self._console     = ConsoleWindow()
        self._admin       = AdminWindow()
        self._memory_win  = MemoryWindow()

        # index 0 = auth (pre-login), 1 = console, 2 = admin, 3 = memory
        self._stack.addWidget(self._auth)
        self._stack.addWidget(self._console)
        self._stack.addWidget(self._admin)
        self._stack.addWidget(self._memory_win)

        self._auth.auth_success.connect(self._on_auth_proceed)
        self._auth.enroll_requested.connect(self._open_enroll_dialog)

        # ── Status bar ─────────────────────────────────────────────────────
        self._status_bar = StatusBarWidget()

        outer.addWidget(top_bar)
        outer.addWidget(self._stack, stretch=1)
        outer.addWidget(self._status_bar)

        # Start on auth screen; hide nav until authenticated
        self._stack.setCurrentIndex(0)
        self._nav_console.hide()
        self._nav_admin.hide()
        self._nav_memory.hide()
        
        # Start microphone in background while LOCKED
        self._start_pipeline()

        # Check if auth bypass is requested (via command line or config)
        import sys
        if "--bypass-auth" in sys.argv or config.get("aura.dev_mode", False):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._auto_bypass_startup)

    def _auto_bypass_startup(self):
        logger.info("Dev Mode: Auto-bypassing authentication on startup.")
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._on_auth_proceed("Omm")

    def _make_nav_btn(self, label: str, stack_idx: int) -> QPushButton:
        btn = QPushButton(label)
        btn.setObjectName("nav_btn")
        btn.setCheckable(True)
        btn.clicked.connect(lambda _, i=stack_idx: self._switch_screen(i))
        return btn

    # ── System Tray ───────────────────────────────────────────────────────────

    def _setup_tray_icon(self):
        # Create tray icon
        self._tray_icon = QSystemTrayIcon(self)
        
        # Use a standard Qt icon for the tray
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self._tray_icon.setIcon(icon)
        self._tray_icon.setToolTip("AURA - AI Voice Assistant")
        
        # Create context menu
        tray_menu = QMenu(self)
        
        show_action = tray_menu.addAction("Show AURA")
        show_action.triggered.connect(self._tray_show_requested)
        
        quit_action = tray_menu.addAction("Exit")
        quit_action.triggered.connect(self.close)
        
        self._tray_icon.setContextMenu(tray_menu)
        
        # Show/hide on double click
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _tray_show_requested(self):
        if self.isHidden():
            if sm.is_(State.LOCKED):
                self._start_face_auth()
            else:
                self.showNormal()
                self.raise_()
                self.activateWindow()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._tray_show_requested()

    # ── Auth → console transition ─────────────────────────────────────────

    @Slot(str)
    def _on_auth_proceed(self, username: str = "user"):
        """Called by auth_success signal with the authenticated username."""
        session.authorize(username)

        for btn in (self._nav_console, self._nav_admin, self._nav_memory):
            btn.show()
        self._nav_console.setChecked(True)
        self._switch_screen(1)
        self._console.load_history()
        
        sm.transition(State.IDLE)
        # We transition to SPEAKING first so the VAD doesn't capture the greeting
        if sm.transition(State.SPEAKING):
            self._signals.activity_update.emit("Authenticated. Greeting user...")
            self._start_active_timer() # This now handles both the timer and the UI signals
        
        self._tts.speak(f"Access granted. Welcome {username}.")

    def _open_enroll_dialog(self):
        dlg = EnrollDialog(self)
        dlg.enroll_start.connect(self._auth.start_enrollment)
        dlg.exec()

    def _switch_screen(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        self._nav_console.setChecked(idx == 1)
        self._nav_admin.setChecked(idx == 2)
        self._nav_memory.setChecked(idx == 3)
        if idx == 3:
            self._memory_win.refresh()

    # ── Signal wiring ─────────────────────────────────────────────────────────

    def _wire_signals(self):
        sig = self._signals
        sig.state_changed.connect(self._console.on_state_changed)
        sig.user_transcript.connect(self._console.add_user_transcript)
        sig.aura_response.connect(self._console.add_aura_response)
        sig.activity_update.connect(self._console.set_activity)
        sig.countdown_start.connect(self._status_bar.start_countdown)
        sig.countdown_stop.connect(self._status_bar.stop_countdown)

        bus.subscribe(Events.STATE_CHANGED, lambda p: self._signals.state_changed.emit(p.get("to", "IDLE")))
        bus.subscribe(Events.SESSION_LOCKED, lambda _: self._on_locked())
        bus.subscribe(Events.AUTH_SUCCESS,   lambda p: logger.info("Event: AUTH_SUCCESS user={}", p.get("user")))
        
        # Phase 2: Agent Telemetry Wiring
        bus.subscribe("agent.thought", lambda p: self._signals.activity_update.emit(f"[Planner] {p.get('thought', '')}"))
        bus.subscribe("agent.action", lambda p: self._signals.activity_update.emit(f"Executing: {p.get('tool', '')}"))

    # ── Audio pipeline ────────────────────────────────────────────────────────

    def _start_pipeline(self):
        # ── TTS ──────────────────────────────────────────────────────────
        self._tts = TTSThread(
            rate=config.get("tts.rate", 175),
            volume=config.get("tts.volume", 0.95),
        )
        self._tts.speech_started.connect(self._on_tts_start)
        self._tts.speech_ended.connect(self._on_tts_done)
        self._tts.start()

        # ── STT (Groq Whisper — used for BOTH wake detection and commands) ─
        api_key = config.groq_api_key()
        if not api_key:
            logger.error("GROQ_API_KEY is not set — wake detection and STT will not work!")
            self._tts.speak("Warning: Groq API key not found. Please set it in the .env file.")
            self._signals.aura_response.emit("⚠ GROQ_API_KEY missing — check .env file.")
        else:
            self._stt = WhisperSTT(
                api_key=api_key,
                model=config.get("stt.model", "whisper-large-v3-turbo"),
            )
            # Wake detector wraps the same STT instance — no separate model needed
            phrase = config.get("wake.phrase", "take control")
            self._wake = WakeDetector(phrase, self._stt)

        # ── VAD — single instance, always running ─────────────────────────
        self._vad = VadManager(
            on_speech_end=self._on_utterance_captured,   # fires from VAD thread
            aggressiveness=config.get("vad.aggressiveness", 2),
            silence_frames=config.get("vad.silence_frames", 30), # tuned from 35
            min_speech_frames=config.get("vad.min_speech_frames", 8), # tuned from 15
            pre_speech_pad=config.get("vad.pre_speech_pad_frames", 7), # tuned from 10
        )

        # ── VAD consumer thread — feeds mic frames into VadManager ────────
        self._shutdown_flag = False
        Thread(target=self._vad_consumer, daemon=True, name="vad-consumer").start()

        # ── Mic ───────────────────────────────────────────────────────────
        device_idx = config.get("audio.device_index", None)
        self._mic = MicStream(self._audio_queue, device_index=device_idx)
        self._mic.start()
        self._status_bar.set_mic(True)

        # ── Dashboard Scheduler ───────────────────────────────────────────
        from PySide6.QtCore import QTimer
        self._scheduler_timer = QTimer(self)
        self._scheduler_timer.timeout.connect(self._check_scheduler)
        self._scheduler_timer.start(30000) # Check every 30 seconds
        logger.info("Scheduler started (30s interval)")

        # Announce
        logger.info("Pipeline started silently — waiting for wake phrase")

    # ── VAD consumer (background thread) ─────────────────────────────────────

    def _vad_consumer(self) -> None:
        """
        Continuously pulls PCM frames from the shared queue and feeds VadManager.
        VadManager accumulates speech and fires _on_utterance_captured when done.
        """
        while not self._shutdown_flag:
            try:
                frame = self._audio_queue.get(timeout=0.5)
            except Empty:
                continue
            # Always feed VAD — VadManager routes internally via callback
            self._vad.process(frame)
        logger.debug("VAD consumer thread exited.")

    # ── Utterance router ──────────────────────────────────────────────────────

    def _on_utterance_captured(self, audio: bytes) -> None:
        """
        Called by VadManager from the VAD consumer thread when an utterance ends.
        Routes to wake check or command processing depending on state.
        """
        # Phase 4: Media Cooldown (Self-listening protection)
        import time
        if time.time() - self._last_media_cmd_time < 1.5:
            logger.debug("Ignoring utterance during media cooldown.")
            self._vad.reset()
            return

        state = sm.state

        if state in (State.IDLE, State.LOCKED):
            # Check if this utterance is the wake phrase
            Thread(target=self._check_wake, args=(audio,), daemon=True, name="wake-check").start()

        elif state == State.LISTENING:
            # User is giving a command — process it
            Thread(target=self._process_command, args=(audio,), daemon=True, name="cmd-proc").start()

        # All other states (THINKING, SPEAKING, etc.) — ignore audio

    # ── Wake check ────────────────────────────────────────────────────────────

    def _check_wake(self, audio: bytes) -> None:
        """Transcribe audio via Groq and check for wake phrase (runs in thread)."""
        if self._wake is None or self._stt is None:
            return

        is_wake, transcript = self._wake.check(audio)

        if is_wake:
            if sm.is_(State.LOCKED):
                from PySide6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(self, "_start_face_auth", Qt.QueuedConnection)
            else:
                if sm.transition(State.LISTENING):
                    self._vad.reset()
                    session.touch()
                    self._start_active_timer()
                    self._signals.activity_update.emit("Listening for your command…")
                    self._signals.countdown_start.emit(self._active_timeout)
                    self._tts.speak("Yes?")
        else:
            # Non-wake speech in IDLE or LOCKED — silently ignore (no log spam for ambient noise)
            if transcript.strip():
                logger.debug("Silently ignored ambient speech: '{}'", transcript)

    @Slot()
    def _start_face_auth(self):
        """Called when wake phrase is detected while LOCKED."""
        self.showNormal()
        self.raise_()
        self.activateWindow()
        
        import sys
        if "--bypass-auth" in sys.argv or config.get("aura.dev_mode", False):
            logger.info("Dev Mode: Bypassing face authentication on wake.")
            self._on_auth_proceed("Omm")
            return

        self._stack.setCurrentIndex(0)
        self._auth.activate_auth_flow()
        self._tts.speak("Please look at the camera to verify your identity.")

    # ── Command processing ────────────────────────────────────────────────────

    def _process_command(self, audio: bytes) -> None:
        """Transcribe, validate, route, and respond (runs in thread)."""
        if not sm.is_(State.LISTENING):
            return

        sm.transition(State.THINKING)
        self._signals.activity_update.emit("Transcribing…")
        session.touch()
        # Timer now resets in _on_tts_done to ensure user gets full window AFTER response

        # ── STT ──────────────────────────────────────────────────────────
        if self._stt is None:
            self._respond("STT is not available. Please check your Groq API key.")
            return

        text = self._stt.transcribe(audio)
        valid, reason = self._validator.validate(text)

        if not valid:
            logger.info("Transcript rejected ({}): '{}'", reason, text)
            self._signals.activity_update.emit(f"I didn't hear that clearly. Try again?")
            sm.transition(State.LISTENING)
            self._vad.reset()
            return

        self._signals.user_transcript.emit(text)
        self._signals.activity_update.emit(f"Processing: {text[:60]}")
        logger.info("User said: '{}'", text)

        # ── 1. Strict Voice Confirmation Check ──
        if confirmation_service.is_awaiting_confirmation:
            self._handle_voice_confirmation(text)
            return

        # ── 2. Route & Parse (Single-Intent Only) ──
        cmds = router.route(text)
        if not cmds:
            return
            
        cmd = cmds[0] # AURA Phase 4: process only the first intent
        logger.info("Universal Brain: Selected intent '{}'", cmd.intent)
        
        # ── 3. Authorization Gate ──
        allowed, reason = session_guard.verify_access(cmd)
        if not allowed and reason == "re_auth_required":
            response = "I need to verify your identity before doing that. Please look at the camera."
            self._signals.aura_response.emit(response)
            sm.transition(State.SPEAKING)
            self._tts.speak(response)
            # Re-open auth window
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3500, self._trigger_reauth)
            return
    
        # ── 4. Confirmation Gate (Dangerous Actions) ──
        if cmd.requires_confirmation:
            confirmation_service.request_confirmation(cmd)
            action_name = cmd.action.replace("_", " ")
            
            response = f"I'm ready to {action_name}. Please confirm — say yes to proceed or no to cancel."
            
            # Show visual dialog on main thread
            from PySide6.QtCore import QMetaObject, Q_ARG
            QMetaObject.invokeMethod(self, "_show_confirmation_dialog", Qt.QueuedConnection, Q_ARG(str, action_name))
            
            self._respond(response)
            # Active Window Timer for confirmation (short 6s window)
            self._start_confirmation_timer()
            return

        # ── 5. Dispatch ──
        if cmd.intent == "conversation":
            sm.transition(State.EXECUTING)
            response = conversation.chat(text)
            spoken = format_for_speech(response)
            memory.log_turn(text, spoken)
            self._respond(spoken)

        elif cmd.intent == "time":
            # Use the new time service
            sm.transition(State.EXECUTING)
            result = dispatcher.dispatch(cmd)
            memory.log_turn(text, result.message)
            self._respond(result.message)

        else:
            sm.transition(State.EXECUTING)
            result = dispatcher.dispatch(cmd)
            
            # Phase 4: Media Cooldown trigger
            if cmd.intent in ("media_control", "volume", "volume_up", "volume_down"):
                import time
                self._last_media_cmd_time = time.time()
                logger.debug("Media cooldown initiated.")

            memory.log_turn(text, result.message)
            self._respond(result.message)

    def _handle_voice_confirmation(self, text: str):
        """Processes restricted voice input during the confirmation window."""
        text = text.lower().strip()
        logger.info("Confirmation mode heard: '{}'", text)
        
        yes_list = ("yes", "confirm", "do it", "proceed", "yeah", "yep")
        no_list = ("no", "cancel", "stop", "don't", "dont", "nope")
        
        if any(word in text for word in yes_list):
            logger.info("Voice confirmation: YES")
            self._on_confirmation_yes()
        elif any(word in text for word in no_list):
            logger.info("Voice confirmation: NO")
            self._on_confirmation_no()
        else:
            logger.warning("Unrecognized confirmation reply: '{}'. Ignoring.", text)
            # User instructions: "if the reply is unclear, ask once more or cancel safely"
            # For simplicity and speed, we'll cancel safely if unheard or ask once
            self._respond("I didn't catch that. Please say yes to confirm or no to cancel.")
            self._start_confirmation_timer() # Reset timer for one more try
            
        memory.log_turn(text, "I didn't catch that. Please say yes to confirm or no to cancel.")

    # ── Response output ────────────────────────────────────────────────────────

    def _respond(self, text: str) -> None:
        self._signals.aura_response.emit(text)
        sm.transition(State.SPEAKING)
        self._tts.speak(text)

    @Slot(str)
    def _on_tts_start(self, text: str) -> None:
        """When AURA starts speaking, mute mic and clear the queue."""
        if self._mic:
            self._mic.set_mute(True)
        self._purge_audio_queue()
        logger.debug("TTS started — monitoring paused to avoid feedback.")

    @Slot()
    def _on_tts_done(self) -> None:
        """After speaking, return to LISTENING (stay in active window) or IDLE."""
        self._purge_audio_queue()
        if self._mic:
            self._mic.set_mute(False)
            
        if sm.is_(State.SPEAKING):
            # Check for queued notifications first
            if self._pending_notifications:
                notif = self._pending_notifications.pop(0)
                sm.transition(State.IDLE) # briefly reset
                self._trigger_notification(notif)
                return

            # Restart the timer so the user gets a full window of silence
            self._start_active_timer()
            sm.transition(State.LISTENING)
            self._vad.reset()

    def _purge_audio_queue(self) -> None:
        """Clear all pending audio frames to remove echoes."""
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except Empty:
                break
        logger.debug("Audio queue purged.")

    # ── Scheduler & Notifications ─────────────────────────────────────────────

    def _check_scheduler(self) -> None:
        """Poll DB for due reminders/alarms."""
        due_items = memory.get_due_reminders()
        if not due_items:
            return

        for item in due_items:
            notif = {
                "id": item.id,
                "type": item.type,
                "message": item.message
            }
            if sm.is_(State.SPEAKING, State.THINKING):
                logger.debug("Deferring notification [ID:{}]; AURA is busy.", item.id)
                self._pending_notifications.append(notif)
            else:
                self._trigger_notification(notif)
            
            # Mark completed immediately so we don't trigger twice
            memory.mark_reminder_completed(item.id)

    def _trigger_notification(self, notif: dict) -> None:
        """Play sound and/or speak the reminder."""
        rtype = notif.get("type", "reminder")
        msg = notif.get("message", "something")
        self._last_triggered_notif = notif # Track for snooze
        
        sm.transition(State.SPEAKING)
        
        if rtype == "alarm":
            # Play a brief beep
            import winsound
            Thread(target=lambda: winsound.Beep(1000, 500), daemon=True).start()
            self._tts.speak(f"Alarm ringing. It is time for your scheduled alarm.")
        else:
            self._tts.speak(f"Reminder: {msg}")
            
        self._signals.aura_response.emit(f"🔔 [{rtype.upper()}] {msg}")
        logger.info("Triggered {} [ID:{}]: {}", rtype, notif.get("id"), msg)

    # ── Active window timer ────────────────────────────────────────────────────

    def _start_active_timer(self) -> None:
        self._cancel_timers()
        self._active_timer = Timer(self._active_timeout, self._on_active_timeout)
        self._active_timer.daemon = True
        self._active_timer.start()
        self._signals.countdown_start.emit(self._active_timeout)

    def _start_confirmation_timer(self) -> None:
        """Start a short 6-second window for confirmations."""
        self._cancel_timers()
        self._active_timer = Timer(6.0, self._on_confirmation_timeout)
        self._active_timer.daemon = True
        self._active_timer.start()

    def _cancel_timers(self) -> None:
        if self._active_timer and self._active_timer.is_alive():
            self._active_timer.cancel()
        self._active_timer = None

    def _on_confirmation_timeout(self) -> None:
        if confirmation_service.is_awaiting_confirmation:
            logger.info("Confirmation timed out after 6 seconds.")
            # Use QMetaObject to call UI cleanup on main thread
            from PySide6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self, "_on_confirmation_no", Qt.QueuedConnection)

    def _on_active_timeout(self) -> None:
        logger.info("Active window timed out — returning to IDLE")
        self._signals.countdown_stop.emit()
        if sm.state in (State.LISTENING, State.THINKING):
            sm.transition(State.IDLE)
            self._vad.reset()
            # If confirmation was pending, clear it
            if confirmation_service.is_awaiting_confirmation:
                confirmation_service.resolve(False)

    # ── Confirmation Callbacks ────────────────────────────────────────────────

    @Slot(str)
    def _show_confirmation_dialog(self, action_name: str):
        self._active_dialog = ConfirmationDialog(action_name, self)
        self._active_dialog.confirmed.connect(self._on_confirmation_yes)
        self._active_dialog.cancelled.connect(self._on_confirmation_no)
        self._active_dialog.show()

    @Slot()
    def _on_confirmation_yes(self):
        self._active_dialog = None
        cmd = confirmation_service.resolve(True)
        if cmd:
            Thread(target=self._execute_confirmed, args=(cmd,), daemon=True).start()

    @Slot()
    def _on_confirmation_no(self):
        self._active_dialog = None
        confirmation_service.resolve(False)
        msg = "Action cancelled."
        memory.log_turn("no", msg)
        self._respond(msg)

    def _execute_confirmed(self, cmd):
        sm.transition(State.EXECUTING)
        result = dispatcher.dispatch(cmd)
        memory.log_turn("yes", result.message)
        self._respond(result.message)

    # ── Re-auth trigger ───────────────────────────────────────────────────────

    def _trigger_reauth(self):
        """Re-show the auth screen for re-authentication."""
        self._cancel_timers()
        self._signals.countdown_stop.emit()
        # Stop active audio pipeline temporarily
        if sm.is_(State.LISTENING, State.THINKING):
            sm.transition(State.IDLE)
        self._stack.setCurrentIndex(0)   # back to auth
        for btn in (self._nav_console, self._nav_admin, self._nav_memory):
            btn.hide()
        # Restart camera in auth window
        if hasattr(self._auth, '_start_camera'):
            self._auth._attempts = 0
            self._auth._restart_auth()

    # ── Lock ──────────────────────────────────────────────────────────────────

    def _on_locked(self) -> None:
        self._cancel_timers()
        self._signals.countdown_stop.emit()
        self.hide()   # Hide the UI to stay silent in background
        if hasattr(self, '_tray_icon'):
            self._tray_icon.showMessage("AURA", "AURA is running in the background. Say 'Take Control' to wake.", QSystemTrayIcon.MessageIcon.Information, 3000)
        if self._tts:
            self._tts.speak("Session locked due to inactivity.")

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def closeEvent(self, event):  # noqa: N802
        logger.info("Initiating AURA shutdown sequence...")
        self._shutdown_flag = True
        
        # 1. Stop all timers
        logger.debug("Stopping session and confirmation timers...")
        self._cancel_timers()
        self._signals.countdown_stop.emit()
        
        # 2. Stop microphone stream
        if self._mic:
            logger.debug("Stopping microphone stream...")
            self._mic.stop()
        
        # 3. Stop TTS engine thread
        if self._tts:
            logger.debug("Shutting down TTS engine thread...")
            self._tts.shutdown()
        
        # 4. Clean up VAD consumer (flag already set)
        
        # 5. Notify system
        logger.info("Publishing shutdown event...")
        bus.publish(Events.SHUTDOWN, {})
        
        logger.info("AURA offline. Goodbye.")
        event.accept()
