"""
actions/computer_control.py — Phase 3 Actuation layer using PyAutoGUI.
"""
import pyautogui
import pygetwindow as gw
from loguru import logger

from core.action_registry import registry
from core.result_types import ParsedCommand, ExecutionResult
from core.event_bus import bus
from core.kill_switch import kill_switch
from vision.grounding import ground_element

# Global Failsafe: Moving mouse to a corner throws FailSafeException
pyautogui.FAILSAFE = True

def _verify_safety():
    """Checks the kill switch before any physical actuation."""
    kill_switch.check()

def click_element(cmd: ParsedCommand) -> ExecutionResult:
    """Finds an element by name visually and clicks it."""
    element_name = cmd.arguments.get("name", "")
    if not element_name:
        return ExecutionResult(success=False, message="No element name provided.")
        
    _verify_safety()
    bus.publish("agent.action", {"tool": f"Locating '{element_name}' on screen..."})
    
    coords = ground_element(element_name)
    if not coords:
        return ExecutionResult(success=False, message=f"Could not find '{element_name}' on screen.")
        
    x, y = coords
    _verify_safety()
    
    bus.publish("agent.action", {"tool": f"Moving mouse to click '{element_name}'"})
    try:
        # Smooth human-like movement
        pyautogui.moveTo(x, y, duration=0.5, tween=pyautogui.easeInOutQuad)
        _verify_safety()
        pyautogui.click()
        return ExecutionResult(success=True, message=f"Clicked '{element_name}'.")
    except pyautogui.FailSafeException:
        logger.warning("FailSafe triggered during click!")
        return ExecutionResult(success=False, message="User triggered mouse failsafe.")

def type_into_element(cmd: ParsedCommand) -> ExecutionResult:
    """Clicks an element and types text into it."""
    element_name = cmd.arguments.get("name", "")
    text = cmd.arguments.get("text", "")
    
    if not element_name or not text:
        return ExecutionResult(success=False, message="Element name or text missing.")
        
    # Reuse click logic
    click_result = click_element(cmd)
    if not click_result.success:
        return click_result
        
    _verify_safety()
    bus.publish("agent.action", {"tool": f"Typing '{text[:15]}...' into '{element_name}'"})
    try:
        pyautogui.typewrite(text, interval=0.02)
        return ExecutionResult(success=True, message=f"Typed into '{element_name}'.")
    except pyautogui.FailSafeException:
        return ExecutionResult(success=False, message="User triggered mouse failsafe.")

def focus_window(cmd: ParsedCommand) -> ExecutionResult:
    """Brings a window to the foreground."""
    window_name = cmd.arguments.get("name", "")
    if not window_name:
        return ExecutionResult(success=False, message="No window name provided.")
        
    _verify_safety()
    bus.publish("agent.action", {"tool": f"Focusing window '{window_name}'"})
    
    try:
        windows = gw.getWindowsWithTitle(window_name)
        if not windows:
            return ExecutionResult(success=False, message=f"Window '{window_name}' not found.")
            
        win = windows[0]
        if win.isMinimized:
            win.restore()
        win.activate()
        return ExecutionResult(success=True, message=f"Focused window '{window_name}'.")
    except Exception as e:
        logger.error(f"Focus window failed: {e}")
        return ExecutionResult(success=False, message=f"Failed to focus window: {e}")

def close_window(cmd: ParsedCommand) -> ExecutionResult:
    """Closes a specific window."""
    window_name = cmd.arguments.get("name", "")
    if not window_name:
        return ExecutionResult(success=False, message="No window name provided.")
        
    _verify_safety()
    bus.publish("agent.action", {"tool": f"Closing window '{window_name}'"})
    
    try:
        windows = gw.getWindowsWithTitle(window_name)
        if not windows:
            return ExecutionResult(success=False, message=f"Window '{window_name}' not found.")
            
        win = windows[0]
        win.close()
        return ExecutionResult(success=True, message=f"Closed window '{window_name}'.")
    except Exception as e:
        logger.error(f"Close window failed: {e}")
        return ExecutionResult(success=False, message=f"Failed to close window: {e}")

def press_shortcut(cmd: ParsedCommand) -> ExecutionResult:
    """Presses a combination of keys."""
    keys = cmd.arguments.get("keys", [])
    if not keys:
        return ExecutionResult(success=False, message="No keys provided.")
        
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split("+")]
        
    _verify_safety()
    bus.publish("agent.action", {"tool": f"Pressing shortcut {'+'.join(keys)}"})
    
    try:
        pyautogui.hotkey(*keys)
        return ExecutionResult(success=True, message=f"Pressed {'+'.join(keys)}.")
    except Exception as e:
        logger.error(f"Hotkey failed: {e}")
        return ExecutionResult(success=False, message=f"Failed to press shortcut: {e}")

# Register all tools
registry.register("computer", "click_element", click_element)
registry.register("computer", "type_into_element", type_into_element)
registry.register("computer", "focus_window", focus_window)
registry.register("computer", "close_window", close_window)
registry.register("computer", "press_shortcut", press_shortcut)
