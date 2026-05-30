"""
Verification script for Chrome Launch Reliability.
Tests slot extraction, normalization, and mapping.
"""
from brain.core.slot_extractor import slot_extractor
from core.command_parser import command_parser
import json

def test_chrome_variations():
    print("--- Testing Chrome Intent Normalization ---")
    test_cases = [
        "open chrome",
        "launch chrome",
        "can you open chrome",
        "please open chrome",
        "start chrome",
        "open the browser",
        "can you launch google chrome for me?",
        "start internet"
    ]
    
    # In the real app, these would come from the router/matcher
    # but here we simulate the 'open_app' intent being detected.
    intent = "open_app"
    
    for text in test_cases:
        slots = slot_extractor.extract_slots(intent, text)
        app_name = slots.get("app", "")
        
        # Parse into command
        cmd = command_parser.parse("open_app", slots, text)
        
        print(f"Input: '{text}'")
        print(f"  -> Extracted Slot: '{app_name}'")
        print(f"  -> Command Target: '{cmd.target}'")
        
        # Target should be 'chrome'
        assert cmd.target == "chrome", f"Failed for '{text}': got '{cmd.target}'"

if __name__ == "__main__":
    try:
        from core.config_loader import config
        config.load()
        test_chrome_variations()
        print("\nAll Chrome normalization tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
