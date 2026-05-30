import os
from brain.intent_router import router

print("--- Phase 3 Core Pipeline Test ---")

queries = [
    "shutdown the computer",
    "take a screenshot",
    "what's the weather today",
    "search youtube for lo-fi music",
    "open chrome",
    "close edge",
    "increase brightness by 20"
]

for q in queries:
    cmds = router.route(q)
    print(f"\nQuery: '{q}'")
    for cmd in cmds:
        print(f"  Parsed: intent={cmd.intent}, action={cmd.action}, target={cmd.target}")
        print(f"  Auth Req: {cmd.requires_auth}, Conf Req: {cmd.requires_confirmation}")
