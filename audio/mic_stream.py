"""
audio/mic_stream.py — sounddevice InputStream wrapper.

Runs in its own thread. Publishes int16 PCM bytes to a shared queue
consumed by the VAD/wake pipeline.
"""

from __future__ import annotations
from queue import Queue, Full

import numpy as np
import sounddevice as sd
from loguru import logger


class MicStream:
    """
    Always-on microphone stream.
    Audio frames (int16 PCM bytes, 30 ms chunks @ 16 kHz) are put into
    the shared `audio_queue` for downstream consumers.
    """

    SAMPLE_RATE = 16000
    CHANNELS = 1
    FRAME_SAMPLES = 480      # 30 ms at 16 kHz (must be 10/20/30 ms for WebRTC VAD)
    DTYPE = "int16"

    def __init__(self, audio_queue: Queue, device_index: int | None = None):
        self._q = audio_queue
        self._device = device_index
        self._stream: sd.InputStream | None = None
        self._running = False
        self._muted = False

    def set_mute(self, status: bool) -> None:
        """Prevent or allow putting data into the queue."""
        self._muted = status
        mode = "MUTED" if status else "ACTIVE"
        logger.debug("MicStream is now {}", mode)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype=self.DTYPE,
            blocksize=self.FRAME_SAMPLES,
            device=self._device,
            callback=self._callback,
        )
        self._stream.start()
        logger.info("MicStream started ({}Hz, {} samples/frame)", self.SAMPLE_RATE, self.FRAME_SAMPLES)

    def stop(self) -> None:
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        logger.info("MicStream stopped")

    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        if status:
            logger.debug("MicStream status: {}", status)
            
        if self._muted:
            return

        raw = indata[:, 0].tobytes()   # int16 bytes
        try:
            self._q.put_nowait(raw)
        except Full:
            pass  # drop frame if consumer is too slow
