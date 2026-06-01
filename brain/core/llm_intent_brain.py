import json
import io
from loguru import logger
from core.config_loader import config

class LLMIntentBrain:
    def __init__(self):
        self.client = None
        self._model = config.get("brain.llm_model", "llama-3.1-8b-instant")
        
    def _init_client(self):
        if self.client is None:
            api_key = config.groq_api_key()
            if api_key:
                from groq import Groq
                self.client = Groq(api_key=api_key)

    def classify(self, text: str, context: str = "") -> dict | None:
        self._init_client()
        if not self.client:
            return None
            
        system_prompt = f"""
You are the Intent Brain for AURA. 
Convert the user speech into a structured JSON command.
Context: {context}

IMPORTANT: The user input is from a Speech-to-Text (STT) engine. It may contain phonetic errors (e.g., "Such was" instead of "Search for", "on Google" for web search). Silently correct these STT errors based on context before extracting slots.

Available Intents: 
- app_control (action: open_app, close_app)
- browser_control (action: open_website, search_web)
- system_control (action: shutdown, restart, lock, sleep, volume, brightness)
- media_control (action: play, pause, next, prev)
- screenshot (action: capture, open_latest)
- whatsapp (action: send_message, open_chat)
- email (action: draft_email)
- time (action: get_time)
- weather (action: get_weather)
- conversation (action: chat)

Output Format:
{{
  "intent": "category",
  "action": "specific_action",
  "slots": {{"app": "name", "site": "name", "query": "corrected text to search", "target": "name", "message": "text"}},
  "confidence": 0.0-1.0,
  "needs_clarification": false,
  "clarification_question": "",
  "requires_confirmation": false,
  "reason": "explanation of corrections and intent"
}}
"""
        try:
            resp = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            logger.error("LLM Intent Brain failed: {}", e)
            return None

llm_brain = LLMIntentBrain()
