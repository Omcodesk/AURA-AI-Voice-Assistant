import re

class MultiIntentParser:
    def __init__(self):
        # Splitting on common conjunctions
        self._split_pattern = re.compile(r"\s+(?:and|then|also)\s+", re.IGNORECASE)

    def split(self, text: str) -> list[str]:
        """
        Splits a single transcript into multiple potential command segments.
        Example: "open edge and search for weather" -> ["open edge", "search for weather"]
        """
        segments = self._split_pattern.split(text)
        return [s.strip() for s in segments if s.strip()]

multi_parser = MultiIntentParser()
