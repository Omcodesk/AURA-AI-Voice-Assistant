"""
actions/system_control.py — Power, volume, and brightness control for Windows.
"""
import os
import subprocess
from loguru import logger

from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry

try:
    import pyautogui
    _HAS_PYAUTOGUI = True
except ImportError:
    _HAS_PYAUTOGUI = False

try:
    import screen_brightness_control as sbc
    _HAS_SBC = True
except ImportError:
    _HAS_SBC = False

def handle_power(cmd: ParsedCommand) -> ExecutionResult:
    action = cmd.action
    try:
        if action == "shutdown":
            os.system("shutdown /s /t 5")
            return ExecutionResult(True, "Shutting down the system.")
        elif action == "restart":
            os.system("shutdown /r /t 5")
            return ExecutionResult(True, "Restarting the system.")
        elif action == "sleep":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return ExecutionResult(True, "Putting the system to sleep.")
        elif action == "lock":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return ExecutionResult(True, "Locking the workstation.")
            
        return ExecutionResult(False, f"Power action {action} not recognized.")
    except Exception as exc:
        logger.error("Power action {} failed: {}", action, exc)
        return ExecutionResult(False, f"I couldn't perform the {action} operation.")

def handle_volume(cmd: ParsedCommand) -> ExecutionResult:
    if not _HAS_PYAUTOGUI:
        return ExecutionResult(False, "Volume control relies on pyautogui which is not installed.")
        
    raw_intent = cmd.source_text.lower()
    amount = cmd.arguments.get("amount", 10) # Default to 10% change
    steps = max(1, amount // 2) # each press is typically 2% on Windows
    
    logger.info("Volume Service Attempt | Raw: '{}' | amount: {} | steps: {}", raw_intent, amount, steps)
    
    try:
        if "up" in raw_intent or "increase" in raw_intent:
            pyautogui.press('volumeup', presses=steps)
            msg = f"Increasing volume by {amount} percent."
        elif "down" in raw_intent or "decrease" in raw_intent:
            pyautogui.press('volumedown', presses=steps)
            msg = f"Decreasing volume by {amount} percent."
        elif "unmute" in raw_intent:
            # Most windows drivers toggle with the same key, but we label it correctly
            pyautogui.press('volumemute')
            msg = "Unmuting volume."
        elif "mute" in raw_intent:
            pyautogui.press('volumemute')
            msg = "Muting volume."
        else:
            return ExecutionResult(False, "I didn't catch whether to turn the volume up or down.")
            
        logger.info("Volume Service Status | Success | {}", msg)
        return ExecutionResult(True, msg)
    except Exception as exc:
        logger.error("Volume Service Status | Failed | Error: {}", exc)
        return ExecutionResult(False, "I couldn't change the volume.")

def handle_brightness(cmd: ParsedCommand) -> ExecutionResult:
    if not _HAS_SBC:
        return ExecutionResult(False, "Brightness control is not available on this device.")
        
    raw_intent = cmd.source_text.lower()
    amount = cmd.arguments.get("amount", 10)
    
    try:
        current = sbc.get_brightness()[0]
        # Check if an absolute amount was provided
        target_amount = cmd.arguments.get("amount")
        
        if cmd.action == "brightness_set" and target_amount is not None:
            target = max(0, min(100, target_amount))
            sbc.set_brightness(target)
            return ExecutionResult(True, f"Setting brightness to {target} percent.")
        
        if "up" in raw_intent or "increase" in raw_intent:
            target = min(100, current + amount)
            sbc.set_brightness(target)
            return ExecutionResult(True, "Increasing brightness.")
        elif "down" in raw_intent or "decrease" in raw_intent:
            target = max(0, current - amount)
            sbc.set_brightness(target)
            return ExecutionResult(True, "Decreasing brightness.")
        else:
            return ExecutionResult(False, "I didn't catch if you wanted to increase or decrease the brightness.")
    except Exception as exc:
        logger.error("Brightness control failed: {}", exc)
        return ExecutionResult(False, "Brightness control is not available on this device.")

registry.register("system_control", "shutdown", handle_power)
registry.register("system_control", "restart", handle_power)
registry.register("system_control", "sleep", handle_power)
registry.register("system_control", "lock", handle_power)

registry.register("system_control", "volume", handle_volume)
registry.register("system_control", "brightness", handle_brightness)
registry.register("system_control", "brightness_set", handle_brightness)
registry.register("system_control", "brightness_up", handle_brightness)
registry.register("system_control", "brightness_down", handle_brightness)
