"""
services/action_dispatcher.py — Dispatches parsed commands to registered handlers.
"""

from loguru import logger
from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry

class ActionDispatcher:
    def dispatch(self, cmd: ParsedCommand) -> ExecutionResult:
        """Finds and executes the correct handler for a command."""
        logger.info("Dispatching command: {} / {} (target='{}', args={})", 
                    cmd.intent, cmd.action, cmd.target, cmd.arguments)
        
        handler = registry.get_handler(cmd.intent, cmd.action)
        if not handler:
            logger.warning("No handler registered for {} / {}", cmd.intent, cmd.action)
            return ExecutionResult(
                success=False,
                message=f"I don't know how to execute {cmd.action} yet."
            )
            
        try:
            result = handler(cmd)
            return result
        except Exception as exc:
            logger.exception("Error executing {} / {}: {}", cmd.intent, cmd.action, exc)
            return ExecutionResult(
                success=False,
                message=f"I encountered an error while trying to {cmd.action}."
            )

# Singleton
dispatcher = ActionDispatcher()
