"""
core/session_manager.py — User session lifecycle, auth state, and protected action gate.

Authorization model:
  - `is_authorized` = True  → user has passed face auth; all actions allowed
  - `is_authorized` = False → session exists but protected actions (tier 2+) are blocked
  - Auto-deauthorize after inactivity; re-auth re-opens camera
"""
from __future__ import annotations
from datetime import datetime
from threading import Timer
from loguru import logger
from core.event_bus import bus, Events
from core.state_machine import sm, State
from core.config_loader import config


class SessionManager:
    _instance: SessionManager | None = None

    def __new__(cls) -> SessionManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.active_user: str | None = None
        self.session_start: datetime | None = None
        self._authorized: bool = False
        self._lock_timer: Timer | None = None
        self._auto_lock_minutes = config.get("session.auto_lock_minutes", 10)

    # ── Auth state ────────────────────────────────────────────────────────────

    def authorize(self, user: str) -> None:
        """Called after successful face authentication."""
        self.active_user = user
        self.session_start = datetime.now()
        self._authorized = True
        self._reset_lock_timer()
        logger.info("Session authorized for '{}'", user)

    def deauthorize(self) -> None:
        """
        Lock protected actions but keep session alive for conversation.
        Risky actions will prompt re-authentication.
        """
        if self._authorized:
            self._authorized = False
            self._cancel_lock_timer()
            bus.publish(Events.SESSION_LOCKED, {"user": self.active_user})
            logger.info("Session deauthorized — protected actions locked")

    @property
    def is_authorized(self) -> bool:
        return self._authorized

    @property
    def is_active(self) -> bool:
        return self.active_user is not None

    def end_session(self) -> None:
        self.deauthorize()
        self.active_user = None
        self.session_start = None
        logger.info("Session ended")

    # ── Activity tracking ─────────────────────────────────────────────────────

    def touch(self) -> None:
        """Reset the auto-deauthorize countdown on any user activity."""
        if self._authorized:
            self._reset_lock_timer()

    # ── Protected-action gate ─────────────────────────────────────────────────

    def gate(self, intent: str) -> tuple[bool, str]:
        """
        Check whether `intent` is allowed in the current session state.
        Returns (allowed: bool, reason: str).

        reason values:
          "ok"               → proceed
          "re_auth_required" → session deauthorized; re-open camera
          "confirm_required" → ask user to confirm before executing
        """
        from brain.policy import get_tier, requires_confirmation

        tier = get_tier(intent)

        if tier >= 2 and not self._authorized:
            logger.warning("Gate blocked '{}' — session not authorized", intent)
            return False, "re_auth_required"

        if requires_confirmation(intent):
            return False, "confirm_required"

        return True, "ok"

    # ── Lock timer internals ─────────────────────────────────────────────────

    def _reset_lock_timer(self) -> None:
        self._cancel_lock_timer()
        seconds = self._auto_lock_minutes * 60
        self._lock_timer = Timer(seconds, self._on_auto_lock)
        self._lock_timer.daemon = True
        self._lock_timer.start()

    def _cancel_lock_timer(self) -> None:
        if self._lock_timer and self._lock_timer.is_alive():
            self._lock_timer.cancel()
        self._lock_timer = None

    def _on_auto_lock(self) -> None:
        logger.info("Auto-deauthorize triggered after {} min inactivity", self._auto_lock_minutes)
        self.deauthorize()


# Module-level singleton
session = SessionManager()
