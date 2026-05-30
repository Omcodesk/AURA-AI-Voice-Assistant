"""
gui/confirmation_dialog.py — Visual confirmation overlay for risky actions.
"""
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton

class ConfirmationDialog(QDialog):
    confirmed = Signal()
    cancelled = Signal()

    def __init__(self, action_name: str, parent=None, timeout_ms: int = 10000):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        self.action_name = action_name
        self._timeout_ms = timeout_ms
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        
        self._build_ui()
        self._timer.start(timeout_ms)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        container = QLabel()
        container.setObjectName("confirm_box")
        container.setStyleSheet(
            "background: rgba(10, 20, 35, 0.95); "
            "border: 2px solid #FF3355; "
            "border-radius: 12px;"
        )
        lay = QVBoxLayout(container)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel(f"CONFIRM ACTION")
        title.setStyleSheet("color: #FF3355; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        msg = QLabel(f"Execute: {self.action_name}?\n\nSay YES to proceed, NO to cancel.")
        msg.setStyleSheet("color: #E0E0E0; font-size: 14px;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_lay = QHBoxLayout()
        btn_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_yes = QPushButton("YES")
        self.btn_yes.setStyleSheet("background: #00D4FF; color: black; padding: 6px 16px; border-radius: 4px;")
        self.btn_yes.clicked.connect(self._on_yes)
        
        self.btn_no = QPushButton("NO")
        self.btn_no.setStyleSheet("background: transparent; color: #FF3355; border: 1px solid #FF3355; padding: 6px 16px; border-radius: 4px;")
        self.btn_no.clicked.connect(self._on_no)
        
        btn_lay.addWidget(self.btn_yes)
        btn_lay.addWidget(self.btn_no)
        
        lay.addWidget(title)
        lay.addSpacing(10)
        lay.addWidget(msg)
        lay.addSpacing(20)
        lay.addLayout(btn_lay)
        
        root.addWidget(container)

    @Slot()
    def _on_yes(self):
        self._timer.stop()
        self.confirmed.emit()
        self.accept()

    @Slot()
    def _on_no(self):
        self._timer.stop()
        self.cancelled.emit()
        self.reject()

    @Slot()
    def _on_timeout(self):
        self.cancelled.emit()
        self.reject()

    def process_voice_reply(self, text: str) -> bool:
        """Returns True if the dialog consumed the text."""
        lower = text.lower()
        if "yes" in lower or "proceed" in lower or "confirm" in lower or "do it" in lower:
            self._on_yes()
            return True
        elif "no" in lower or "cancel" in lower or "stop" in lower:
            self._on_no()
            return True
        return False
