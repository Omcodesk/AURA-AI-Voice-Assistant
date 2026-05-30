"""
audio/audio_buffer.py — Thread-safe ring buffer for raw PCM audio frames.
"""

from __future__ import annotations
from collections import deque
from threading import Lock


class AudioBuffer:
    """
    Thread-safe deque-backed ring buffer.
    Stores raw PCM bytes frames (each frame = chunk_size samples * 2 bytes).
    """

    def __init__(self, maxlen: int = 500):
        """
        maxlen: max frames to hold (500 × 30 ms = 15 seconds at 16 kHz).
        """
        self._buf: deque[bytes] = deque(maxlen=maxlen)
        self._lock = Lock()

    def put(self, frame: bytes) -> None:
        with self._lock:
            self._buf.append(frame)

    def get_all(self) -> bytes:
        """Drain buffer and return all bytes concatenated."""
        with self._lock:
            data = b"".join(self._buf)
            self._buf.clear()
            return data

    def drain_list(self) -> list[bytes]:
        """Return list of frames and clear."""
        with self._lock:
            frames = list(self._buf)
            self._buf.clear()
            return frames

    def clear(self) -> None:
        with self._lock:
            self._buf.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)
