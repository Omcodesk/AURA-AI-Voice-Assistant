import re
import json
from pathlib import Path
from loguru import logger

class SlotExtractor:
    def __init__(self, synonym_map_path="config/synonym_map.json"):
        self.synonyms = {}
        self._load_synonyms(synonym_map_path)

    def _load_synonyms(self, path):
        p = Path(path)
        if p.exists():
            try:
                with open(p, "r") as f:
                    self.synonyms = json.load(f)
            except Exception as e:
                logger.error("Failed to load synonyms: {}", e)

    def extract_slots(self, intent: str, text: str) -> dict:
        text_lower = text.lower().strip()
        # Phase 4: Strip trailing noise and punctuation
        text_lower = re.sub(r"[?!.]$", "", text_lower)
        text_lower = re.sub(r"\s+(for me|please|now|immediately|thanks|thank you)$", "", text_lower).strip()
        slots = {}

        # 1. App Extraction
        if intent in ("open_app", "close_app", "app_control"):
            app = self._extract_after(text_lower, ["open", "launch", "start", "close", "kill", "quit"])
            slots["app"] = self._canonical_app(app)

        # 2. Website/Site Extraction
        if intent in ("open_website", "browser_control"):
            site = self._extract_after(text_lower, ["go to", "navigate to", "open", "on"])
            # Check if it's a known site name
            slots["site"] = self._canonical_site(site)
            # If site not found, maybe it's a raw URL
            if not slots["site"] and "." in site:
                slots["url"] = site

        # 3. Search Query
        if "search" in text_lower or intent == "search_web" or "google" in text_lower or "look up" in text_lower:
            # 1. Resolve search target (youtube or google)
            search_target = "google"
            if re.search(r"\bon\s+youtube\b", text_lower):
                search_target = "youtube"
            elif re.search(r"\bon\s+google\b", text_lower):
                search_target = "google"
            elif re.search(r"^search\s+youtube\b", text_lower):
                search_target = "youtube"
            elif re.search(r"^search\s+google\b", text_lower) or re.search(r"^google\b", text_lower):
                search_target = "google"
            elif "youtube" in text_lower and "google" not in text_lower:
                search_target = "youtube"
            slots["url"] = search_target

            # 2. Extract query text
            strip_leading = [
                r"^search\s+for\s+the\s+web\s+for\s+",
                r"^search\s+the\s+web\s+for\s+",
                r"^search\s+google\s+for\s+",
                r"^search\s+youtube\s+for\s+",
                r"^search\s+for\s+",
                r"^google\s+for\s+",
                r"^look\s+up\s+",
                r"^search\s+",
                r"^google\s+",
            ]
            query = text_lower
            for pattern in strip_leading:
                if re.match(pattern, query):
                    query = re.sub(pattern, "", query, count=1)
                    break
            strip_trailing = [
                r"\s+on\s+(google|youtube|chrome|edge|browser|internet|safari|firefox|the\s+web|the\s+internet)$",
                r"\s+in\s+google$",
                r"\s+using\s+google$"
            ]
            for pattern in strip_trailing:
                query = re.sub(pattern, "", query).strip()
            slots["query"] = query

        # 4. Weather Location
        if intent == "weather":
            location = self._extract_after(text_lower, ["weather in", "weather for", "weather at", "weather of"])
            if location == text_lower: # No marker found
                location = self._extract_after(text_lower, ["weather"])
            
            # Phase 4 Improved: Strip temporal fillers that aren't locations
            location = re.sub(r"\b(right now|now|today|currently|tonight|tomorrow|right|presently)\b", "", location).strip()
            # If the result is just a filler or empty, clear it
            slots["location"] = location if len(location) > 0 else ""

        # 5. Brightness / Volume Amount
        if intent in ("brightness_up", "brightness_down", "volume_up", "volume_down", "brightness_set", "volume"):
            # Try to find a percentage or number
            match = re.search(r"(\d+)", text_lower)
            if match:
                slots["amount"] = int(match.group(1))
            elif "a lot" in text_lower or "way up" in text_lower:
                slots["amount"] = 30
            elif "a bit" in text_lower or "a little" in text_lower:
                slots["amount"] = 5

        # 6. Media Control Slots
        if intent == "media_control":
            if "play" in text_lower or "resume" in text_lower: slots["action"] = "play"
            elif "pause" in text_lower: slots["action"] = "pause"
            elif "next" in text_lower: slots["action"] = "next"
            elif "prev" in text_lower or "back" in text_lower: slots["action"] = "prev"
            elif "stop" in text_lower: slots["action"] = "stop"

        # 7. Message/Target (WhatsApp/Email)
        if intent in ("whatsapp", "email", "send_whatsapp", "draft_email"):
            m = re.search(r"to\s+([\w\s]+)(?:[:\.]|saying)\s*(.+)", text, re.IGNORECASE)
            if not m:
                m = re.search(r"to\s+([\w\s]+)\s+(.+)", text, re.IGNORECASE)
            if m:
                slots["target"] = m.group(1).strip()
                slots["message"] = m.group(2).strip()

        # 7. Alarms & Reminders
        if intent == "set_reminder":
            task = self._extract_after(text_lower, ["remind me to"])
            # task might still contain the time, e.g. "drink water at 5 pm"
            # We'll extract time separately
            slots["task"] = re.sub(r"\b(at|in|on)\s+\d+.*", "", task).strip()
            slots["time"] = self._extract_time_str(text_lower)

        if intent == "set_alarm":
            slots["time"] = self._extract_time_str(text_lower)
            slots["task"] = "Alarm"

        return slots

    def _extract_time_str(self, text: str) -> str:
        """Helper to pull the raw time-related substring."""
        # Look for "at ...", "in ...", "for ..."
        match = re.search(r"\b(at|in|for)\s+(\d+.*)", text)
        if match:
            return match.group(0).strip()
        # Fallback: maybe just "7 pm"
        match = re.search(r"(\d{1,2}(?::\d{2})?\s*(am|pm)?)", text)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_after(self, text: str, markers: list[str]) -> str:
        for m in markers:
            # Pattern: find the marker, then capture everything after it
            pattern = rf"\b{re.escape(m)}\b\s*(.*)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                res = match.group(1).strip()
                return res if res else ""
        return "" # If no marker found, return empty in this context

    def _canonical_app(self, name: str) -> str:
        name = name.lower().strip()
        # Phase 4 improved normalization: strip fillers
        # e.g. "the browser" -> "browser", "google chrome" -> "chrome"
        name = re.sub(r"^(the|it|google|an|a)\s+", "", name).strip()
        
        app_map = self.synonyms.get("apps", {})
        if name in app_map:
            return app_map[name]
            
        # Check website mapping too, just in case 'open' intent got confused
        # If it's a known site, we return it as is so app_control can reroute
        if self._canonical_site(name):
            return name

        return app_map.get(name, name)

    def _canonical_site(self, name: str) -> str:
        name = name.lower().strip()
        site_map = self.synonyms.get("sites", {})
        # Handle "youtube" vs "youtube.com"
        clean_name = name.replace(".com", "").replace(".net", "").replace(".org", "")
        return site_map.get(clean_name, "")

slot_extractor = SlotExtractor()
