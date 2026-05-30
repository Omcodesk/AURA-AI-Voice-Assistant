import time
from collections import deque

class ContextMemory:
    def __init__(self, max_age_seconds=60):
        self.max_age = max_age_seconds
        # Stores recent entities as {'type': 'app|file|site', 'value': '...', 'ts': ...}
        self._history = deque(maxlen=5) 

    def update(self, entity_type: str, value: str):
        self._history.appendleft({
            "type": entity_type,
            "value": value,
            "ts": time.time()
        })

    def resolve(self, pronoun: str) -> dict | None:
        """
        Resolves "it", "this", "that" to the latest valid context.
        """
        if pronoun not in ("it", "this", "that", "the", "system"):
            return None
            
        now = time.time()
        for item in self._history:
            if now - item["ts"] < self.max_age:
                return item
        return None

    def get_last(self, entity_type: str = None) -> str | None:
        now = time.time()
        for item in self._history:
            if entity_type and item["type"] != entity_type:
                continue
            if now - item["ts"] < self.max_age:
                return item["value"]
        return None

context_memory = ContextMemory()
