"""
actions/conversation.py — LLM conversation handler.

Supports two providers, switched via config/settings.yaml:
  provider: groq    → Groq API (llama-3.1-8b-instant etc.) — fastest, recommended
  provider: ollama  → local Ollama                          — fully offline

The LLM is ONLY used for:
  - Natural conversation
  - Paraphrasing / spoken summary formatting
  - Soft intent interpretation
It never directly executes system or browser actions.
"""

from __future__ import annotations
from loguru import logger
from core.config_loader import config

SYSTEM_PROMPT = """You are Aura, an advanced AI assistant running on a Windows PC.
You are calm, professional, efficient, and friendly.
Your responses will be spoken aloud via text-to-speech, so:
- Be concise. Default to 1-2 sentences unless more detail is explicitly requested.
- Never use markdown, bullet points, code blocks, or special formatting.
- Speak naturally and directly. Address the user in second person.
- If you don't know something, say so briefly.
- Never claim to execute a system action you cannot actually perform."""


class ConversationHandler:

    def __init__(self):
        self._provider = config.get("llm.provider", "groq").lower()
        self._model    = config.get("llm.model", "llama-3.1-8b-instant")
        self._timeout  = config.get("llm.timeout", 15)
        self._max_hist = config.get("llm.max_history_turns", 10)
        self._history: list[dict] = []

        logger.info("ConversationHandler: provider={} model={}", self._provider, self._model)

    # ── Public API ──────────────────────────────────────────────────────────

    def chat(self, user_text: str) -> str:
        """Generate a spoken response for the user's message."""
        self._history.append({"role": "user", "content": user_text})
        self._trim_history()

        if self._provider == "groq":
            reply = self._groq_chat()
        elif self._provider == "ollama":
            reply = self._ollama_chat()
        else:
            reply = f"Unknown LLM provider '{self._provider}'. Check config/settings.yaml."

        self._history.append({"role": "assistant", "content": reply})
        logger.debug("LLM reply ({}): '{}'", self._provider, reply[:100])
        return reply

    def summarize_for_speech(self, raw_data: str, context: str = "") -> str:
        """Reformat raw data (weather JSON, news text) for natural spoken delivery."""
        prompt = (
            f"Reformat the following for natural spoken English in 1-2 sentences. "
            f"Be extremely concise but friendly. No markdown. No bullet points. Context: {context}\n\n{raw_data}"
        )
        tmp = self._history
        self._history = [{"role": "user", "content": prompt}]
        result = self._groq_chat() if self._provider == "groq" else self._ollama_chat()
        self._history = tmp
        return result

    def reset_history(self) -> None:
        self._history = []

    # ── Groq provider ───────────────────────────────────────────────────────

    def _groq_chat(self) -> str:
        try:
            from groq import Groq
            client = Groq(api_key=config.groq_api_key())
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._history
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.7,
                max_tokens=200,
                timeout=self._timeout,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("Groq LLM error: {}", exc)
            return self._fallback(self._history[-1]["content"] if self._history else "")

    # ── Ollama provider ─────────────────────────────────────────────────────

    def _ollama_chat(self) -> str:
        try:
            import ollama
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._history
            response = ollama.chat(
                model=self._model,
                messages=messages,
                options={"temperature": 0.7, "num_predict": 200},
            )
            return response["message"]["content"].strip()
        except ImportError:
            logger.error("ollama package not installed: pip install ollama")
            return "Ollama is not installed. Run: pip install ollama"
        except Exception as exc:
            logger.error("Ollama error: {}", exc)
            return "I'm having trouble connecting to Ollama. Make sure it's running."

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _trim_history(self) -> None:
        max_msgs = self._max_hist * 2   # each turn = user + assistant
        if len(self._history) > max_msgs:
            self._history = self._history[-max_msgs:]

    @staticmethod
    def _fallback(text: str) -> str:
        """Minimal offline response when all providers fail."""
        lower = text.lower()
        if any(w in lower for w in ("hello", "hi ", "hey")):
            return "Hello. Aura at your service, though my reasoning engine is currently offline."
        if "time" in lower:
            from datetime import datetime
            return f"It is {datetime.now().strftime('%I:%M %p')}."
        return "I understood you, but my reasoning engine is currently unavailable."


# Module-level singleton
conversation = ConversationHandler()
