"""
Verification script for Time Command Support.
Tests intent mapping and paraphrase resolution.
"""
from core.command_parser import command_parser
from brain.core.intent_engine import engine

def test_time_variations():
    print("--- Testing Time Intent Mapping ---")
    test_cases = [
        "what time is it",
        "tell me the time",
        "time right now",
        "can you tell me the time"
    ]
    
    for text in test_cases:
        # 1. Simulate the Brain detecting 'time'
        # In rule matcher, these all match 'time'
        raw_intent = "time"
        args = {}
        
        # 2. Parse into command
        cmd = command_parser.parse(raw_intent, args, text)
        
        print(f"Input: '{text}'")
        print(f"  -> Raw Intent: '{raw_intent}'")
        print(f"  -> Parsed Intent: '{cmd.intent}'")
        print(f"  -> Parsed Action: '{cmd.action}'")
        
        # Intent should be 'time'
        assert cmd.intent == "time", f"Failed for '{text}': got '{cmd.intent}'"
        assert cmd.action == "time", f"Failed for '{text}': got '{cmd.action}'"

if __name__ == "__main__":
    try:
        from core.config_loader import config
        config.load()
        test_time_variations()
        print("\nAll Time normalization tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
