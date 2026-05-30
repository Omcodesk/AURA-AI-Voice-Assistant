"""
brain/policy.py — Risk tier classification for every intent.
Maps intent names → tier level. Tier 2+ require spoken confirmation.
"""

from __future__ import annotations
from core.config_loader import config

# Tier definitions:
#   0 = safe, no confirmation needed
#   1 = low risk
#   2 = confirm before executing (send, form submit, download)
#   3 = always confirm (delete, shutdown, restart, overwrite)

_TIER_MAP: dict[str, int] = {
    # Tier 0
    "conversation": 0,
    "time": 0,
    "weather": 0,
    "news": 0,
    "search_web": 0,
    "open_app": 0,
    "screenshot": 0,
    "media_play": 0,
    "media_pause": 0,
    "volume_up": 0,
    "volume_down": 0,
    "volume_set": 0,
    "brightness_up": 0,
    "brightness_down": 0,
    "open_folder": 0,
    "open_website": 0,
    "open_tab": 0,
    # Tier 1
    "close_app": 1,
    "media_next": 1,
    "media_prev": 1,
    "close_tab": 1,
    "switch_window": 1,
    "scroll": 1,
    # Tier 2
    "send_message": 2,
    "submit_form": 2,
    "login": 2,
    "download": 2,
    "upload": 2,
    # Tier 3
    "delete_file": 3,
    "shutdown": 3,
    "restart": 3,
    "sleep": 3,
    "overwrite": 3,
    "lock": 0,    # lock is safe (pro-security)
}


def get_tier(intent: str) -> int:
    return _TIER_MAP.get(intent, 1)    # unknown = tier 1 by default


def requires_confirmation(intent: str) -> bool:
    return get_tier(intent) >= 2


def is_safe(intent: str) -> bool:
    return get_tier(intent) == 0


def protected_action_allowed(intent: str) -> tuple[bool, str]:
    """
    Full gate: checks session authorization AND confirmation requirement.
    Returns (allowed: bool, reason: str).

    Callers should check `allowed` before executing any action.
    If reason == 're_auth_required' → trigger camera re-auth.
    If reason == 'confirm_required' → ask for spoken confirmation.
    """
    from core.session_manager import session
    return session.gate(intent)
