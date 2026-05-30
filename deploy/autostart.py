"""
deploy/autostart.py — Programmatic Task Scheduler Auto-Start Setup for JARVIS

This script creates a Windows Task Scheduler entry to automatically
start Jarvis on system logon with highest privileges.
"""
import os
import sys
import subprocess
from pathlib import Path

def setup_autostart():
    project_dir = Path(__file__).parent.parent.resolve()
    
    # Use pythonw to prevent a command prompt window from popping up on boot
    python_exe = sys.executable
    if python_exe.endswith("python.exe"):
        pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
        if os.path.exists(pythonw_exe):
            python_exe = pythonw_exe

    app_script = str(project_dir / "app.py")
    task_name = "Aura_AutoStart"
    
    print(f"Setting up Windows auto-start for Aura...")
    print(f"Project directory: {project_dir}")
    print(f"Executable: {python_exe}")
    print(f"Script: {app_script}")
    
    # Task Scheduler command to run at logon with highest privileges
    cmd = [
        "schtasks",
        "/create",
        "/tn", task_name,
        "/tr", f'"{python_exe}" "{app_script}"',
        "/sc", "onlogon",
        "/rl", "highest",
        "/f"  # force overwrite if exists
    ]
    
    try:
        # Run command without creating a window if possible
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
            
        print(f"\nExecuting: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, creationflags=creationflags)
        print("\nSuccess! Aura will now start automatically at boot (logon).")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("\nFAILED: Could not create Task Scheduler entry.")
        print(e.stderr)
        print("\nPlease run this script as Administrator to configure Task Scheduler.")

if __name__ == "__main__":
    setup_autostart()
