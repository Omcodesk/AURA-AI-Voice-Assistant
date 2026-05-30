"""
actions/email_web.py — Phase 4 Email automation via Playwright.
Uses Gmail web interface.
"""
import time
import json
import urllib.parse
from pathlib import Path
from loguru import logger
from playwright.sync_api import sync_playwright

from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry

_TEMPLATES_FILE = Path("config/email_templates.json")
_PROFILE_DIR = Path("data/browser_profile")

def _get_template(name: str) -> str:
    if _TEMPLATES_FILE.exists():
        with open(_TEMPLATES_FILE, "r") as f:
            templates = json.load(f)
            return templates.get(name.lower(), "")
    return ""

def handle_draft_email(cmd: ParsedCommand) -> ExecutionResult:
    target = cmd.target.strip()
    msg = cmd.arguments.get("message", "")
    
    # If the message matches a template name, retrieve it
    template_msg = _get_template(msg)
    if template_msg:
        msg = template_msg
        
    if not target or not msg:
        return ExecutionResult(False, "I need both a recipient email/name and a message to draft.")

    subject = urllib.parse.quote("Sent via JARVIS")
    body = urllib.parse.quote(msg)
    
    gmail_url = f"https://mail.google.com/mail/u/0/?view=cm&fs=1&to={target}&su={subject}&body={body}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(_PROFILE_DIR),
                headless=False,
                channel="msedge",
                no_viewport=True
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            
            page.goto(gmail_url)
            
            try:
                # Wait for the compose window to appear
                page.wait_for_selector('div[aria-label="Message Body"]', timeout=30000)
                
                # We wait 5 minutes before closing to allow user to review and send
                # Phase 4 timeout rule: Timeout any open browser sessions after 5 minutes
                logger.info("Draft ready. Browser will remain open for 5 minutes.")
                time.sleep(300) 
                
                browser.close()
                return ExecutionResult(True, "Email draft session closed.")
                
            except Exception:
                # Login likely required
                logger.warning("Gmail login required.")
                browser.close()
                return ExecutionResult(False, "Gmail requires you to login. Try opening your browser first to save your session.")

    except Exception as e:
        logger.error(f"Email drafting failed: {e}")
        return ExecutionResult(False, "Failed to automate Gmail.")

registry.register("email", "draft_email", handle_draft_email)
