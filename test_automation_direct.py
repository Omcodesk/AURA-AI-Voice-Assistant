import os
from core.result_types import ParsedCommand
from actions.whatsapp import handle_send_whatsapp

print("--- Direct WhatsApp Action Test ---")
print("Simulating a voice command that has already been spoken and confirmed with 'Yes'...")

cmd = ParsedCommand(
    intent="whatsapp",
    action="send_message",
    target="asim",
    arguments={"target": "asim", "message": "hi"},
    requires_auth=True,
    requires_confirmation=True,
    source_text="send whatsapp to asim: hi"
)

result = handle_send_whatsapp(cmd)

print(f"\nExecution Result:")
print(f"Success: {result.success}")
print(f"Message: {result.message}")
