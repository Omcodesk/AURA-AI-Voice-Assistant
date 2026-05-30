"""
services/confirmation_service.py — Manages the pending state for commands needing confirmation.
"""

from typing import Optional
from loguru import logger
from core.result_types import ParsedCommand
from PySide6.QtCore import QTimer

class ConfirmationService:
    def __init__(self):
        self.pending_cmd: Optional[ParsedCommand] = None
        self._timer: Optional[QTimer] = None

    def request_confirmation(self, cmd: ParsedCommand, timeout_ms: int = 10000) -> None:
        """Sets the pending command and optionally starts a timeout timer."""
        self.pending_cmd = cmd
        logger.info("Awaiting confirmation for: {} / {}", cmd.intent, cmd.action)
        
        # We can implement a QTimer based timeout here or manually handle it
        # For V1, the timeout can be handled by the main_window session timeout
        
    def resolve(self, confirmed: bool) -> Optional[ParsedCommand]:
        """Resolves the confirmation state and returns the pending command if confirmed."""
        cmd = self.pending_cmd
        self.pending_cmd = None
        
        if confirmed:
            logger.info("Command confirmed.")
            return cmd
        else:
            logger.info("Command cancelled via confirmation.")
            return None
            
    @property
    def is_awaiting_confirmation(self) -> bool:
        return self.pending_cmd is not None

# Singleton
confirmation_service = ConfirmationService()
