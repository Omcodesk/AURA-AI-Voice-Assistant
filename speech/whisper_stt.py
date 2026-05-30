"""
speech/whisper_stt.py — Groq Whisper STT (whisper-large-v3-turbo).

Converts raw int16 PCM audio bytes to a WAV buffer and posts it to the
Groq transcription endpoint. Runs synchronously inside the processing thread.
"""

from __future__ import annotations
import io
import wave

from loguru import logger


class WhisperSTT:
    """Groq-backed Whisper transcription."""

    def __init__(self, api_key: str, model: str = "whisper-large-v3-turbo"):
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for STT.")
        from groq import Groq
        self._client = Groq(api_key=api_key, timeout=20.0)
        self._model = model
        logger.info("WhisperSTT ready (model={})", model)

    def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """
        Transcribe raw int16 PCM bytes.
        Returns the transcript string, or "" on failure.
        """
        if not audio_bytes:
            return ""

        wav_buffer = self._to_wav(audio_bytes, sample_rate)
        if wav_buffer is None:
            return ""

        try:
            response = self._client.audio.transcriptions.create(
                model=self._model,
                file=("audio.wav", wav_buffer),
                response_format="text",
                language="en",
            )
            text = str(response).strip()
            logger.debug("STT: '{}'", text)
            return text
        except Exception as exc:
            logger.error("Groq STT error: {}", exc)
            return ""

    @staticmethod
    def _to_wav(pcm: bytes, sample_rate: int) -> bytes | None:
        """Wrap raw int16 PCM in a WAV container."""
        try:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)          # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(pcm)
            return buf.getvalue()
        except Exception as exc:
            logger.error("WAV conversion error: {}", exc)
            return None
