"""
core/policy_engine.py — Determines authorization and confirmation requirements for commands.
"""

from core.result_types import ParsedCommand

class PolicyEngine:
    def apply_policies(self, cmd: ParsedCommand) -> ParsedCommand:
        """
        Annotates a ParsedCommand with security flags (`requires_auth`, `requires_confirmation`).
        """
        # Determine from existing intent policies (Tier system from Phase 2)
        # We'll adapt it here for Phase 3
        # High risk: shutdown, restart, sleep
        
        # Default flags
        auth_req = False
        conf_req = False
        
        # App control specific checks
        if cmd.intent == "app_control" and cmd.action == "close_app":
            # For V1, closing apps is moderately risky but we won't require auth by default unless it's a protected app
            # No protected apps list yet, so just confirm
            conf_req = True
            
        elif cmd.intent == "system_control":
            if cmd.action in ("shutdown", "restart", "sleep", "lock"):
                # System state changes always require auth
                auth_req = True
                if cmd.action != "lock":
                    # Lock is safe enough to not prompt "are you sure?"
                    conf_req = True

        cmd.requires_auth = auth_req
        cmd.requires_confirmation = conf_req
        return cmd

# Singleton
policy_engine = PolicyEngine()
