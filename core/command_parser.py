"""
core/command_parser.py — Transforms raw router intents into structured ParsedCommands.
"""

from core.result_types import ParsedCommand
from core.policy_engine import policy_engine

class CommandParser:
    """Normalizes raw (intent, args, text) into a ParsedCommand."""
    
    def parse(self, raw_intent: str, args: dict, text: str) -> ParsedCommand:
        intent = "unsupported"
        action = raw_intent
        target = ""

        # Map legacy router intents to Phase 3 intent categories and actions
        if raw_intent in ("shutdown", "restart", "sleep", "lock"):
            intent = "system_control"
            action = raw_intent
        elif raw_intent in ("volume_up", "volume_down", "mute", "unmute"):
            intent = "system_control"
            action = "volume"
        elif raw_intent in ("brightness_up", "brightness_down"):
            intent = "system_control"
            action = "brightness"
        elif raw_intent in ("media_play", "media_pause", "media_next", "media_prev", "media_stop"):
            intent = "media_control"
            action = raw_intent.replace("media_", "")
        elif raw_intent in ("open_app", "close_app"):
            app_name = args.get("app", "")
            if "whatsapp" in app_name.lower():
                intent = "whatsapp"
                action = "open_chat"
                target = app_name.lower().replace("whatsapp chat with", "").replace("whatsapp", "").strip()
            else:
                intent = "app_control"
                action = raw_intent
                target = app_name
        elif raw_intent in ("search_web", "open_website", "open_tab", "close_tab"):
            intent = "browser_control"
            action = raw_intent
            target = args.get("url", "")
        elif raw_intent == "screenshot":
            intent = "screenshot"
            action = "capture"
        elif raw_intent == "weather":
            intent = "weather"
            action = "current_weather"
            target = args.get("location", "")
        elif raw_intent == "news":
            intent = "news"
            action = "top_headlines"
        elif raw_intent in ("send_whatsapp", "open_whatsapp", "read_whatsapp"):
            intent = "whatsapp"
            if raw_intent == "send_whatsapp":
                action = "send_message"
                target = args.get("target", "")
            elif raw_intent == "open_whatsapp":
                action = "open_chat"
                target = args.get("target", "")
            else:
                action = "read_recent"
        elif raw_intent == "open_screenshot_folder":
            intent = "explorer"
            action = "open_folder"
            target = "data/screenshots"
        elif raw_intent == "draft_email":
            intent = "email"
            action = "draft_email"
            target = args.get("target", "")
        elif raw_intent == "time":
            intent = "time"
            action = "time"
        elif raw_intent == "conversation":
            intent = "conversation"
            action = "chat"
            
        cmd = ParsedCommand(
            intent=intent,
            action=action,
            target=target,
            arguments=args,
            source_text=text
        )
        
        # Apply policies
        cmd = policy_engine.apply_policies(cmd)
        
        # Phase 4 strict explicit confirmation
        dangerous_actions = ("shutdown", "restart", "lock", "sleep")
        if (cmd.intent in ("whatsapp", "email") and cmd.action in ("send_message", "draft_email")) or \
           (cmd.intent == "system_control" and cmd.action in dangerous_actions):
            cmd.requires_confirmation = True
            
        return cmd

# Singleton
command_parser = CommandParser()
