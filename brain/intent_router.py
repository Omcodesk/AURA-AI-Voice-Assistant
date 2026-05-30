from brain.core.intent_engine import engine
from core.command_parser import command_parser
from core.result_types import ParsedCommand

class IntentRouter:
    def route(self, text: str) -> ParsedCommand | list[ParsedCommand]:
        """
        Uses the Universal Intent Brain to understand the user's request.
        """
        results = engine.process(text)
        
        parsed_commands = []
        for res in results:
            # Map engine output back to ParsedCommand
            # Note: command_parser.parse takes (raw_intent, args, text)
            cmd = command_parser.parse(
                res["intent"], 
                res["slots"], 
                text
            )
            
            # Enrich with new fields
            cmd.confidence = res.get("confidence", 1.0)
            cmd.needs_clarification = res.get("needs_clarification", False)
            cmd.clarification_question = res.get("clarification_question", "")
            cmd.requires_confirmation = res.get("requires_confirmation", False)
            
            parsed_commands.append(cmd)
            
        # Always return a list for consistent processing
        return parsed_commands

# Module-level singleton
router = IntentRouter()
