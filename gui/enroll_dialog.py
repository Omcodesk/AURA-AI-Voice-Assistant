"""
gui/enroll_dialog.py — Modal enrollment dialog.

Shows a name input + live camera feed during capture.
Called from the admin screen "Enrol New User" button or
from AuthWindow when the registry is empty.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QMessageBox,
)
from loguru import logger


class EnrollDialog(QDialog):
    """
    Simple dialog: enter name → click START ENROL → auth_window does the rest.
    """
    enroll_start = Signal(str)   # emitted with the name to begin enrollment

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AURA — Enrol New User")
        self.setFixedSize(420, 220)
        self.setModal(True)
        self.setStyleSheet(
            "QDialog { background: #070B14; }"
            "QLabel { color: #7B9DB5; font-size: 13px; }"
            "QLineEdit { background: #0D1928; color: #E8F4FE; border: 1px solid #0D2840;"
            "           border-radius: 6px; padding: 8px; font-size: 14px; }"
            "QPushButton { background: #003D5C; color: #00D4FF; border: 1px solid #0066A0;"
            "              border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 700; }"
            "QPushButton:hover { background: #004D73; }"
            "QPushButton:disabled { color: #3D5A7A; border-color: #1A2A3A; }"
        )
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(24, 24, 24, 24)

        title = QLabel("ENROL NEW USER")
        title.setStyleSheet(
            "color: #00D4FF; font-size: 18px; font-weight: 700; letter-spacing: 3px;"
        )
        root.addWidget(title)

        root.addWidget(QLabel("Enter your name:"))

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Om")
        self._name_edit.textChanged.connect(self._on_name_changed)
        root.addWidget(self._name_edit)

        note = QLabel("Your face will be captured via webcam (20 frames).")
        note.setStyleSheet("color: #3D5A7A; font-size: 11px;")
        root.addWidget(note)

        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("START ENROLMENT")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start)
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setStyleSheet(
            "background: transparent; color: #3D5A7A; border: 1px solid #1A2A3A;"
            "border-radius: 6px; padding: 8px 20px;"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._start_btn)
        root.addLayout(btn_row)

    @Slot(str)
    def _on_name_changed(self, text: str):
        self._start_btn.setEnabled(len(text.strip()) >= 2)

    @Slot()
    def _on_start(self):
        name = self._name_edit.text().strip()
        if not name:
            return
        self.enroll_start.emit(name)
        self.accept()
