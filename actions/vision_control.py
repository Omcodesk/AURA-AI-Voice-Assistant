"""
actions/vision_control.py — Vision subsystem commands for AURA.
"""

from core.action_registry import registry
from core.result_types import ParsedCommand, ExecutionResult
from vision.vlm_client import vlm_client
from loguru import logger

@registry.register("vision", "describe_screen")
def describe_screen(cmd: ParsedCommand) -> ExecutionResult:
    """Takes a screenshot and describes it."""
    
    prompt = cmd.slots.get("query", "Describe what is on my screen in a helpful and concise manner.")
    
    # Optional context if the user asks a specific question
    logger.info("Executing vision action with prompt: {}", prompt)
    
    analysis = vlm_client.analyze_screen(prompt)
    
    if analysis and "Error" not in analysis:
        return ExecutionResult(
            success=True,
            message=analysis
        )
    else:
        return ExecutionResult(
            success=False,
            message=analysis or "I'm sorry, I couldn't see the screen."
        )
