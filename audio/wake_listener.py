"""
audio/wake_listener.py — Wake phrase detection using Groq Whisper API.

Architecture (no Vosk):
  MicStream → VadManager captures full utterance as bytes
              └─ If state is IDLE:
                   Send to Groq Whisper → check transcript for wake phrase
                   If match → emit wake_detected
              └─ If state is LISTENING:
                   Publish AUDIO_CAPTURED event for processing thread

This module provides WakeDetector — a lightweight helper used by the
main audio processor thread inside MainWindow.
"""

from __future__ import annotations
from loguru import logger


class WakeDetector:
    """
    Checks whether a captured audio segment contains the wake phrase
    by transcribing it via Groq Whisper.

    Usage:
        detector = WakeDetector("take control", stt_instance)
        is_wake, transcript = detector.check(audio_bytes)
    """

    def __init__(self, phrase: str, stt):
        """
        phrase : wake phrase (lowercased for matching)
        stt    : WhisperSTT instance (already initialised with Groq key)
        """
        self._phrase = phrase.lower().strip()
        self._stt = stt
        logger.info("WakeDetector ready — phrase: '{}'", self._phrase)

    def check(self, audio: bytes) -> tuple[bool, str]:
        """
        Transcribe audio and check for the wake phrase.

        Returns:
            (True, transcript)  if wake phrase found
            (False, transcript) otherwise
        """
        transcript = self._stt.transcribe(audio)
        import string
        clean_transcript = transcript.lower().translate(str.maketrans('', '', string.punctuation))
        matched = self._phrase in clean_transcript
        if matched:
            logger.info("Wake phrase detected in: '{}'", transcript)
        return matched, transcript
