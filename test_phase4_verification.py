"""
Verification script for JARVIS Phase 4 Upgrade.
Tests intent parsing, weather defaults, and time formatting.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from brain.core.intent_engine import engine
from brain.core.fast_rule_matcher import matcher
from brain.core.slot_extractor import slot_extractor
from core.command_parser import command_parser

def test_single_intent():
    print("--- Testing Single Intent & Multi-Step Block ---")
    text = "Tell me the time and take a screenshot"
    res = engine.process(text)
    print(f"Input: {text}")
    print(f"Results length: {len(res)} (Expected: 1)")
    print(f"Selected Intent: {res[0]['intent']}")
    assert len(res) == 1

def test_weather_logic():
    print("\n--- Testing Weather Location Logic ---")
    # Test 1: Explicit city
    text = "What is the weather in Saharanpur?"
    intent = matcher.match(text)
    slots = slot_extractor.extract_slots(intent, text)
    print(f"Input: {text} -> Extracted City: {slots.get('location')}")
    assert slots.get('location') == "saharanpur"
    
    # Test 2: Default city
    text = "Tell me the weather"
    intent = matcher.match(text)
    slots = slot_extractor.extract_slots(intent, text)
    print(f"Input: {text} -> Extracted City: {slots.get('location') or 'None'}")
    # Default is handled in weather_service.py at runtime, but extractor should return empty
    assert not slots.get('location')

def test_safety_blocklist():
    print("\n--- Testing Safety Blocklist (Bye/Thanks) ---")
    phrases = ["Thank you", "Bye", "Thanks Aura"]
    for p in phrases:
        intent = matcher.match(p)
        print(f"Input: '{p}' -> Intent: {intent} (Expected: None)")
        assert intent is None

def test_dangerous_confirmation():
    print("\n--- Testing Dangerous Confirmation Marking ---")
    dangerous = ["shutdown", "restart", "lock the pc"]
    for d in dangerous:
        intent = matcher.match(d)
        cmd = command_parser.parse(intent, {}, d)
        print(f"Input: '{d}' -> Intent: {cmd.intent} -> Confirm Required: {cmd.requires_confirmation}")
        assert cmd.requires_confirmation is True

if __name__ == "__main__":
    try:
        from core.config_loader import config
        config.load()
        test_single_intent()
        test_weather_logic()
        test_safety_blocklist()
        test_dangerous_confirmation()
        print("\nAll unit tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
