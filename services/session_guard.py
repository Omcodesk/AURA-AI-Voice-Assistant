"""
services/session_guard.py — Protects actions based on session authorization.
"""

from loguru import logger
from core.session_manager import session
from core.result_types import ParsedCommand

class SessionGuard:
    def verify_access(self, cmd: ParsedCommand) -> tuple[bool, str]:
        """
        Returns (allowed, reason_code).
        If requires_auth is True, session must be authorized.
        """
        if not cmd.requires_auth:
            return True, "allowed_no_auth_needed"
            
        if session.is_authorized:
            return True, "allowed_authorized"
            
        logger.warning("Access denied to {} / {}: unauthorized session", cmd.intent, cmd.action)
        return False, "re_auth_required"

# Singleton
session_guard = SessionGuard()
