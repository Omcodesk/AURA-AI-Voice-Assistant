"""
gui/memory_window.py — Memory / routine viewer screen.
Phase 1: shows DB stats and recent conversation history.
Alias and routine management unlocked in Phase 5.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QScrollArea, QHeaderView,
)

from brain.memory_manager import memory


class MemoryWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("screen_panel")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(12)

        title = QLabel("MEMORY  &  ROUTINES")
        title.setStyleSheet("font-size: 20px; font-weight: 700; letter-spacing: 4px; color: #00D4FF;")
        root.addWidget(title)

        # ── Recent conversation ─────────────────────────────────────────────
        sec = QLabel("RECENT CONVERSATION")
        sec.setObjectName("section_title")
        root.addWidget(sec)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["You said", "AURA replied"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setStyleSheet(
            "QTableWidget { background: #0A0F1E; border: 1px solid #0D2040; border-radius: 8px; }"
            "QHeaderView::section { background: #0D1928; color: #3D5A7A; border: none; padding: 6px; }"
        )
        root.addWidget(self._table, stretch=1)

        btn_row = QVBoxLayout()
        refresh_btn = QPushButton("REFRESH")
        refresh_btn.setObjectName("action_btn")
        refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(refresh_btn)

        phase_note = QLabel(
            "Alias learning, routines, and preferences visible in Phase 5."
        )
        phase_note.setStyleSheet("color: #3D5A7A; font-size: 11px;")
        phase_note.setAlignment(Qt.AlignmentFlag.AlignCenter)

        root.addLayout(btn_row)
        root.addWidget(phase_note)

    @Slot()
    def refresh(self) -> None:
        turns = memory.recent_turns(20)
        self._table.setRowCount(len(turns))
        for row, turn in enumerate(reversed(turns)):
            self._table.setItem(row, 0, QTableWidgetItem(turn.user_text))
            self._table.setItem(row, 1, QTableWidgetItem(turn.aura_text))
