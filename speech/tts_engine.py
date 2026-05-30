"""
speech/tts_engine.py — Text-to-speech via pyttsx3 (Windows SAPI male voice).

Runs in a dedicated QThread with an internal text queue.
Exposes speak(text) which is thread-safe.
Primary engine: pyttsx3 (works immediately on Windows without model downloads).
Upgrade path: set engine=piper in config for neural TTS.
"""

from __future__ import annotations
from queue import Queue, Empty

import pythoncom
from comtypes.client import CreateObject
from PySide6.QtCore import QThread, Signal
from loguru import logger


class TTSThread(QThread):
    speech_started = Signal(str)
    speech_ended = Signal()

    def __init__(self, rate: int = 175, volume: float = 0.95, parent=None):
        super().__init__(parent)
        self._rate = rate
        self._volume = volume
        self._queue: Queue[str | None] = Queue()
        self._running = True
        self._interrupted = False
        self._speaker = None
        self.daemon = True

    # ── Public API ──────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """Thread-safe: enqueue text for speech output."""
        if text and text.strip():
            self._queue.put(text.strip())

    def stop_speaking(self) -> None:
        """Clear queue and interrupt current utterance."""
        logger.debug("TTSThread: stop_speaking requested.")
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Empty:
                break
        self._interrupted = True
        if self._speaker:
            try:
                self._speaker.Speak("", 2)  # SVSFPurgeBeforeSpeak
            except Exception as e:
                logger.debug("Direct speak purge error: {}", e)

    def shutdown(self) -> None:
        """Gracefully stop the TTS thread."""
        logger.debug("TTSThread: Shutdown requested.")
        self._running = False
        self.stop_speaking()
        
        self._queue.put(None)   # unblock get() and trigger loop exit
        self.quit()             # Request Qt thread to quit
        if not self.wait(3000): # Wait for up to 3 seconds
            logger.warning("TTSThread: Wait timed out. Forcing termination.")
            self.terminate()
            self.wait()
        logger.debug("TTSThread: Shutdown complete.")

    # ── Thread body ─────────────────────────────────────────────────────────

    def run(self) -> None:
        pythoncom.CoInitialize()
        try:
            self._speaker = CreateObject("SAPI.SpVoice")
            self._configure_voice(self._speaker)

            while self._running:
                try:
                    text = self._queue.get(timeout=0.2)
                except Empty:
                    continue

                if text is None:
                    break

                logger.debug("TTS speaking: '{}'", text[:80])
                self.speech_started.emit(text)
                
                try:
                    self._interrupted = False
                    # Speak asynchronously (flag 1)
                    self._speaker.Speak(text, 1)
                    # Block worker thread until speaking completes or is interrupted
                    while self._running and not self._interrupted:
                        if self._speaker.WaitUntilDone(100):
                            break
                except Exception as exc:
                    logger.error("TTS error during Speak: {}", exc)
                
                self.speech_ended.emit()
        finally:
            self._speaker = None
            pythoncom.CoUninitialize()

    # ── Voice configuration ─────────────────────────────────────────────────

    def _configure_voice(self, speaker) -> None:
        # Convert rate (e.g. 175 -> 0, 200 -> 1, 150 -> -1)
        sapi_rate = int((self._rate - 175) / 25)
        sapi_rate = max(-10, min(10, sapi_rate))
        speaker.Rate = sapi_rate

        # Convert volume (e.g. 0.95 -> 95)
        sapi_volume = int(self._volume * 100)
        sapi_volume = max(0, min(100, sapi_volume))
        speaker.Volume = sapi_volume

        try:
            voices = speaker.GetVoices()
            male_keywords = ["david", "mark", "james", "george", "male", "en-us-guy"]
            selected_index = None

            for i in range(voices.Count):
                desc = voices.Item(i).GetDescription().lower()
                for kw in male_keywords:
                    if kw in desc:
                        selected_index = i
                        break
                if selected_index is not None:
                    break

            if selected_index is not None:
                speaker.Voice = voices.Item(selected_index)
                logger.info("TTS voice: '{}'", voices.Item(selected_index).GetDescription())
            elif voices.Count > 0:
                speaker.Voice = voices.Item(0)
                logger.warning("No male voice found; using default: '{}'", voices.Item(0).GetDescription())
            else:
                logger.warning("No TTS voices found on this system")
        except Exception as e:
            logger.error("Error configuring TTS voice: {}", e)
