"""
speech/response_formatter.py — Prepare LLM/action output for spoken TTS delivery.

- Strips markdown (bold, bullets, code fences, headers)
- Truncates very long responses to MAX_WORDS
- Ensures a final period for natural TTS cadence
"""

from __future__ import annotations
import re

MAX_WORDS = 120


def format_for_speech(text: str) -> str:
    """Clean and trim text for natural TTS delivery."""
    if not text:
        return ""

    # Strip markdown formatting
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)   # code blocks
    text = re.sub(r"`[^`]+`", "", text)                       # inline code
    text = re.sub(r"#{1,6}\s*", "", text)                     # headers
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)     # bold/italic
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)  # bullets
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)    # links → label
    text = re.sub(r"\n+", " ", text)                          # newlines → space
    text = re.sub(r"\s{2,}", " ", text)                       # collapse spaces

    text = text.strip()

    # Truncate to MAX_WORDS
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS]) + "."

    # Ensure ends with punctuation
    if text and text[-1] not in ".!?":
        text += "."

    return text


def aura_prefix(action: str) -> str:
    """Short spoken prefix for action acknowledgements."""
    prefixes = {
        "open_app":    "Opening that for you.",
        "close_app":   "Closing that now.",
        "screenshot":  "Screenshot taken.",
        "volume":      "Volume adjusted.",
        "brightness":  "Brightness adjusted.",
        "search":      "Searching now.",
        "weather":     "",
        "news":        "",
        "reminder":    "Reminder set.",
        "error":       "I ran into an issue.",
        "confirm":     "Please confirm: ",
        "denied":      "I can't do that without confirmation.",
    }
    return prefixes.get(action, "")
