"""
regression_test.py — Full pipeline regression check.
Simulates natural language queries through the entire JARVIS V2 brain.
"""
import sys
import os
from pathlib import Path
from loguru import logger

# Setup paths
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

# Silence unnecessary logs for the report
logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")

from core.config_loader import config
from brain.core.fast_rule_matcher import matcher
from brain.core.slot_extractor import slot_extractor
from core.command_parser import command_parser
from services.action_dispatcher import dispatcher

# Ensure services are loaded
import actions.app_control
import actions.time_service
import actions.weather_service

def run_regression():
    config.load(ROOT)
    
    test_cases = [
        "open chrome",
        "launch chrome",
        "what time is it",
        "tell me the time",
        "weather in Saharanpur",
        "weather in Delhi today",
        "weather now",
        "how is the weather"
    ]
    
    print(f"{'INPUT':<30} | {'INTENT':<12} | {'TARGET':<15} | {'RESULT'}")
    print("-" * 100)
    
    report = []

    for text in test_cases:
        # 1. Matching
        intent = matcher.match(text) or "conversation"
        
        # 2. Extraction
        slots = slot_extractor.extract_slots(intent, text)
        
        # 3. Parsing
        cmd = command_parser.parse(intent, slots, text)
        
        # 4. Dispatch (Capture results without actually launching for the test script if possible, 
        # but the dispatcher usually returns ExecutionResult)
        result = dispatcher.dispatch(cmd)
        
        # Status calculation
        worked = "PASS" if result.success else "FAIL"
        
        line = f"{text:<30} | {cmd.intent:<12} | {cmd.target:<15} | {worked}: {result.message}"
        print(line.encode('ascii', errors='replace').decode('ascii'))
        
        report.append({
            "input": text,
            "normalized": text.lower().strip(),
            "intent": cmd.intent,
            "slots": slots,
            "action": cmd.action,
            "result": result.message,
            "status": worked
        })
        
    return report

if __name__ == "__main__":
    run_regression()
