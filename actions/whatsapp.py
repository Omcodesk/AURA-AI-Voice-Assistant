"""
actions/whatsapp.py — Phase 4 WhatsApp Web automation via Playwright.
Supports manual login and persistent contexts.
"""
import time
import json
from pathlib import Path
from loguru import logger
from playwright.sync_api import sync_playwright

from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry

_CONTACTS_FILE = Path("config/whatsapp_contacts.json")
_PROFILE_DIR = Path("data/browser_profile")

def _get_contact_number(name: str) -> str:
    if _CONTACTS_FILE.exists():
        with open(_CONTACTS_FILE, "r") as f:
            contacts = json.load(f)
            return contacts.get(name.lower(), "")
    return ""

def handle_send_whatsapp(cmd: ParsedCommand) -> ExecutionResult:
    contact_name = cmd.target.strip()
    msg = cmd.arguments.get("message", "")
    
    if not contact_name or not msg:
        return ExecutionResult(False, "I need both a contact name and a message.")

    number = _get_contact_number(contact_name)
    if not number:
        return ExecutionResult(False, f"Contact {contact_name} is not in your configured contacts list.")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(_PROFILE_DIR),
                headless=False,
                channel="msedge",
                no_viewport=True
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            
            page.goto("https://web.whatsapp.com/")
            
            # 1. Handle "Use Here" or QR code login
            try:
                # Quick wait to see if the "Use Here" prompt or main pane appears
                page.wait_for_selector('#pane-side, div[role="button"]:has-text("Use Here")', timeout=60000)
                
                # Click "Use Here" if it exists
                use_here = page.locator('div[role="button"]:has-text("Use Here")')
                if use_here.count() > 0:
                    use_here.first.click()
                    time.sleep(2)
                    
                # Guarantee it's fully loaded before navigating to the specific chat URL
                page.wait_for_selector('#pane-side', timeout=30000)
                
            except Exception:
                logger.warning("WhatsApp Web login required or timed out.")
                browser.close()
                return ExecutionResult(False, "WhatsApp Web needs you to login. Try saying 'Open WhatsApp' first to scan your QR code.")

            # 2. Inject URL payload
            clean_number = number.replace('+', '').replace(' ', '').replace('-', '')
            page.goto(f"https://web.whatsapp.com/send?phone={clean_number}&text={msg}")
            
            try:
                page.wait_for_selector('#main', timeout=30000)
                time.sleep(4)
                page.keyboard.press("Enter")
                time.sleep(3) # Wait for send transmission

                browser.close()
                return ExecutionResult(True, f"WhatsApp message sent to {contact_name}.")
                
            except Exception:
                logger.warning("WhatsApp Web login required or timed out.")
                # We do NOT close the browser here, to allow the user to scan the QR code manually.
                # However, since Playwright blocks, we could return a message. 
                # But closing releases the context. We'll close it and tell the user to login via open_whatsapp intent first.
                browser.close()
                return ExecutionResult(False, "WhatsApp Web needs you to login. Try saying 'Open WhatsApp' first to scan your QR code.")

    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")
        return ExecutionResult(False, "Failed to automate WhatsApp.")

def handle_open_whatsapp(cmd: ParsedCommand) -> ExecutionResult:
    target = cmd.target.strip()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(_PROFILE_DIR),
                headless=False,
                channel="msedge",
                no_viewport=True
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            
            number = _get_contact_number(target)
            if target and number:
                page.goto(f"https://web.whatsapp.com/send?phone={number}")
            else:
                page.goto("https://web.whatsapp.com")
                
            # Phase 4 timeout rule: Timeout any open browser sessions after 5 minutes
            logger.info("WhatsApp window opened. Browser will remain open for 5 minutes.")
            time.sleep(300) 
            
            browser.close()
            return ExecutionResult(True, "WhatsApp session timed out and closed.")
            
    except Exception as e:
        logger.error(f"WhatsApp open failed: {e}")
        return ExecutionResult(False, "Failed to open WhatsApp.")

def handle_read_whatsapp(cmd: ParsedCommand) -> ExecutionResult:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(_PROFILE_DIR),
                headless=False,
                channel="msedge",
                no_viewport=True
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://web.whatsapp.com/")
            
            try:
                page.wait_for_selector('#pane-side', timeout=45000)
                time.sleep(3) # Let chats load
                
                # Fetch recent contact titles
                chats = page.query_selector_all('#pane-side span[dir="auto"]')
                recent_names = []
                for chat in chats[:5]:
                    name = chat.inner_text()
                    if name and len(name) > 1:
                        recent_names.append(name)
                        
                browser.close()
                names_str = ", ".join(recent_names[:3])
                return ExecutionResult(True, f"Your recent chats are with {names_str}.")
                
            except Exception:
                browser.close()
                return ExecutionResult(False, "Could not load your recent chats. You may need to log in.")
                
    except Exception as e:
        logger.error(f"WhatsApp read failed: {e}")
        return ExecutionResult(False, "Failed to read WhatsApp messages.")

registry.register("whatsapp", "send_message", handle_send_whatsapp)
registry.register("whatsapp", "open_chat", handle_open_whatsapp)
registry.register("whatsapp", "read_recent", handle_read_whatsapp)
