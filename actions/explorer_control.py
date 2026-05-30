"""
actions/explorer_control.py — File and folder exploration.
"""
import os
from loguru import logger
from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry

def handle_open_folder(cmd: ParsedCommand) -> ExecutionResult:
    target = cmd.target or cmd.arguments.get("path", "")
    
    if not target:
        return ExecutionResult(False, "Tell me which folder to open.")
        
    try:
        # Resolve relative to project root if needed
        full_path = os.path.abspath(target)
        if not os.path.exists(full_path):
            return ExecutionResult(False, f"Folder not found: {target}")
            
        os.startfile(full_path)
        return ExecutionResult(True, f"Opening {os.path.basename(full_path)}.")
    except Exception as e:
        logger.error("Failed to open folder {}: {}", target, e)
        return ExecutionResult(False, "I couldn't open that folder.")

registry.register("explorer", "open_folder", handle_open_folder)
