"""
actions/media_control.py — Controls system media.
"""
from loguru import logger
from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry

try:
    import pyautogui
    _HAS_PYAUTOGUI = True
except ImportError:
    _HAS_PYAUTOGUI = False
    logger.warning("pyautogui not installed; media controls will not work.")

def handle_media(cmd: ParsedCommand) -> ExecutionResult:
    if not _HAS_PYAUTOGUI:
        return ExecutionResult(False, "Media control library is missing on this system.")
        
    action = cmd.action
    logger.info("Media Service Attempt | Raw: '{}' | Action: '{}'", cmd.source_text, action)
    
    key = None
    if action in ("play", "pause", "resume", "playpause"):
        key = "playpause"
        msg = "Toggling playback." if action == "playpause" else f"Executing {action}."
    elif action == "next":
        key = "nexttrack"
        msg = "Skipping to next track."
    elif action in ("prev", "previous"):
        key = "prevtrack"
        msg = "Returning to previous track."
    elif action == "stop":
        key = "stop"
        msg = "Stopping media."
        
    if key:
        try:
            pyautogui.press(key)
            logger.info("Media Service Status | Success | Action: {} (key: {})", action, key)
            return ExecutionResult(True, msg)
        except Exception as exc:
            logger.error("Media Service Status | Failed | Action: {} | Error: {}", action, exc)
            return ExecutionResult(False, "I couldn't control the media.")
            
    return ExecutionResult(False, f"Media action {action} is not supported.")

# Registration
registry.register("media_control", "play", handle_media)
registry.register("media_control", "pause", handle_media)
registry.register("media_control", "resume", handle_media)
registry.register("media_control", "next", handle_media)
registry.register("media_control", "prev", handle_media)
registry.register("media_control", "stop", handle_media)
registry.register("media_control", "media_control", handle_media) # Generic
