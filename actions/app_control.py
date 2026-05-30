"""
actions/app_control.py — Opens and closes basic applications based on mappings.
"""
import os
import json
import subprocess
from pathlib import Path
from loguru import logger

from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry

_MAPPINGS_FILE = Path("config/app_mappings.json")
_MAPPINGS: dict[str, str] = {}

def _load_mappings():
    global _MAPPINGS
    if _MAPPINGS_FILE.exists():
        try:
            with open(_MAPPINGS_FILE, "r") as f:
                _MAPPINGS = json.load(f)
        except Exception as e:
            logger.error("Failed to load app_mappings.json: {}", e)

_load_mappings()

def handle_open_app(cmd: ParsedCommand) -> ExecutionResult:
    target = cmd.target.lower().strip()
    source = cmd.source_text
    
    logger.info("App Control Attempt | Raw: '{}' | Target: '{}'", source, target)
    
    if not target:
        return ExecutionResult(False, "Tell me what app to open.")
        
    exe = _MAPPINGS.get(target)
    
    # Precise logging for audit
    logger.info("App Control Resolve | Canonical: '{}' | Command: '{}' | Method: 'start'", target, exe or "NOT_FOUND")
    
    if not exe:
        # Phase 4 Unified Open: Check if this is a known website fallback
        from actions.browser_control import _MAPPINGS as SITE_MAPPINGS, handle_open_website
        
        if target in SITE_MAPPINGS or ("." in target and " " not in target):
            logger.info("App Control Fallback | Target: '{}' | Rerouting to Browser", target)
            return handle_open_website(cmd)
            
        return ExecutionResult(False, f"I don't know how to open {target} yet.")
        
    try:
        # 1. Primary Method: Windows 'start'
        logger.debug("Executing primary launch command: 'start {}'", exe)
        # Using shell=True for start command
        proc = subprocess.Popen(f"start {exe}", shell=True)
        # Note: Popen returns immediately for 'start' commands
        
        # 2. Chrome Fallback logic
        if target == "chrome":
            # For Chrome, we might want to check if it actually started
            # But 'start' is usually enough. If user has issues, we could add a last-resort path:
            # e.g. "C:\Program Files\Google\Chrome\Application\chrome.exe"
            pass

        logger.info("App Control Status | Success | Command Sent")
        return ExecutionResult(True, f"Opening {target}.")
        
    except Exception as exc:
        logger.error("App Control Status | Failed | Target: {} | Error: {}", target, exc)
        
        # chrome-specific fallback if primary fails
        if target == "chrome":
            common_paths = [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe")
            ]
            for path in common_paths:
                if os.path.exists(path):
                    logger.info("Chrome Fallback Attempt | Method: 'Direct Path' | Path: '{}'", path)
                    subprocess.Popen(path)
                    return ExecutionResult(True, "Opening Chrome via direct path.")
                    
        return ExecutionResult(False, f"I couldn't open {target}. The system reported: {str(exc)}")

def handle_close_app(cmd: ParsedCommand) -> ExecutionResult:
    target = cmd.target.lower().strip()
    if not target:
        return ExecutionResult(False, "Tell me what app to close.")
        
    exe = _MAPPINGS.get(target)
    if not exe:
        return ExecutionResult(False, f"I don't have a configured process for {target}.")
        
    try:
        # Graceful terminate first; if required, hard kill could be /F 
        exit_code = os.system(f"taskkill /IM {exe}")
        if exit_code == 0:
            return ExecutionResult(True, f"Closed {target}.")
        else:
            # Usually exit code means process wasn't found
            return ExecutionResult(False, f"{target} does not seem to be running.")
    except Exception as exc:
        logger.error("Error closing app {}: {}", target, exc)
        return ExecutionResult(False, f"I couldn't close {target}.")

registry.register("app_control", "open_app", handle_open_app)
registry.register("app_control", "close_app", handle_close_app)
