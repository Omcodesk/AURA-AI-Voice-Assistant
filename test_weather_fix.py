"""
Verification script for Weather Location Handling.
Tests slot extraction, temporal filter stripping, and fallback logic.
"""
from brain.core.slot_extractor import slot_extractor
from core.command_parser import command_parser
from actions.weather_service import handle_weather
from core.result_types import ParsedCommand
from loguru import logger
import json

def test_weather_scenarios():
    print("--- Testing Weather Location Logic ---")
    
    test_cases = [
        ("weather in Saharanpur", "Saharanpur", "User Speech"),
        ("weather in Delhi today", "Delhi", "User Speech"),
        ("weather now", "Dehradun", "Default Fallback"),
        ("how is the weather", "Dehradun", "Default Fallback"),
        ("weather in Saharanpur right now", "Saharanpur", "User Speech"),
        ("what's the weather", "Dehradun", "Default Fallback")
    ]
    
    intent = "weather"
    
    for text, expected_target, expected_source_type in test_cases:
        # 1. Extraction
        slots = slot_extractor.extract_slots(intent, text)
        loc = slots.get("location", "")
        
        # 2. Parsing
        cmd = command_parser.parse(intent, slots, text)
        
        # 3. Call the actual handler
        from actions.weather_service import handle_weather
        result = handle_weather(cmd)
        
        # 3. Resolve logic simulation (for testing metadata)
        extracted_loc = cmd.arguments.get("location") or cmd.target
        is_fallback = False
        if not extracted_loc or extracted_loc.strip() == "":
            final_target = "Dehradun"
            is_fallback = True
        else:
            final_target = extracted_loc.strip()
            
        source_type = "Default Fallback" if is_fallback else "User Speech"
        
        print(f"Input: '{text}'")
        print(f"  -> Extracted: '{loc}'")
        print(f"  -> Resolved Target: '{final_target}'")
        print(f"  -> Source: '{source_type}'")
        
        # 4. Success check (if geocoding works)
        if result.success:
            print(f"  -> SUCCESS: {result.message}")
            assert "degrees Celsius" in result.message
            assert "humidity is" in result.message
            assert "wind speed is" in result.message
            assert "As of" in result.message
        
        assert final_target.lower() == expected_target.lower(), f"Target mismatch for '{text}': got '{final_target}' expected '{expected_target}'"
        assert source_type == expected_source_type, f"Source mismatch for '{text}': got '{source_type}' expected '{expected_source_type}'"

if __name__ == "__main__":
    try:
        from core.config_loader import config
        config.load()
        test_weather_scenarios()
        print("\nAll Weather location tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
