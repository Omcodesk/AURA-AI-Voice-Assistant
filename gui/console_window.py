"""
gui/console_window.py — Main JARVIS voice console screen.

Layout:
  ┌─────────────────────────────────────┐
  │ [state label]                       │
  │        [OrbWidget]                  │
  │      [ActivityCard]                 │
  │  ─────────────────────────────────  │
  │       [TranscriptPanel]             │
  └─────────────────────────────────────┘
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSizePolicy,
)

from core.state_machine import State
from gui.widgets.orb_widget import OrbWidget
from gui.widgets.transcript_panel import TranscriptPanel
from gui.widgets.activity_card import ActivityCard

_STATE_LABELS = {
    State.LOCKED:    "LOCKED",
    State.IDLE:      "IDLE  —  Say \"Take Control\"",
    State.LISTENING: "AURA IS AT YOUR SERVICE, SIR",
    State.THINKING:  "THINKING…",
    State.EXECUTING: "EXECUTING…",
    State.SPEAKING:  "SPEAKING…",
    State.ERROR:     "ERROR",
}


class ConsoleWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("screen_panel")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 12)
        root.setSpacing(0)

        # ── State label ────────────────────────────────────────────────────
        self._state_label = QLabel("IDLE  —  Say \"Take Control\"")
        self._state_label.setObjectName("state_label")
        self._state_label.setProperty("state", "IDLE")
        self._state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Orb ────────────────────────────────────────────────────────────
        self._orb = OrbWidget()
        self._orb.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        orb_row = QHBoxLayout()
        orb_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        orb_row.addWidget(self._orb)

        # ── Activity card ──────────────────────────────────────────────────
        self._activity = ActivityCard()

        # ── Divider ────────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #0D2040; background: #0D2040; max-height: 1px; margin: 12px 0;")

        # ── Transcript ─────────────────────────────────────────────────────
        self._transcript = TranscriptPanel()

        root.addSpacing(8)
        root.addWidget(self._state_label)
        root.addSpacing(10)
        root.addLayout(orb_row)
        root.addSpacing(10)
        root.addWidget(self._activity)
        root.addWidget(divider)
        root.addWidget(self._transcript, stretch=1)

    # ── Public API (called by MainWindow via slots) ─────────────────────────

    @Slot(str)
    def on_state_changed(self, state_name: str) -> None:
        try:
            state = State(state_name)
        except ValueError:
            return
        label = _STATE_LABELS.get(state, state_name)
        self._state_label.setText(label)
        self._state_label.setProperty("state", state_name)
        self._state_label.style().unpolish(self._state_label)
        self._state_label.style().polish(self._state_label)
        self._orb.set_state(state)

    @Slot(str)
    def add_user_transcript(self, text: str) -> None:
        self._transcript.add_user(text)

    @Slot(str)
    def add_aura_response(self, text: str) -> None:
        self._transcript.add_aura(text)
        self._activity.clear()

    @Slot(str)
    def set_activity(self, text: str) -> None:
        self._activity.set_task(text)

    def load_history(self) -> None:
        """Clear transcript to start fresh for the current session."""
        self._transcript.clear()
