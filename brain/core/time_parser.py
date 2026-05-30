"""
brain/core/time_parser.py — Robust NLP time parsing for JARVIS V2.
Supports relative (in X mins) and absolute (at 7 PM) within a 24h window.
"""

import re
from datetime import datetime, timedelta
from loguru import logger

class TimeParser:
    def parse(self, text: str) -> datetime | None:
        """
        Parses a time string and returns a datetime object.
        Returns None if no time could be determined.
        """
        text = text.lower().strip()
        now = datetime.now()

        # 1. Relative: "in 10 minutes", "in 1 hour"
        rel_match = re.search(r"in\s+(\d+)\s*(minute|min|hour|hr|second|sec)s?", text)
        if rel_match:
            amount = int(rel_match.group(1))
            unit = rel_match.group(2)
            if "hour" in unit or unit == "hr":
                return now + timedelta(hours=amount)
            if "minute" in unit or unit == "min":
                return now + timedelta(minutes=amount)
            if "second" in unit or unit == "sec":
                return now + timedelta(seconds=amount)

        # 2. Absolute: "at 7 pm", "at 19:30", "at 8"
        abs_match = re.search(r"(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
        if abs_match:
            hours = int(abs_match.group(1))
            minutes = int(abs_match.group(2)) if abs_match.group(2) else 0
            meridiem = abs_match.group(3)

            if meridiem == "pm" and hours < 12:
                hours += 12
            elif meridiem == "am" and hours == 12:
                hours = 0
            
            # Create target for today
            try:
                target = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                # If target is in the past, move to tomorrow
                if target <= now:
                    target += timedelta(days=1)
                return target
            except ValueError:
                logger.error("Invalid time values: {}:{}", hours, minutes)
                return None

        return None

time_parser = TimeParser()
