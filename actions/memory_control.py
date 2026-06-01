"""
actions/memory_control.py — Phase 5 Memory tools for the Planner.
"""
from core.action_registry import registry
from core.result_types import ParsedCommand, ExecutionResult
from core.event_bus import bus
from services.memory.cognitive_engine import engine
from services.memory.retrieval import retrieve_context

def store_memory(cmd: ParsedCommand) -> ExecutionResult:
    """Explicitly stores a memory."""
    category = cmd.arguments.get("category", "episodic")
    text = cmd.arguments.get("text", "")
    project = cmd.arguments.get("project", None)
    
    if not text:
        return ExecutionResult(success=False, message="Memory text is required.")
        
    stored = engine.store_memory(category, text, project)
    if stored:
        bus.publish("agent.action", {"tool": f"Stored {category} memory: {text}"})
        return ExecutionResult(success=True, message=f"Successfully stored {category} memory.")
    else:
        return ExecutionResult(success=False, message="Memory was rejected (Importance score too low).")

def recall_memory(cmd: ParsedCommand) -> ExecutionResult:
    """Explicitly queries the memory bank."""
    query = cmd.arguments.get("query", "")
    project = cmd.arguments.get("project", None)
    
    if not query:
        return ExecutionResult(success=False, message="Query is required.")
        
    context = retrieve_context(query, project=project, top_k=3)
    bus.publish("agent.action", {"tool": f"Recalled memory for: {query}"})
    
    if context:
        return ExecutionResult(success=True, message=context)
    return ExecutionResult(success=False, message="No relevant memories found.")

registry.register("memory", "store_memory", store_memory)
registry.register("memory", "recall_memory", recall_memory)
