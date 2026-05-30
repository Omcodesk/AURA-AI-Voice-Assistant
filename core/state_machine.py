"""
core/state_machine.py — JARVIS state machine.

States:  LOCKED → IDLE → LISTENING → THINKING → EXECUTING → SPEAKING → IDLE
Transitions are validated; illegal transitions are logged and blocked.
"""

from __future__ import annotations
from enum import Enum, auto
from threading import Lock

from loguru import logger
from core.event_bus import bus, Events


class State(str, Enum):
    LOCKED = "LOCKED"
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"


# Valid transitions: from_state → {allowed to_states}
_TRANSITIONS: dict[State, set[State]] = {
    State.LOCKED:    {State.IDLE, State.SPEAKING, State.ERROR},
    State.IDLE:      {State.LISTENING, State.SPEAKING, State.LOCKED, State.ERROR},
    State.LISTENING: {State.THINKING, State.IDLE, State.LOCKED, State.ERROR},
    State.THINKING:  {State.EXECUTING, State.SPEAKING, State.IDLE, State.LISTENING, State.ERROR},
    State.EXECUTING: {State.SPEAKING, State.IDLE, State.ERROR},
    State.SPEAKING:  {State.LISTENING, State.IDLE, State.LOCKED, State.ERROR},
    State.ERROR:     {State.IDLE, State.SPEAKING, State.LOCKED},
}


class StateMachine:
    _instance: StateMachine | None = None

    def __new__(cls) -> StateMachine:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._state = State.LOCKED
            cls._instance._lock = Lock()
        return cls._instance

    @property
    def state(self) -> State:
        return self._state

    def transition(self, to: State) -> bool:
        """Attempt a state transition. Returns True on success."""
        with self._lock:
            allowed = _TRANSITIONS.get(self._state, set())
            if to not in allowed:
                logger.warning(
                    "Illegal transition: {} → {} (allowed: {})",
                    self._state.value,
                    to.value,
                    [s.value for s in allowed],
                )
                return False

            prev = self._state
            self._state = to
            logger.debug("State: {} → {}", prev.value, to.value)
            bus.publish(Events.STATE_CHANGED, {"from": prev.value, "to": to.value})
            return True

    def is_(self, *states: State) -> bool:
        return self._state in states

    def force(self, to: State) -> None:
        """Force-set state without transition validation (use for recovery only)."""
        with self._lock:
            prev = self._state
            self._state = to
            logger.warning("State forced: {} → {}", prev.value, to.value)
            bus.publish(Events.STATE_CHANGED, {"from": prev.value, "to": to.value})


# Module-level singleton
sm = StateMachine()
