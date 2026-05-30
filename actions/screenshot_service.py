"""
actions/screenshot_service.py — Captures the screen.
"""
import os
from datetime import datetime
from pathlib import Path

from loguru import logger
from PIL import ImageGrab

from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry
from core.config_loader import config

def handle_screenshot(cmd: ParsedCommand) -> ExecutionResult:
    try:
        save_dir = Path(config.get("screenshot.save_directory", "data/screenshots"))
        save_dir.mkdir(parents=True, exist_ok=True)
        
        fmt = config.get("screenshot.format", "png")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.{fmt}"
        filepath = save_dir / filename
        
        # Capture full screen
        img = ImageGrab.grab(all_screens=True)
        img.save(filepath)
        
        # Auto-open the image
        try:
            os.startfile(filepath)
        except Exception as e:
            logger.warning("Failed to auto-open screenshot: {}", e)
        
        logger.info("Screenshot saved to {}", filepath)
        return ExecutionResult(
            success=True,
            message="Screenshot saved successfully.",
            data={"path": str(filepath)}
        )
    except Exception as exc:
        logger.error("Screenshot failed: {}", exc)
        return ExecutionResult(
            success=False,
            message="I couldn't take the screenshot.",
            error_code="capture_error"
        )

# Register action
registry.register("screenshot", "capture", handle_screenshot)
