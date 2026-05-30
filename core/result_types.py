"""
core/result_types.py — Dataclasses for parsed commands and execution results.
"""
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class ParsedCommand:
    """Represents a structured, normalized command ready for execution."""
    intent: str
    action: str
    target: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    requires_auth: bool = False
    requires_confirmation: bool = False
    source_text: str = ""

@dataclass
class ExecutionResult:
    """Standardized response from any action execution module."""
    success: bool
    message: str          # For spoken TTS or GUI display
    data: Optional[Any] = None  # Optional payload (e.g. screenshot path, weather temp)
    error_code: str = ""  # If failure occurred
