"""
agents/planner.py — Central Supervisor Agent for AURA God Mode.
"""

import json
from loguru import logger
from groq import Groq
from core.config_loader import config
from core.event_bus import bus
from core.agent_events import AgentEventTypes, AgentThoughtEvent, AgentActionEvent, AgentResultEvent
from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry
# We will import the dispatcher in the implementation method to avoid circular imports.

@registry.register("system", "echo")
def planner_echo(cmd: ParsedCommand) -> ExecutionResult:
    """A dummy action used by the Planner to return its final message back to the GUI."""
    return ExecutionResult(success=True, message=cmd.slots.get("text", "Task completed."))

class PlannerAgent:
    MAX_ITERATIONS = 5

    def __init__(self):
        self.client = None
        self._model = config.get("brain.llm_model", "llama-3.1-8b-instant")
        
    def _init_client(self):
        if self.client is None:
            api_key = config.groq_api_key()
            if api_key:
                self.client = Groq(api_key=api_key)

    def execute_goal(self, goal: str, context: str = "") -> list[dict]:
        """
        Executes a ReAct loop to achieve the goal.
        Returns a mock ParsedCommand list, typically just the conversation/TTS output 
        at the end, because the actions are dispatched dynamically inside the loop.
        """
        self._init_client()
        if not self.client:
            return [{"intent": "conversation", "action": "chat", "slots": {"text": "My LLM client is offline."}, "confidence": 1.0}]

        system_prompt = f"""
You are the AURA God Mode Planner. You are an autonomous AI operator.
Your task is to achieve the user's goal by using the available tools.
Context: {context}

Available Tools (Intents):
- app_control (action: open_app, close_app) [slots: app]
- browser_control (action: open_website, search_web) [slots: site, query]
- system_control (action: shutdown, restart, lock, sleep, volume, brightness) [slots: target]
- media_control (action: play, pause, next, prev)
- screenshot (action: capture, open_latest)
- vision (action: describe_screen) [slots: query]
- time (action: get_time)
- weather (action: get_weather)
- conversation (action: chat) [slots: text]

You must output a STRICT JSON object on every turn.
If you need to take an action, set "is_complete" to false.
If you have achieved the goal, set "is_complete" to true and provide a conversation response.

Output Format:
{{
  "thought": "Your internal reasoning for this step.",
  "action": {{
    "intent": "category",
    "action": "specific_action",
    "slots": {{"key": "value"}}
  }},
  "is_complete": false
}}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Goal: {goal}"}
        ]

        iteration = 0
        final_message = "I have completed the task."

        # ReAct Loop
        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            logger.info("Planner Loop Iteration {}/{}", iteration, self.MAX_ITERATIONS)
            
            try:
                resp = self.client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                
                content = resp.choices[0].message.content
                messages.append({"role": "assistant", "content": content})
                
                parsed = json.loads(content)
                thought = parsed.get("thought", "Thinking...")
                
                # Emit Thought Event
                bus.publish(AgentEventTypes.THOUGHT, AgentThoughtEvent(
                    agent_name="Planner",
                    thought=thought,
                    step=iteration
                ).to_dict())
                
                if parsed.get("is_complete"):
                    final_message = parsed.get("action", {}).get("slots", {}).get("text", "Task completed.")
                    bus.publish(AgentEventTypes.PLAN_COMPLETED, {"message": final_message})
                    break
                    
                # Extract Action
                action_data = parsed.get("action")
                if action_data:
                    intent = action_data.get("intent")
                    action = action_data.get("action")
                    slots = action_data.get("slots", {})
                    
                    # Emit Action Event
                    bus.publish(AgentEventTypes.ACTION, AgentActionEvent(
                        agent_name="Planner",
                        tool=f"{intent}/{action}",
                        args=slots
                    ).to_dict())
                    
                    # Construct ParsedCommand
                    cmd = ParsedCommand(
                        intent=intent,
                        action=action,
                        slots=slots,
                        target=slots.get("app") or slots.get("site") or slots.get("target") or "",
                        arguments=slots,
                        confidence=1.0
                    )
                    
                    # Dispatch (Step 2.3 Bridge)
                    from services.action_dispatcher import dispatcher
                    result = dispatcher.dispatch(cmd)
                    
                    # Emit Result Event
                    bus.publish(AgentEventTypes.RESULT, AgentResultEvent(
                        agent_name="Planner",
                        tool=f"{intent}/{action}",
                        success=result.success,
                        message=result.message
                    ).to_dict())
                    
                    # Feed result back into LLM
                    messages.append({
                        "role": "user", 
                        "content": f"Tool Execution Result (Success: {result.success}): {result.message}\nWhat is the next step?"
                    })
                else:
                    # Malformed JSON, force completion
                    break
                    
            except Exception as e:
                logger.error("Planner loop error: {}", e)
                break

        # Return a mock response to satisfy intent_engine's expectation
        return [{
            "intent": "system",
            "action": "echo",
            "slots": {"text": final_message},
            "confidence": 1.0,
            "needs_clarification": False,
            "requires_confirmation": False
        }]

planner = PlannerAgent()
