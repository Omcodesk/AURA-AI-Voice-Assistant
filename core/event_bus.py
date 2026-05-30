"""
core/event_bus.py — Thread-safe pub/sub event bus using Qt signals.

Events are emitted as (event_type: str, payload: dict) pairs.
Any component can subscribe via EventBus.subscribe(event_type, callback).
"""

from __future__ import annotations
from typing import Callable
from collections import defaultdict
from threading import Lock

from PySide6.QtCore import QObject, Signal
from loguru import logger


class _BusCore(QObject):
    """Internal Qt object that owns the signal."""
    event_fired = Signal(str, object)   # event_type, payload dict


class EventBus:
    """
    Lightweight publish/subscribe bus.
    Thread-safe: publish() can be called from any thread.
    Callbacks are always invoked on the Qt thread via signal/slot.
    """

    _instance: EventBus | None = None

    def __new__(cls) -> EventBus:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._core = _BusCore()
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._lock = Lock()
        self._core.event_fired.connect(self._dispatch)

    def subscribe(self, event_type: str, callback: Callable[[dict], None]) -> None:
        with self._lock:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        with self._lock:
            subs = self._subscribers.get(event_type, [])
            if callback in subs:
                subs.remove(callback)

    def publish(self, event_type: str, payload: dict | None = None) -> None:
        """Thread-safe publish; can be called from any thread."""
        self._core.event_fired.emit(event_type, payload or {})

    def _dispatch(self, event_type: str, payload: object) -> None:
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, []))
        for cb in callbacks:
            try:
                cb(payload)
            except Exception as exc:
                logger.exception("EventBus callback error for '{}': {}", event_type, exc)


# ── Event type constants ────────────────────────────────────────────────────

class Events:
    # Auth
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    SESSION_LOCKED = "session.locked"

    # Wake / listening
    WAKE_DETECTED = "wake.detected"
    SPEECH_START = "speech.start"
    SPEECH_END = "speech.end"
    AUDIO_CAPTURED = "audio.captured"        # payload: {"audio": bytes}

    # Processing
    TRANSCRIPT_READY = "transcript.ready"    # payload: {"text": str}
    TRANSCRIPT_REJECTED = "transcript.rejected"
    INTENT_CLASSIFIED = "intent.classified"  # payload: {"intent": str, "args": dict}
    CONFIRMATION_REQUIRED = "confirmation.required"

    # Action lifecycle
    ACTION_START = "action.start"
    ACTION_COMPLETE = "action.complete"
    ACTION_ERROR = "action.error"

    # Response
    RESPONSE_READY = "response.ready"        # payload: {"text": str}
    TTS_START = "tts.start"
    TTS_END = "tts.end"

    # State
    STATE_CHANGED = "state.changed"          # payload: {"from": str, "to": str}

    # System
    ERROR = "system.error"
    SHUTDOWN = "system.shutdown"


# Module-level singleton
bus = EventBus()
