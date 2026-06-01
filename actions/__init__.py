"""
actions/__init__.py — Exposes Phase 3 action modules and conversation features.
"""

from actions.conversation import conversation

# Import modules to trigger their registry.register() calls
import actions.app_control
import actions.browser_control
import actions.media_control
import actions.news_service
import actions.screenshot_service
import actions.system_control
import actions.weather_service
import actions.whatsapp
import actions.email_web
import actions.vision_control
import actions.computer_control
import actions.file_editor
import actions.terminal_control

__all__ = ["conversation"]
