"""
brain/command_aliases.py — Natural language aliases → canonical intents.

User phrases are lowercased and checked against this table first
before full intent classification.
"""

from __future__ import annotations
import re

# Alias table: (regex_pattern, canonical_intent, optional_args_extractor)
_ALIASES: list[tuple[str, str]] = [
    # Time
    (r"\bwhat.*(time|clock)\b",                         "time"),
    (r"\bwhat('s| is) today\b",                         "time"),

    # Weather
    (r"\bweather\b",                                    "weather"),
    (r"\bwill it rain\b",                               "weather"),
    (r"\bforecast\b",                                   "weather"),

    # News
    (r"\bnews\b",                                       "news"),
    (r"\bheadlines?\b",                                 "news"),

    # Screenshots
    (r"\btake (a )?screenshot\b",                       "screenshot"),
    (r"\bscreenshot\b",                                 "screenshot"),
    (r"\bcapture (the )?screen\b",                      "screenshot"),

    # Volume
    (r"\bvolume up\b",                                  "volume_up"),
    (r"\bincrease volume\b",                            "volume_up"),
    (r"\bvolume down\b",                                "volume_down"),
    (r"\bdecrease volume\b",                            "volume_down"),
    (r"\bmute\b",                                       "volume_down"),

    # Brightness
    (r"\bbrightness up\b",                              "brightness_up"),
    (r"\bbrightness down\b",                            "brightness_down"),
    (r"\bincrease brightness\b",                        "brightness_up"),
    (r"\bdecrease brightness\b",                        "brightness_down"),

    # Apps
    (r"\bopen\b",                                       "open_app"),
    (r"\blaunch\b",                                     "open_app"),
    (r"\bstart\b",                                      "open_app"),
    (r"\bclose\b",                                      "close_app"),
    (r"\bkill\b",                                       "close_app"),

    # Browser
    (r"\bsearch (for |the web for )?\b",                "search_web"),
    (r"\bgoogle\b",                                     "search_web"),
    (r"\bopen (a )?new tab\b",                          "open_tab"),
    (r"\bclose (the )?tab\b",                           "close_tab"),
    (r"\bopen.*website|go to\b",                        "open_website"),

    # System control
    (r"\bshutdown|shut down\b",                         "shutdown"),
    (r"\brestart|reboot\b",                             "restart"),
    (r"\bsleep\b",                                      "sleep"),
    (r"\block (the )?(screen|computer|system|pc)\b",    "lock"),

    # Media
    (r"\bplay\b",                                       "media_play"),
    (r"\bpause\b",                                      "media_pause"),
    (r"\bnext (song|track)\b",                          "media_next"),
    (r"\bprevious (song|track)\b",                      "media_prev"),
    (r"\bskip\b",                                       "media_next"),

    # Reminders
    (r"\bremind me\b",                                  "set_reminder"),
    (r"\bset (a |an )?alarm\b",                         "set_reminder"),
    (r"\bset (a |an )?reminder\b",                      "set_reminder"),

    # Phase 4 - Communication
    (r"\bsend.*whatsapp\b",                             "send_whatsapp"),
    (r"\bwhatsapp to\b",                                "send_whatsapp"),
    (r"\bemail to\b",                                   "draft_email"),
    (r"\bopen.*whatsapp\b",                             "open_whatsapp"),
    (r"\bwhatsapp\b",                                   "open_whatsapp"),
    (r"\bread.*(recent|message)\b",                     "read_whatsapp"),
    (r"\bcheck.*chat\b",                                "read_whatsapp"),
    (r"\bemail\b",                                      "draft_email"),
    (r"\bmail\b",                                       "draft_email"),

    # Files
    (r"\bdelete\b",                                     "delete_file"),
    (r"\bopen.*screenshot\b",                           "open_screenshot_folder"),
    (r"\bopen (the )?(folder|directory)\b",             "open_folder"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), intent) for p, intent in _ALIASES]


def match_alias(text: str) -> str | None:
    """Return canonical intent if text matches an alias pattern, else None."""
    for pattern, intent in _COMPILED:
        if pattern.search(text):
            return intent
    return None
