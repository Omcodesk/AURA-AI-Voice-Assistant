"""
actions/time_service.py — Provides current date and time in spoken format.
"""
from datetime import datetime
from loguru import logger

from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry

def handle_time(cmd: ParsedCommand) -> ExecutionResult:
    # Phase 4 Detailed Logging
    logger.info("Time Service Attempt | Raw: '{}' | Intent: '{}' | Action: '{}'", 
                cmd.source_text, cmd.intent, cmd.action)
                
    try:
        now = datetime.now()
        # Spoken format: "It's 04:30 PM"
        time_str = now.strftime("%I:%M %p")
        # Handle cases where user asks for date
        if "today" in cmd.source_text.lower() or "date" in cmd.source_text.lower():
            date_str = now.strftime("%A, %B %d, %Y")
            message = f"Today is {date_str}, and the time is {time_str}."
        else:
            message = f"It's {time_str}."
            
        logger.info("Time Service Status | Success | Response: '{}'", message)
        return ExecutionResult(True, message)
    except Exception as exc:
        logger.error("Time Service Status | Failed | Error: {}", exc)
        return ExecutionResult(False, "I couldn't retrieve the current time.")

# Register for 'time' intent
registry.register("time", "get_time", handle_time)
registry.register("time", "time", handle_time) # for rule-based matching
