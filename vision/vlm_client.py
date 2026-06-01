"""
vision/vlm_client.py — Communicates with Groq Vision LLMs (e.g. Llama-3.2-11b-vision-preview).
"""

from groq import Groq
from core.config_loader import config
from loguru import logger
from vision.screen_capture import capture_screen_base64

class VisionClient:
    def __init__(self):
        self.client = None
        # Using Groq's multimodal Llama model
        self.model = config.get("vision.model", "llama-3.2-11b-vision-preview")

    def _init_client(self):
        if self.client is None:
            api_key = config.groq_api_key()
            if api_key:
                self.client = Groq(api_key=api_key)
            else:
                logger.error("No Groq API key found for Vision client.")

    def analyze_screen(self, prompt: str = "Describe what is on the screen.") -> str | None:
        """Takes a screenshot and sends it to the Vision model with the given prompt."""
        self._init_client()
        if not self.client:
            return None

        b64_img = capture_screen_base64()
        if not b64_img:
            return "Error: Could not capture screen."

        logger.info("Sending screen to VLM with prompt: '{}'", prompt)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": b64_img
                                }
                            }
                        ]
                    }
                ],
                temperature=0.2,
                max_tokens=1024
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("VLM request failed: {}", e)
            return f"Error communicating with Vision model: {e}"

vlm_client = VisionClient()
