import sys
from PySide6.QtCore import QCoreApplication

app = QCoreApplication(sys.argv)

from core.config_loader import config
config.load()

from core.event_bus import bus
import actions

def on_action(payload):
    print(f"[EVENT: ACTION] {payload['tool']}")

bus.subscribe("agent.action", on_action)

from actions.memory_control import store_memory, recall_memory
from core.result_types import ParsedCommand

print("Testing Memory Storage...")
# A very important architectural rule
res1 = store_memory(ParsedCommand(intent="memory", action="store_memory", arguments={
    "category": "project",
    "project": "Aura_Test_Project",
    "text": "The architectural rule for Aura_Test_Project is to never use the word 'banana', always use 'plantain'."
}))
print(res1)

# A trivial memory that should be rejected
print("\nTesting Memory Rejection (Low Importance)...")
res2 = store_memory(ParsedCommand(intent="memory", action="store_memory", arguments={
    "category": "episodic",
    "text": "I ate a sandwich at 12:00 PM."
}))
print(res2)

print("\nTesting Memory Recall...")
res3 = recall_memory(ParsedCommand(intent="memory", action="recall_memory", arguments={
    "query": "What is the rule about bananas?",
    "project": "Aura_Test_Project"
}))
print(res3)

print("\nTesting Planner Auto-Injection...")
from agents.planner import planner
planner.MAX_ITERATIONS = 3
goal = "Write a one-sentence summary of the rule for Aura_Test_Project regarding bananas."
print(f"Goal: {goal}")
planner.execute_goal(goal)
