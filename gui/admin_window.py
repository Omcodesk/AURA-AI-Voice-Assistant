"""
gui/admin_window.py — Settings / Admin screen (Phase 1 read-only view).
Full edit functionality added in Phase 2-3.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QScrollArea, QFrame,
)

from core.config_loader import config


def _section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setObjectName("section_title")
    return lbl


class AdminWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("screen_panel")

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(16)

        # ── Header ─────────────────────────────────────────────────────────
        title = QLabel("SETTINGS  &  ADMIN")
        title.setStyleSheet("font-size: 20px; font-weight: 700; letter-spacing: 4px; color: #00D4FF;")
        root.addWidget(title)
        root.addSpacing(8)

        # ── Wake phrase ────────────────────────────────────────────────────
        root.addWidget(_section("WAKE PHRASE"))
        grid1 = QGridLayout()
        grid1.setSpacing(10)
        grid1.addWidget(QLabel("Phrase"), 0, 0)
        wake_edit = QLineEdit(config.get("wake.phrase", "take control"))
        wake_edit.setReadOnly(True)
        grid1.addWidget(wake_edit, 0, 1)
        grid1.addWidget(QLabel("Engine"), 1, 0)
        wake_eng = QLineEdit("Groq Whisper  (whisper-large-v3-turbo)")
        wake_eng.setReadOnly(True)
        grid1.addWidget(wake_eng, 1, 1)
        root.addLayout(grid1)
        root.addSpacing(8)

        # ── STT ────────────────────────────────────────────────────────────
        root.addWidget(_section("SPEECH-TO-TEXT"))
        grid2 = QGridLayout()
        grid2.setSpacing(10)
        grid2.addWidget(QLabel("Provider"), 0, 0)
        grid2.addWidget(QLineEdit("Groq  —  whisper-large-v3-turbo"), 0, 1)
        root.addLayout(grid2)
        root.addSpacing(8)

        # ── TTS ────────────────────────────────────────────────────────────
        root.addWidget(_section("TEXT-TO-SPEECH"))
        grid3 = QGridLayout()
        grid3.setSpacing(10)
        grid3.addWidget(QLabel("Engine"), 0, 0)
        tts_combo = QComboBox()
        tts_combo.addItems(["pyttsx3 (active)", "piper (upgrade)"])
        tts_combo.setEnabled(False)
        grid3.addWidget(tts_combo, 0, 1)
        grid3.addWidget(QLabel("Rate"), 1, 0)
        grid3.addWidget(QLineEdit(str(config.get("tts.rate", 175))), 1, 1)
        root.addLayout(grid3)
        root.addSpacing(8)

        # ── LLM ────────────────────────────────────────────────────────────
        root.addWidget(_section("LOCAL / CLOUD LLM"))
        grid4 = QGridLayout()
        grid4.setSpacing(10)
        grid4.addWidget(QLabel("Provider"), 0, 0)
        grid4.addWidget(QLineEdit(config.get("llm.provider", "groq").upper()), 0, 1)
        grid4.addWidget(QLabel("Model"), 1, 0)
        grid4.addWidget(QLineEdit(config.get("llm.model", "llama-3.1-8b-instant")), 1, 1)
        grid4.addWidget(QLabel("Host"), 2, 0)
        host_val = config.ollama_host() if config.get("llm.provider") == "ollama" else "api.groq.com"
        grid4.addWidget(QLineEdit(host_val), 2, 1)
        root.addLayout(grid4)
        root.addSpacing(8)

        # ── Session ────────────────────────────────────────────────────────
        root.addWidget(_section("SESSION"))
        grid5 = QGridLayout()
        grid5.setSpacing(10)
        grid5.addWidget(QLabel("Active window (s)"), 0, 0)
        grid5.addWidget(QLineEdit(str(config.get("session.active_window_timeout", 300))), 0, 1)
        grid5.addWidget(QLabel("Auto-lock (min)"), 1, 0)
        grid5.addWidget(QLineEdit(str(config.get("session.auto_lock_minutes", 10))), 1, 1)
        root.addLayout(grid5)
        root.addSpacing(8)

        # ── Face auth ──────────────────────────────────────────────────────
        root.addWidget(_section("FACE AUTHENTICATION  —  PHASE 2"))
        note = QLabel("Face enrollment and multi-user management unlock in Phase 2.")
        note.setStyleSheet("color: #3D5A7A; font-size: 12px;")
        enroll_btn = QPushButton("ENROLL NEW USER")
        enroll_btn.setObjectName("action_btn")
        enroll_btn.setEnabled(False)
        root.addWidget(note)
        root.addWidget(enroll_btn)
        root.addSpacing(8)

        root.addStretch()

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
