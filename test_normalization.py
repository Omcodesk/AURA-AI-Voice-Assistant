"""
test_normalization.py — Verifies app and site command normalization for JARVIS V2.
"""
import unittest
import sys
from unittest.mock import MagicMock

# Mocking config and other dependencies that might be imported
sys.modules['core.config_loader'] = MagicMock()
sys.modules['loguru'] = MagicMock()

from brain.core.slot_extractor import slot_extractor
from brain.core.fast_rule_matcher import matcher

class TestNormalization(unittest.TestCase):
    def test_open_normalization(self):
        cases = [
            ("open chrome", "open_app", "chrome"),
            ("open google chrome", "open_app", "chrome"),
            ("open google", "open_app", "google"),
            ("open browser", "open_app", "msedge"),
            ("open youtube", "open_app", "youtube"),
            ("open spotify", "open_app", "spotify"),
            ("open email", "open_app", "email")
        ]
        
        for text, expected_intent, expected_target in cases:
            intent = matcher.match(text)
            self.assertEqual(intent, expected_intent, f"Failed intent for '{text}'")
            
            slots = slot_extractor.extract_slots(intent, text)
            # Both apps and sites are currently placed in the 'app' slot for 'open_app' intent
            # based on my SlotExtractor update
            self.assertEqual(slots.get("app"), expected_target, f"Failed target for '{text}'")

if __name__ == "__main__":
    unittest.main()
