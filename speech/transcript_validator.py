"""
speech/transcript_validator.py — Quality gate before processing a transcript.

Rejects: empty strings, single-word noise triggers, known garbage phrases,
         transcripts that are too short, and those containing only punctuation.
"""

from __future__ import annotations
import re
from loguru import logger

# Phrases that Whisper commonly hallucinates on silence / background noise
_NOISE_PHRASES = frozenset([
    "thank you", "thanks", "hmm", "uh", "um", "ah",
    "you", "bye", "the", "ok", "okay", "i",
    "thanks for watching", "thank you for watching",
    "subscribe", "like and subscribe",
    ".", ",", "!", "?", "...", "huh",
])

_PUNCTUATION_ONLY = re.compile(r"^[\s\W]+$")


class TranscriptValidator:
    MIN_CHARS = 3
    MIN_WORDS = 1

    @classmethod
    def validate(cls, text: str) -> tuple[bool, str]:
        """
        Returns (is_valid, reason).
        Callers should only proceed if is_valid is True.
        """
        if not text or not text.strip():
            return False, "empty"

        clean = text.strip().lower().rstrip(".,!?")

        if _PUNCTUATION_ONLY.match(clean):
            return False, "punctuation_only"

        if len(clean) < cls.MIN_CHARS:
            return False, "too_short"

        if clean in _NOISE_PHRASES:
            logger.debug("Transcript rejected as noise: '{}'", clean)
            return False, "noise_phrase"

        words = clean.split()
        if len(words) < cls.MIN_WORDS:
            return False, "too_few_words"

        return True, "ok"
