"""
gui/widgets/status_bar.py — Bottom status indicator bar.
Shows: Mic status | Camera | Network | Active window countdown | Current state.
"""

from __future__ import annotations
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel


class StatusBarWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("status_bar_widget")
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(20)

        self._mic = self._make_label("● MIC")
        self._cam = self._make_label("● CAM")
        self._net = self._make_label("● NET")
        self._session = self._make_label("")

        layout.addWidget(self._mic)
        layout.addWidget(self._cam)
        layout.addWidget(self._net)
        layout.addStretch()
        layout.addWidget(self._session)

        # Active window countdown timer
        self._countdown: int = 0
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._tick_countdown)

        self.set_mic(False)
        self.set_cam(False)
        self.set_net(False)

    # ── Public setters ───────────────────────────────────────────────────────

    def set_mic(self, active: bool) -> None:
        self._mic.setProperty("active", "true" if active else "false")
        self._refresh(self._mic)

    def set_cam(self, active: bool) -> None:
        self._cam.setProperty("active", "true" if active else "false")
        self._refresh(self._cam)

    def set_net(self, active: bool) -> None:
        self._net.setProperty("active", "true" if active else "false")
        self._refresh(self._net)

    def start_countdown(self, seconds: int) -> None:
        self._countdown = seconds
        self._session.setText(f"ACTIVE  {self._countdown}s")
        self._countdown_timer.start(1000)

    def stop_countdown(self) -> None:
        self._countdown_timer.stop()
        self._session.setText("")

    # ── Internals ────────────────────────────────────────────────────────────

    def _tick_countdown(self) -> None:
        self._countdown -= 1
        if self._countdown <= 0:
            self._countdown_timer.stop()
            self._session.setText("")
        else:
            self._session.setText(f"ACTIVE  {self._countdown}s")

    @staticmethod
    def _make_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("indicator_label")
        lbl.setProperty("active", "false")
        return lbl

    @staticmethod
    def _refresh(widget: QLabel) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
