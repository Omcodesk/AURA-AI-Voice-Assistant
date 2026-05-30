import os
import sys
import subprocess
from pathlib import Path
from loguru import logger

def setup_autostart():
    # 1. Paths
    project_root = Path(__file__).parent.parent.absolute()
    app_path = project_root / "app.py"
    
    # Use pythonw.exe to launch without a console window
    python_exe = Path(sys.executable)
    pythonw_exe = python_exe.parent / "pythonw.exe"
    if not pythonw_exe.exists():
        pythonw_exe = python_exe # Fallback if pythonw not found
        
    task_name = "AURA_V2"
    
    # 2. Command for Task Scheduler
    # /create - Create task
    # /tn - Task Name
    # /tr - Task Run command
    # /sc - Schedule (ONLOGON)
    # /rl - Run Level (HIGHEST)
    # /f - Force overwrite
    
    # We use a CMD bridge to ensure the working directory is set correctly
    command = f'schtasks /create /tn "{task_name}" /tr "cmd.exe /c cd /d {project_root} && start {pythonw_exe} {app_path}" /sc ONLOGON /rl HIGHEST /f'
    
    try:
        logger.info("Registering AURA with Windows Task Scheduler...")
        subprocess.run(command, shell=True, check=True)
        logger.info("Successfully registered AURA. She will now start automatically at every logon.")
    except subprocess.CalledProcessError as e:
        logger.error("Failed to register task: {}", e)
        print("\nERROR: Please run this terminal as Administrator to register the startup task.\n")

if __name__ == "__main__":
    setup_autostart()
