"""
audio/vad_manager.py — WebRTC VAD speech endpointing.

Consumes int16 PCM frames (30 ms @ 16 kHz).
Emits complete speech segments as concatenated bytes when silence is detected.
"""

from __future__ import annotations
from collections import deque
from typing import Callable

import webrtcvad
from loguru import logger


class VadManager:
    """
    Ring-buffer VAD that emits full utterances.

    Usage:
        vad = VadManager(on_speech_end=my_callback)
        for frame in frames:
            vad.process(frame)
    """

    SAMPLE_RATE = 16000
    FRAME_DURATION_MS = 30

    def __init__(
        self,
        on_speech_end: Callable[[bytes], None],
        aggressiveness: int = 2,
        silence_frames: int = 20,
        min_speech_frames: int = 10,
        pre_speech_pad: int = 5,
    ):
        self._vad = webrtcvad.Vad(aggressiveness)
        self._on_speech_end = on_speech_end
        self._silence_frames = silence_frames
        self._min_speech_frames = min_speech_frames
        self._pre_pad = pre_speech_pad

        # Pre-speech ring buffer (holds last N frames before speech detected)
        self._pre_buf: deque[bytes] = deque(maxlen=pre_speech_pad)

        self._in_speech = False
        self._speech_frames: list[bytes] = []
        self._silence_count = 0

    def process(self, frame: bytes) -> None:
        """Feed one 30 ms PCM frame."""
        try:
            is_speech = self._vad.is_speech(frame, self.SAMPLE_RATE)
        except Exception:
            is_speech = False

        if is_speech:
            if not self._in_speech:
                self._in_speech = True
                self._speech_frames = list(self._pre_buf)  # prepend pre-roll
                self._silence_count = 0
                logger.debug("VAD: speech start")
            self._speech_frames.append(frame)
            self._silence_count = 0

        else:
            self._pre_buf.append(frame)
            if self._in_speech:
                self._silence_count += 1
                self._speech_frames.append(frame)   # include trailing silence

                if self._silence_count >= self._silence_frames:
                    self._in_speech = False
                    n = len(self._speech_frames) - self._silence_count
                    if n >= self._min_speech_frames:
                        audio = b"".join(self._speech_frames)
                        logger.debug("VAD: speech end ({} frames)", n)
                        self._on_speech_end(audio)
                    else:
                        logger.debug("VAD: too short ({} frames), discarded", n)
                    self._speech_frames = []
                    self._silence_count = 0

    def reset(self) -> None:
        self._in_speech = False
        self._speech_frames = []
        self._silence_count = 0
        self._pre_buf.clear()
