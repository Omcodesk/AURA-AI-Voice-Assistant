"""
core/agent_events.py — Telemetry payloads for God Mode Agent Observability.
"""

from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class AgentThoughtEvent:
    """Emitted when the Planner generates reasoning."""
    agent_name: str
    thought: str
    step: int
    
    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class AgentActionEvent:
    """Emitted when the Planner decides to call a tool."""
    agent_name: str
    tool: str
    args: dict[str, Any]
    
    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class AgentResultEvent:
    """Emitted when a tool finishes and returns data to the Planner."""
    agent_name: str
    tool: str
    success: bool
    message: str
    
    def to_dict(self) -> dict:
        return asdict(self)

# We define the new event bus string constants here to keep them scoped,
# though they will be broadcasted on the main EventBus.
class AgentEventTypes:
    THOUGHT = "agent.thought"
    ACTION = "agent.action"
    RESULT = "agent.result"
    PLAN_COMPLETED = "agent.plan_completed"
    ERROR = "agent.error"
