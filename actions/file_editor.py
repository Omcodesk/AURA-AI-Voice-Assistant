"""
actions/file_editor.py — Phase 4 File System access for Developer Agent.
"""
import os
import glob
from loguru import logger
from core.action_registry import registry
from core.result_types import ParsedCommand, ExecutionResult
from core.event_bus import bus

def resolve_path(filepath: str) -> str:
    """Ensures paths are resolved relative to the workspace root or absolute."""
    workspace_root = os.getcwd()
    if not os.path.isabs(filepath):
        filepath = os.path.join(workspace_root, filepath)
    return os.path.abspath(filepath)

def read_file(cmd: ParsedCommand) -> ExecutionResult:
    """Reads a file from the disk. Optionally restricts to line numbers."""
    filepath = cmd.arguments.get("filepath", "")
    start_line = int(cmd.arguments.get("start_line", 1))
    end_line = cmd.arguments.get("end_line")
    
    if not filepath:
        return ExecutionResult(success=False, message="No filepath provided.")
        
    filepath = resolve_path(filepath)
    if not os.path.exists(filepath):
        return ExecutionResult(success=False, message=f"File not found: {filepath}")
        
    bus.publish("agent.action", {"tool": f"Reading file: {os.path.basename(filepath)}"})
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        end_idx = int(end_line) if end_line else len(lines)
        start_idx = max(0, start_line - 1)
        
        content = "".join(lines[start_idx:end_idx])
        # Return snippet wrapped in contextual message
        return ExecutionResult(success=True, message=f"Contents of {filepath} (Lines {start_line}-{end_idx}):\n```\n{content}\n```")
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        return ExecutionResult(success=False, message=f"Error reading file: {e}")

def write_file(cmd: ParsedCommand) -> ExecutionResult:
    """Creates a new file or completely overwrites an existing one."""
    filepath = cmd.arguments.get("filepath", "")
    content = cmd.arguments.get("content", "")
    
    if not filepath:
        return ExecutionResult(success=False, message="No filepath provided.")
        
    filepath = resolve_path(filepath)
    bus.publish("agent.action", {"tool": f"Writing to file: {os.path.basename(filepath)}"})
    
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        bus.publish("system.file.modified", {"filepath": filepath})
        return ExecutionResult(success=True, message=f"Successfully wrote {len(content)} characters to {filepath}.")
    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        return ExecutionResult(success=False, message=f"Error writing file: {e}")

def patch_file(cmd: ParsedCommand) -> ExecutionResult:
    """Replaces an exact block of text in a file with a new block."""
    filepath = cmd.arguments.get("filepath", "")
    search_block = cmd.arguments.get("search_block", "")
    replace_block = cmd.arguments.get("replace_block", "")
    
    if not filepath or not search_block:
        return ExecutionResult(success=False, message="Missing filepath or search_block.")
        
    filepath = resolve_path(filepath)
    if not os.path.exists(filepath):
        return ExecutionResult(success=False, message=f"File not found: {filepath}")
        
    bus.publish("agent.action", {"tool": f"Patching file: {os.path.basename(filepath)}"})
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if search_block not in content:
            return ExecutionResult(success=False, message="The exact search block was not found in the file. Patch failed.")
            
        new_content = content.replace(search_block, replace_block, 1)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        bus.publish("system.file.modified", {"filepath": filepath})
        return ExecutionResult(success=True, message=f"Successfully patched {filepath}.")
    except Exception as e:
        logger.error(f"Failed to patch file: {e}")
        return ExecutionResult(success=False, message=f"Error patching file: {e}")

def list_directory(cmd: ParsedCommand) -> ExecutionResult:
    """Lists contents of a directory."""
    dirpath = cmd.arguments.get("dirpath", ".")
    dirpath = resolve_path(dirpath)
    
    if not os.path.exists(dirpath):
        return ExecutionResult(success=False, message=f"Directory not found: {dirpath}")
        
    bus.publish("agent.action", {"tool": f"Listing directory: {os.path.basename(dirpath)}"})
    
    try:
        items = os.listdir(dirpath)
        output = "\n".join(items)
        return ExecutionResult(success=True, message=f"Directory contents of {dirpath}:\n{output}")
    except Exception as e:
        return ExecutionResult(success=False, message=f"Error listing directory: {e}")

# Register all tools under Developer Intent
registry.register("developer", "read_file", read_file)
registry.register("developer", "write_file", write_file)
registry.register("developer", "patch_file", patch_file)
registry.register("developer", "list_directory", list_directory)
