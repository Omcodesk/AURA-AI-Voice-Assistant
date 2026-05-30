import os
from brain.intent_router import router
from core.command_parser import command_parser

print("--- Phase 4 Pipeline Test ---")

queries = [
    "Send WhatsApp to Mom: I'm home now",
    "Email boss: running late",
    "Open WhatsApp chat with Ravi",
    "Read my recent messages",
    "whatsapp to mom: checking in"
]

for q in queries:
    cmd = router.route(q)
    print(f"\nQuery: '{q}'")
    
    action_name = cmd.action.replace("_", " ")
    if cmd.intent in ("whatsapp", "email") and cmd.action in ("send_message", "draft_email"):
        short_msg = cmd.arguments.get("message", "")[:20]
        action_name = f"{cmd.intent.title()} to {cmd.target}: {short_msg}..."
            
    print(f"  Parsed: intent={cmd.intent}, action={cmd.action}, target={cmd.target}, args={cmd.arguments}")
    print(f"  Auth Req: {cmd.requires_auth}, Conf Req: {cmd.requires_confirmation}")
    print(f"  GUI Formatted Name: {action_name}")
