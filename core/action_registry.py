"""
core/action_registry.py — Registry of all supported Phase 3 actions.
"""

from typing import Callable, Dict, Any
from loguru import logger
from core.result_types import ParsedCommand, ExecutionResult

class ActionRegistry:
    """Central registry mapping (intent, action) to execution functions."""
    
    def __init__(self):
        # Map of intent -> action -> Callable[[ParsedCommand], ExecutionResult]
        self._registry: Dict[str, Dict[str, Callable[[ParsedCommand], ExecutionResult]]] = {}

    def register(self, intent: str, action: str, handler: Callable[[ParsedCommand], ExecutionResult]) -> None:
        """Register a handler function for a specific intent and action."""
        if intent not in self._registry:
            self._registry[intent] = {}
        self._registry[intent][action] = handler
        logger.debug("Registered action: {} -> {}", intent, action)

    def get_handler(self, intent: str, action: str) -> Callable[[ParsedCommand], ExecutionResult] | None:
        """Retrieve the handler for a specific intent and action."""
        return self._registry.get(intent, {}).get(action)

# Module-level singleton
registry = ActionRegistry()
