"""
main.py — Jarvis V2 Entry point + Windows Auto-start setup instructions.

======================================================================
 AUTO-START SETUP INSTRUCTIONS (Windows Task Scheduler)
======================================================================
To have Jarvis start automatically on boot without a visible terminal
and bypass manual startup:

Method 1 (Automatic via script):
--------------------------------
Run the autostart deployment script as Administrator:
    python deploy/autostart.py

Method 2 (Manual via Task Scheduler):
-------------------------------------
1. Open Windows Task Scheduler.
2. Click "Create Task...".
3. General tab:
   - Name: "JarvisAutoStart"
   - Check "Run with highest privileges".
4. Triggers tab -> New:
   - Begin the task: "At log on".
5. Actions tab -> New:
   - Action: "Start a program"
   - Program/script: `pythonw.exe` (Use your pythonw path to hide console window)
   - Add arguments: `app.py`
   - Start in: (The full absolute path to the Jarvis V2 project directory)
6. Conditions tab:
   - Uncheck "Start the task only if the computer is on AC power".
7. Save and close. Jarvis will now start silently on boot!

======================================================================
"""
import sys
from pathlib import Path

# Provide a convenience entry point that simply delegates to app.py
if __name__ == "__main__":
    # Ensure current directory is in sys.path
    import app
    sys.exit(app.main())
