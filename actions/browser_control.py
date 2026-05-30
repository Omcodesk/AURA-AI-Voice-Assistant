"""
actions/browser_control.py — Simple, deterministic browser automation for V1.
"""
import urllib.parse
import webbrowser
import json
from pathlib import Path
from loguru import logger

from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry
from core.config_loader import config

_MAPPINGS_FILE = Path("config/site_mappings.json")
_MAPPINGS: dict[str, str] = {}

def _load_mappings():
    global _MAPPINGS
    if _MAPPINGS_FILE.exists():
        try:
            with open(_MAPPINGS_FILE, "r") as f:
                _MAPPINGS = json.load(f)
        except Exception as e:
            logger.error("Failed to load site_mappings.json: {}", e)

_load_mappings()

def _get_browser():
    try:
        # Default to system default browser, but allow override
        preferred = config.get("browser.preferred", "").lower()
        if preferred == "chrome":
            return webbrowser.get("windows-default") # Chrome is usually default
    except webbrowser.Error:
        pass
    return webbrowser

def _clean_site_name(url_or_name: str) -> str:
    name = url_or_name.lower().strip()
    name = name.replace("https://", "").replace("http://", "")
    if name.startswith("www."):
        name = name[4:]
    for sub in ["web.", "mail.", "play.", "drive.", "docs."]:
        if name.startswith(sub):
            name = name[len(sub):]
            break
    name = name.split("/")[0]
    for ext in [".com", ".org", ".net", ".co.in", ".co.uk", ".in"]:
        if name.endswith(ext):
            name = name[:-len(ext)]
            break
    return name.strip().capitalize()

def handle_search_web(cmd: ParsedCommand) -> ExecutionResult:
    # Handle "search the web for X" or "search youtube for X"
    target = cmd.target.lower().strip()
    query = cmd.arguments.get("query", "")
    
    if not query and not target:
        return ExecutionResult(False, "Tell me what to search for.")

    url = ""
    if target in _MAPPINGS:
        # e.g., target="youtube"
        base_url = _MAPPINGS[target]
        if "youtube" in target:
            url = f"{base_url}/results?search_query={urllib.parse.quote(query)}"
        else:
            # Generic fallback for mapping
            url = f"{base_url}/search?q={urllib.parse.quote(query)}"
    else:
        # Default google search
        # If target has a value but not in mappings, just merge it into query
        full_query = f"{target} {query}".strip()
        url = f"https://www.google.com/search?q={urllib.parse.quote(full_query)}"
        
    try:
        _get_browser().open(url)
        return ExecutionResult(True, f"Searching for {query}.")
    except Exception as exc:
        logger.error("Browser search failed: {}", exc)
        return ExecutionResult(False, "I couldn't perform the web search.")

def handle_open_website(cmd: ParsedCommand) -> ExecutionResult:
    target = cmd.target.lower().strip()
    if not target:
        return ExecutionResult(False, "Tell me what website to open.")
        
    url = _MAPPINGS.get(target)
    if not url:
        if target.startswith(("http://", "https://")):
            url = target
        elif "." in target and " " not in target:
            url = f"https://{target}"
        else:
            # Fall back to a google search if we don't know the site
            url = f"https://www.google.com/search?q={urllib.parse.quote(target)}"

    try:
        _get_browser().open(url)
        # Clean site name for clean spoken reply
        clean_name = _clean_site_name(target)
        if clean_name.startswith(("Http", "Https")):
            clean_name = _clean_site_name(url)
        return ExecutionResult(True, f"Opening {clean_name}.")
    except Exception as exc:
        logger.error("Browser open failed: {}", exc)
        return ExecutionResult(False, f"I couldn't open {target}.")

registry.register("browser_control", "search_web", handle_search_web)
registry.register("browser_control", "open_website", handle_open_website)
registry.register("browser_control", "open_tab", handle_open_website) # open_tab maps to same behaviour globally
