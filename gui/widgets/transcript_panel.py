"""
gui/widgets/transcript_panel.py — Scrollable card-based conversation transcript.
"""

from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea,
    QFrame, QLabel, QSizePolicy,
)


class TranscriptCard(QFrame):
    def __init__(self, role: str, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("user_card" if role == "user" else "aura_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        who_label = QLabel("YOU" if role == "user" else "AURA")
        who_label.setObjectName("card_who")
        who_label.setProperty("role", role)
        who_label.style().unpolish(who_label)
        who_label.style().polish(who_label)

        text_label = QLabel(text)
        text_label.setObjectName("card_text")
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addWidget(who_label)
        layout.addWidget(text_label)


class TranscriptPanel(QWidget):
    """Scrollable panel that holds conversation cards, newest at bottom."""

    MAX_CARDS = 50

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("transcript_scroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)
        self._layout.addStretch()

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

        self._cards: list[TranscriptCard] = []

    def add_user(self, text: str) -> None:
        self._add_card("user", text)

    def add_aura(self, text: str) -> None:
        self._add_card("aura", text)

    def clear(self) -> None:
        for card in self._cards:
            self._layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

    def _add_card(self, role: str, text: str) -> None:
        if len(self._cards) >= self.MAX_CARDS:
            oldest = self._cards.pop(0)
            self._layout.removeWidget(oldest)
            oldest.deleteLater()

        card = TranscriptCard(role, text)
        self._layout.insertWidget(self._layout.count() - 1, card)  # before stretch
        self._cards.append(card)

        # Auto-scroll to bottom
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())
