"""
gui/auth_window.py — Phase 2 full face authentication screen.

Camera pipeline:
  CameraThread → emits QImage + best face object every frame
  AuthWindow   → draws frame on QLabel, runs state machine

Auth states:
  INITIALIZING → SCANNING → FACE_DETECTED → LIVENESS → RECOGNIZING
  → GRANTED (transition to console) | DENIED (retry)
  NO_USERS → show enroll prompt
"""
from __future__ import annotations
import math
import time
from enum import Enum, auto
from threading import Thread

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QThread
from PySide6.QtGui import QImage, QPixmap, QFont, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy,
)
from loguru import logger
from core.config_loader import config

from auth.face_auth import face_analyzer
from auth.access_controller import access_controller
from auth.enroll_manager import enroll_manager
from auth.user_registry import registry


class AuthState(Enum):
    INITIALIZING  = auto()
    NO_USERS      = auto()
    SCANNING      = auto()
    FACE_DETECTED = auto()
    RECOGNIZING   = auto()
    GRANTED       = auto()
    DENIED        = auto()
    ENROLLING     = auto()
    ENROLL_CONFIRM = auto()
    UNAVAILABLE   = auto()


_STATE_TEXT = {
    AuthState.INITIALIZING:  "Initialising face recognition…",
    AuthState.NO_USERS:      "No users enrolled. Please enrol yourself to continue.",
    AuthState.SCANNING:      "Position your face in the frame…",
    AuthState.FACE_DETECTED: "Face detected — verifying identity...",
    AuthState.RECOGNIZING:   "Identifying…",
    AuthState.GRANTED:       "✓  ACCESS GRANTED",
    AuthState.DENIED:        "✗  ACCESS DENIED",
    AuthState.ENROLLING:     "Look at the camera and hold still…",
    AuthState.ENROLL_CONFIRM: "Confirm your identity summary below.",
    AuthState.UNAVAILABLE:   "Face auth unavailable — InsightFace not installed",
}

_STATE_COLOR = {
    AuthState.INITIALIZING:  "#3D5A7A",
    AuthState.NO_USERS:      "#FF9900",
    AuthState.SCANNING:      "#3D5A7A",
    AuthState.FACE_DETECTED: "#00D4FF",
    AuthState.RECOGNIZING:   "#7B5FFF",
    AuthState.GRANTED:       "#00FF88",
    AuthState.DENIED:        "#FF3355",
    AuthState.ENROLLING:     "#00D4FF",
    AuthState.ENROLL_CONFIRM: "#00FF88",
    AuthState.UNAVAILABLE:   "#FF3355",
}


# ── Camera QThread ────────────────────────────────────────────────────────────

class CameraThread(QThread):
    frame_ready = Signal(QImage, object)   # (QImage, face_object or None)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self.daemon = True
        self.last_bgr: np.ndarray | None = None   # latest raw frame for recognition

    def run(self):
        device_idx = config.get("camera.device_index", 0)
        backend_str = config.get("camera.backend", "default").lower()
        
        backend = None
        if backend_str == "dshow":
            backend = cv2.CAP_DSHOW
        elif backend_str == "msmf":
            backend = cv2.CAP_MSMF
            
        logger.info("CameraThread: Initializing hardware (index={}, backend={})...", device_idx, backend_str)
        if backend is not None:
            cap = cv2.VideoCapture(device_idx, backend)
        else:
            cap = cv2.VideoCapture(device_idx)
        
        if not cap.isOpened():
            logger.error("CameraThread: VideoCapture failed to open (index={}, backend={}).", device_idx, backend_str)
            return
            
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        logger.info("CameraThread: Hardware online. Starting acquisition.")

        while self._running:
            ret, frame = cap.read()
            if not ret:
                logger.warning("CameraThread: ret=False from cap.read()")
                time.sleep(0.03)
                continue

            frame = cv2.flip(frame, 1)          # mirror view
            self.last_bgr = frame.copy()         # store for recognition (no second cap needed)

            # Detect face
            try:
                face = face_analyzer.best_face(frame, min_confidence=0.75)
            except Exception as e:
                logger.error("CameraThread: Face detection error: {}", e)
                face = None

            # Draw overlay on frame
            if face is not None:
                x, y, w, h = face["bbox"]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 212, 255), 2)  # cyan
                for kp in face["landmarks"]:
                    cv2.circle(frame, tuple(kp), 3, (0, 255, 136), -1)

            # Convert to QImage using tobytes() to avoid garbage collection issues
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                qimg = QImage(rgb.tobytes(), w, h, ch * w, QImage.Format.Format_RGB888)
                self.frame_ready.emit(qimg, face)
            except Exception as e:
                logger.error("CameraThread: Frame conversion error: {}", e)

        cap.release()
        logger.info("CameraThread: Hardware released.")

    def stop(self):
        self._running = False


# ── Auth Window ───────────────────────────────────────────────────────────────

class AuthWindow(QWidget):
    """
    Full face authentication screen.
    Emits `auth_success(username)` when user passes face auth.
    """
    auth_success = Signal(str)           # username
    enroll_requested = Signal()          # open enrollment dialog

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("auth_panel")

        self._state = AuthState.INITIALIZING
        self._camera: CameraThread | None = None
        self._attempts = 0
        self._max_attempts = 3
        self._last_face = None
        self._scan_angle = 0.0

        self._build_ui()
        self._start_scan_animation()
        self._init_face_analyzer()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Brand ──────────────────────────────────────────────────────────
        brand = QLabel("A U R A")
        brand.setObjectName("auth_title")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("BIOMETRIC AUTHENTICATION")
        sub.setObjectName("auth_subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Camera preview ─────────────────────────────────────────────────
        self._cam_label = QLabel()
        self._cam_label.setFixedSize(480, 360)
        self._cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cam_label.setStyleSheet(
            "background:#050A14; border: 2px solid #0D2840; border-radius: 12px;"
        )

        cam_row = QHBoxLayout()
        cam_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cam_row.addWidget(self._cam_label)

        # ── Status text ────────────────────────────────────────────────────
        self._status = QLabel("Initialising…")
        self._status.setObjectName("auth_status")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setWordWrap(True)

        # ── Attempt counter ────────────────────────────────────────────────
        self._attempt_label = QLabel("")
        self._attempt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._attempt_label.setStyleSheet("color: #3D5A7A; font-size: 12px;")

        # ── Enroll button (shown when NO_USERS or UNAVAILABLE bypass) ──────
        self._enroll_btn = QPushButton("ENROL MY FACE")
        self._enroll_btn.setObjectName("auth_btn")
        self._enroll_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._enroll_btn.clicked.connect(self.enroll_requested)
        self._enroll_btn.hide()

        # ── Bypass button (dev/setup mode only) ────────────────────────────
        self._bypass_btn = QPushButton("BYPASS  (setup mode)")
        self._bypass_btn.setStyleSheet(
            "color: #3D5A7A; background: transparent; border: 1px solid #1A2A3A;"
            "border-radius: 6px; padding: 4px 12px; font-size: 11px;"
        )
        self._bypass_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bypass_btn.clicked.connect(self._on_bypass)
        self._bypass_btn.hide()

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.addWidget(self._enroll_btn)

        # ── Confirm / Retry row ────────────────────────────────────────────
        self._confirm_row = QWidget()
        conf_layout = QHBoxLayout(self._confirm_row)
        self._save_btn = QPushButton("CONFIRM & SAVE")
        self._save_btn.setObjectName("auth_btn_save")
        self._save_btn.clicked.connect(self._on_enroll_save)
        
        self._retry_btn = QPushButton("RETRY")
        self._retry_btn.setObjectName("auth_btn_retry")
        self._retry_btn.clicked.connect(self._restart_auth)
        
        conf_layout.addWidget(self._retry_btn)
        conf_layout.addWidget(self._save_btn)
        self._confirm_row.hide()

        root.addStretch(1)
        root.addWidget(brand)
        root.addSpacing(4)
        root.addWidget(sub)
        root.addSpacing(20)
        root.addLayout(cam_row)
        root.addSpacing(16)
        root.addWidget(self._status)
        root.addSpacing(6)
        root.addWidget(self._attempt_label)
        root.addSpacing(12)
        root.addLayout(btn_row)
        root.addWidget(self._confirm_row, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._bypass_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addStretch(2)

    # ── Init face analyzer ────────────────────────────────────────────────────

    def _init_face_analyzer(self):
        def _init():
            ok = face_analyzer.initialize()
            if ok:
                self._on_analyzer_ready()
            else:
                self._set_state(AuthState.UNAVAILABLE)
                self._bypass_btn.show()

        Thread(target=_init, daemon=True, name="fa-init").start()

    @Slot()
    def _on_analyzer_ready(self):
        registry.init_db()
        if registry.is_empty():
            self._set_state(AuthState.NO_USERS)
            self._enroll_btn.show()
            return
        self._status.setText("Awaiting voice activation...")

    def activate_auth_flow(self):
        """Called externally when the wake phrase is triggered in LOCKED state."""
        if self._camera is None and not registry.is_empty():
            self._start_camera()

    # ── Camera ────────────────────────────────────────────────────────────────

    def _start_camera(self):
        self._set_state(AuthState.SCANNING)
        self._camera = CameraThread()          # no parent — avoids Qt thread warning
        self._camera.frame_ready.connect(self._on_frame)
        self._camera.start()

    def _stop_camera(self):
        if self._camera:
            self._camera.stop()
            self._zombie_camera = self._camera
            self._zombie_camera.finished.connect(self._zombie_camera.deleteLater)
            self._camera = None

    @Slot(QImage, object)
    def _on_frame(self, qimg: QImage, face):
        # Update preview
        pix = QPixmap.fromImage(qimg).scaled(
            self._cam_label.width(), self._cam_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._cam_label.setPixmap(pix)
        self._last_face = face

        # State-based logic
        if self._state == AuthState.SCANNING:
            if face is not None:
                self._set_state(AuthState.FACE_DETECTED)
                self._set_state(AuthState.RECOGNIZING)
                Thread(target=self._run_recognition, daemon=True, name="recognition").start()

        elif self._state == AuthState.ENROLLING:
            # Convert QImage back to BGR numpy for embedding
            qimg_clone = qimg
            ptr = qimg_clone.bits()
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape(
                qimg_clone.height(), qimg_clone.width(), 3
            )
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            done = enroll_manager.feed_frame(bgr)
            captured, target = enroll_manager.progress
            
            if not done:
                # Show quality feedback if rejected
                reason = enroll_manager.last_rejection
                self._status.setText(f"{reason}\nCapturing: {captured}/{target}")
            else:
                self._on_enrollment_captured()

    # ── Recognition ───────────────────────────────────────────────────────────

    def _run_recognition(self):
        face = self._last_face
        if face is None:
            self._on_denied("no_face")
            return

        # Use the frame already held by the camera thread — no second VideoCapture
        frame = self._camera.last_bgr if self._camera else None
        if frame is None:
            self._on_denied("no_frame")
            return

        embedding = face_analyzer.get_embedding(frame, face)
        if embedding is None:
            embedding = face_analyzer.embedding_from_frame(frame)
        if embedding is None:
            self._on_denied("no_embedding")
            return

        decision = access_controller.verify(embedding)
        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        if decision.granted:
            QMetaObject.invokeMethod(self, "_on_granted", Qt.QueuedConnection, Q_ARG(str, decision.username), Q_ARG(float, decision.confidence))
        else:
            QMetaObject.invokeMethod(self, "_on_denied", Qt.QueuedConnection, Q_ARG(str, decision.reason))

    @Slot(str, float)
    def _on_granted(self, username: str, confidence: float):
        self._set_state(AuthState.GRANTED)
        logger.info("Auth GRANTED: {} ({:.2f})", username, confidence)
        # Stop camera BEFORE transitioning to console so device is free for mic pipeline
        QTimer.singleShot(500, lambda: self._stop_and_emit(username))

    def _stop_and_emit(self, username: str):
        self._stop_camera()
        self.auth_success.emit(username)

    @Slot(str)
    def _on_denied(self, reason: str):
        self._attempts += 1
        self._set_state(AuthState.DENIED)
        access_controller.deny_log(reason)

        if self._attempts >= self._max_attempts:
            self._speak("Access denied. Maximum attempts reached.")
            self._attempt_label.setText(f"Locked after {self._max_attempts} failed attempts.")
            return

        self._speak("Access denied. Please try again.")
        self._attempt_label.setText(f"Attempt {self._attempts} of {self._max_attempts}")
        QTimer.singleShot(2500, self._retry)

    def _retry(self):
        if self._camera:
            self._set_state(AuthState.SCANNING)

    # ── Enrollment ────────────────────────────────────────────────────────────

    def start_enrollment(self, name: str):
        """Called from EnrollDialog after user enters their name."""
        enroll_manager.start(name)
        if self._camera is None:
            self._start_camera()
        self._set_state(AuthState.ENROLLING)
        self._speak(f"Hi {name}. Please look at the camera and hold still.")

    def _on_enrollment_captured(self):
        """Called when 20 frames are captured but not yet saved."""
        self._set_state(AuthState.ENROLL_CONFIRM)
        self._stop_camera()
        
        # Show the best frame captured
        if enroll_manager.best_frame_bgr is not None:
             rgb = cv2.cvtColor(enroll_manager.best_frame_bgr, cv2.COLOR_BGR2RGB)
             h, w, ch = rgb.shape
             qimg = QImage(rgb.data.tobytes(), w, h, ch * w, QImage.Format.Format_RGB888)
             pix = QPixmap.fromImage(qimg).scaled(self._cam_label.size(), Qt.AspectRatioMode.KeepAspectRatio)
             self._cam_label.setPixmap(pix)

        self._confirm_row.show()
        self._speak("Capture complete. Check your face quality and confirm to save.")

    @Slot()
    def _on_enroll_save(self):
        user_id = enroll_manager.finalize_and_save()
        name = enroll_manager._target_name
        self._confirm_row.hide()
        if user_id != -1:
            self._set_state(AuthState.GRANTED)
            self._speak(f"Enrollment successful. Welcome {name}.")
            QTimer.singleShot(2000, lambda: self._stop_and_emit(name))
        else:
            self._restart_auth()

    def _restart_auth(self):
        self._confirm_row.hide()
        enroll_manager.cancel()
        self._attempts = 0
        self._attempt_label.setText("")
        if registry.is_empty():
            self._set_state(AuthState.NO_USERS)
            self._enroll_btn.show()
        else:
            self._set_state(AuthState.SCANNING)

    # ── State management ──────────────────────────────────────────────────────

    def _set_state(self, state: AuthState):
        self._state = state
        text  = _STATE_TEXT.get(state, "")
        color = _STATE_COLOR.get(state, "#7B9DB5")
        self._status.setText(text)
        self._status.setStyleSheet(
            f"font-size: 15px; letter-spacing: 2px; color: {color}; font-weight: 600;"
        )

    # ── Scan ring animation ───────────────────────────────────────────────────

    def _start_scan_animation(self):
        self._scan_timer = QTimer(self)
        self._scan_timer.timeout.connect(self._tick_scan)
        self._scan_timer.start(16)

    def _tick_scan(self):
        self._scan_angle = (self._scan_angle + 2) % 360

    # ── TTS helper (synchronous pre-pipeline) ─────────────────────────────────

    @staticmethod
    def _speak(text: str):
        def _run():
            try:
                import pythoncom
                from comtypes.client import CreateObject
                pythoncom.CoInitialize()
                speaker = CreateObject("SAPI.SpVoice")
                speaker.Rate = 2
                speaker.Speak(text)
            except Exception as exc:
                logger.debug("Auth TTS error: {}", exc)
        from threading import Thread
        Thread(target=_run, daemon=True, name="auth-tts").start()

    # ── Bypass (dev) ──────────────────────────────────────────────────────────

    def _on_bypass(self):
        logger.warning("Auth bypassed via dev button")
        self.auth_success.emit("user")

    # ── Connect proceed (Phase 1 compatibility + external wiring) ────────────

    def connect_proceed(self, slot) -> None:
        """Legacy shim — now wires to auth_success."""
        self.auth_success.connect(lambda _: slot())

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event):  # noqa: N802
        self._stop_camera()
        if hasattr(self, '_zombie_camera') and self._zombie_camera.isRunning():
            self._zombie_camera.wait(500)
        event.accept()
