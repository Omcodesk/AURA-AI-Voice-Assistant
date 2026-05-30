import json
import re
from pathlib import Path
from loguru import logger

class CommandNormalizer:
    def __init__(self, synonym_map_path="config/synonym_map.json"):
        self.synonyms = {}
        self._load_synonyms(synonym_map_path)
        self._stopwords = {"can", "you", "please", "could", "would", "hey", "jarvis", "aura", "kindly", "i", "want", "to"}

    def _load_synonyms(self, path):
        p = Path(path)
        if p.exists():
            try:
                with open(p, "r") as f:
                    self.synonyms = json.load(f)
            except Exception as e:
                logger.error("Failed to load synonyms: {}", e)

    def normalize(self, text: str) -> str:
        """
        1. Lowercase/Strip
        2. Remove punctuation
        3. Simple typo correction via synonyms.verbs
        4. Remove fluff words
        """
        text = text.lower().strip()
        # Remove punctuation except dots for URLs
        text = re.sub(r"[^\w\s\.]", "", text)
        
        words = text.split()
        
        # 1. Verb normalization (simple typo/alias)
        verb_map = self.synonyms.get("verbs", {})
        cleaned_words = []
        for w in words:
            if w in self._stopwords:
                continue
            if w in verb_map:
                cleaned_words.append(verb_map[w])
            else:
                cleaned_words.append(w)
                
        return " ".join(cleaned_words)

normalizer = CommandNormalizer()
