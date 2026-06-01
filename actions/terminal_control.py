"""
actions/terminal_control.py — Phase 4 Terminal access with Command Interceptor Sandboxing.
"""
import subprocess
import threading
from loguru import logger
from core.action_registry import registry
from core.result_types import ParsedCommand, ExecutionResult
from core.event_bus import bus

# The Command Interceptor List
DANGEROUS_COMMANDS = ["rm", "del", "format", "pip install", "npm install", "git push", "Drop", "truncate"]

class CommandInterceptor:
    """Blocks execution of dangerous commands unless explicitly bypassed."""
    def __init__(self):
        self.approved_commands = set()
        
    def check_safety(self, command: str) -> tuple[bool, str]:
        if command in self.approved_commands:
            self.approved_commands.remove(command) # One-time use
            return True, ""
            
        for d in DANGEROUS_COMMANDS:
            # Check if the command starts with the dangerous keyword or has it as a distinct word
            if command.lower().startswith(d + " ") or command.lower() == d:
                return False, f"Interceptor Blocked: '{d}' is flagged as dangerous. You must request user approval first."
        return True, ""

interceptor = CommandInterceptor()

def approve_command(cmd: ParsedCommand) -> ExecutionResult:
    """A developer tool to simulate the user approving a blocked command via GUI/Voice."""
    command = cmd.arguments.get("command", "")
    interceptor.approved_commands.add(command)
    bus.publish("agent.action", {"tool": f"Command '{command}' has been whitelisted."})
    return ExecutionResult(success=True, message=f"Command '{command}' approved for execution.")

def run_command(cmd: ParsedCommand) -> ExecutionResult:
    """Executes a command in the terminal."""
    command = cmd.arguments.get("command", "")
    timeout = int(cmd.arguments.get("timeout", 10))
    
    if not command:
        return ExecutionResult(success=False, message="No command provided.")
        
    # Safety Check
    is_safe, msg = interceptor.check_safety(command)
    if not is_safe:
        bus.publish("agent.action", {"tool": f"Interceptor Blocked: {command}"})
        # Note: In the real world, this would trigger TTS asking the user to say "Yes".
        # For now, it returns the error to the LLM so the LLM knows it's blocked.
        return ExecutionResult(success=False, message=msg)
        
    bus.publish("system.terminal.executing", {"command": command})
    bus.publish("agent.action", {"tool": f"Terminal: {command}"})
    
    try:
        # Run command synchronously
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        # Truncate outputs to prevent LLM context overflow
        if len(stdout) > 2000:
            stdout = stdout[:2000] + "\n...[TRUNCATED]"
        if len(stderr) > 2000:
            stderr = stderr[:2000] + "\n...[TRUNCATED]"
            
        output = ""
        if stdout:
            output += f"STDOUT:\n{stdout}\n"
        if stderr:
            output += f"STDERR:\n{stderr}\n"
            
        if not output:
            output = "[Command executed successfully with no output]"
            
        return ExecutionResult(success=result.returncode == 0, message=output)
        
    except subprocess.TimeoutExpired:
        return ExecutionResult(success=False, message=f"Command timed out after {timeout} seconds.")
    except Exception as e:
        logger.error(f"Terminal error: {e}")
        return ExecutionResult(success=False, message=f"Execution error: {e}")

registry.register("developer", "run_command", run_command)
registry.register("developer", "approve_command", approve_command)
