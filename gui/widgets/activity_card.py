"""
gui/widgets/activity_card.py — Current task / action card shown below orb.
"""

from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy


class ActivityCard(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("activity_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        self._title = QLabel("CURRENT TASK")
        self._title.setObjectName("activity_title")

        self._text = QLabel("—")
        self._text.setObjectName("activity_text")
        self._text.setWordWrap(True)
        self._text.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(self._title)
        layout.addWidget(self._text)
        self.hide()

    def set_task(self, text: str) -> None:
        self._text.setText(text)
        self.show()

    def clear(self) -> None:
        self._text.setText("—")
        self.hide()
