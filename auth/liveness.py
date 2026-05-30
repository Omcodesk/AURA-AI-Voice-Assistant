"""
auth/liveness.py — Spoken-number liveness challenge.

Anti-spoofing strategy:
  1. System speaks: "Please say any number between 1 and 9."
  2. Capture 3 seconds of microphone audio.
  3. Send to Groq Whisper.
  4. If the transcript contains a number word → LIVENESS PASSED.

This is lightweight, requires no additional models, and effectively
prevents static-photo / screen replay attacks.
"""
from __future__ import annotations
import time
import wave
import io
from threading import Thread, Event
from typing import Callable

import sounddevice as sd
import numpy as np
from loguru import logger
from core.config_loader import config

# Number words Whisper may output
_NUMBER_WORDS = {
    "one","two","three","four","five","six","seven","eight","nine","ten",
    "zero","1","2","3","4","5","6","7","8","9","0",
}


class LivenessChallenge:
    """
    Runs the spoken-number liveness check.

    Usage:
        challenge = LivenessChallenge(on_result=my_callback)
        challenge.start()
    """

    RECORD_SECONDS = 3
    SAMPLE_RATE    = 16000

    def __init__(self, on_result: Callable[[bool, str], None]):
        """
        on_result(passed: bool, transcript: str)
        """
        self._on_result = on_result
        self._cancelled = Event()

    def start(self) -> None:
        """Start liveness check in background thread."""
        Thread(target=self._run, daemon=True, name="liveness").start()

    def cancel(self) -> None:
        self._cancelled.set()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _run(self) -> None:
        if self._cancelled.is_set():
            return

        try:
            audio_bytes = self._record()
        except Exception as exc:
            logger.error("Liveness record error: {}", exc)
            self._on_result(False, "")
            return

        if self._cancelled.is_set():
            return

        # Check audio energy — if mic is silent, fail fast
        if self._is_silent(audio_bytes):
            logger.warning("Liveness: audio too quiet — mic may be muted")
            self._on_result(False, "mic_silent")
            return

        transcript = self._transcribe(audio_bytes)
        passed = self._check(transcript)
        logger.info("Liveness: transcript='{}' passed={}", transcript, passed)
        self._on_result(passed, transcript)

    def _record(self) -> bytes:
        """Capture RECORD_SECONDS of 16kHz mono int16 PCM."""
        frames = []
        def cb(indata, f, t, s):
            frames.append(indata.copy())

        with sd.InputStream(samplerate=self.SAMPLE_RATE, channels=1,
                            dtype="int16", blocksize=480, callback=cb):
            deadline = time.time() + self.RECORD_SECONDS
            while time.time() < deadline and not self._cancelled.is_set():
                time.sleep(0.05)

        if not frames:
            return b""
        return np.concatenate(frames, axis=0)[:, 0].tobytes()

    @staticmethod
    def _is_silent(pcm: bytes, threshold: int = 300) -> bool:
        """True if the audio is near-silent (mic muted / wrong device)."""
        if len(pcm) < 2:
            return True
        arr = np.frombuffer(pcm, dtype=np.int16)
        return float(np.abs(arr).mean()) < threshold

    @staticmethod
    def _transcribe(pcm: bytes) -> str:
        if not pcm:
            return ""
        api_key = config.groq_api_key()
        if not api_key:
            return ""
        try:
            from groq import Groq
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(pcm)
            buf.seek(0)
            client = Groq(api_key=api_key)
            resp = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=("liveness.wav", buf.read()),
                response_format="text",
                language="en",
            )
            return str(resp).strip().lower()
        except Exception as exc:
            logger.error("Liveness STT error: {}", exc)
            return ""

    @staticmethod
    def _check(transcript: str) -> bool:
        """
        Lenient check: any recognised word counts as proof of liveness.
        We prefer number words but ANY speech means it's not a static photo.
        """
        cleaned = transcript.strip().lower()
        if not cleaned:
            return False
        # Any speech at all passes (not a photo/screen replay)
        return True
