import sys
from PySide6.QtCore import QCoreApplication

# Initialize Qt App for EventBus
app = QCoreApplication(sys.argv)

from core.config_loader import config
config.load()

from core.event_bus import bus
import actions

def on_action(payload):
    print(f"[EVENT: ACTION] {payload['tool']}")

bus.subscribe("agent.action", on_action)

from core.result_types import ParsedCommand
from actions.file_editor import write_file, read_file
from actions.terminal_control import run_command, approve_command

print("Testing File Editor (write)...")
res1 = write_file(ParsedCommand(intent="developer", action="write_file", arguments={"filepath": "test_developer.txt", "content": "Hello AURA Developer!"}))
print(res1)

print("\nTesting File Editor (read)...")
res2 = read_file(ParsedCommand(intent="developer", action="read_file", arguments={"filepath": "test_developer.txt"}))
print(res2)

print("\nTesting Terminal (safe command)...")
# Note: 'dir' doesn't exist as a standalone command without shell=True in some cases, but shell=True is set.
res3 = run_command(ParsedCommand(intent="developer", action="run_command", arguments={"command": "echo 'Terminal Test Works'"}))
print(res3)

print("\nTesting Terminal Sandboxing (dangerous command)...")
res4 = run_command(ParsedCommand(intent="developer", action="run_command", arguments={"command": "pip install fake-pkg"}))
print(res4)

print("\nTesting Sandbox Override (approve_command)...")
approve_command(ParsedCommand(intent="developer", action="approve_command", arguments={"command": "pip install fake-pkg"}))
res5 = run_command(ParsedCommand(intent="developer", action="run_command", arguments={"command": "pip install fake-pkg"}))
print(res5)
# Wait, actually running `rm -rf /` on windows git bash would be disastrous if it works, so let's mock it by doing a dry-run or changing the command...
# Actually `rm -rf /` on native windows shell will just error, but just in case, let's use a fake command that triggers the filter: "pip install fake-pkg"
