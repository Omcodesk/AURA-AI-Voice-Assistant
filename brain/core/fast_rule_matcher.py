import re

class FastRuleMatcher:
    def __init__(self):
        # (Pattern, Intent)
        self._rules = [
            (r"\b(what|tell me|current).*(time|clock|date)\b", "time"),
            (r"\bwhat('s| is) today\b",                         "time"),
            (r"\b(how|what).*(weather|forecast)\b",           "weather"),
            (r"\bweather\b",                                    "weather"),
            (r"\bwill it rain\b",                               "weather"),
            (r"\bforecast\b",                                   "weather"),
            (r"\b(play|pause|resume|next track|previous track|stop music|music)\b", "media_control"),
            (r"\btake (a )?screenshot\b",                       "screenshot"),
            (r"\bscreenshot\b",                                 "screenshot"),
            (r"\bcapture (the )?screen\b",                      "screenshot"),
            (r"\bvolume\s+(up|increase)\b",                    "volume_up"),
            (r"\bvolume\s+(down|decrease)\b",                  "volume_down"),
            (r"\bincrease volume\b",                            "volume_up"),
            (r"\bdecrease volume\b",                            "volume_down"),
            (r"\bmute\b",                                       "volume_down"),
            (r"\bbrightness\s+(up|increase)\b",                "brightness_up"),
            (r"\bbrightness\s+(down|decrease)\b",              "brightness_down"),
            (r"\bset brightness\b",                             "brightness_set"),
            (r"\b(unmute|mute)\b",                              "volume"),
            (r"\bvolume\b",                                     "volume"),
            (r"\bopen\b",                                       "open_app"),
            (r"\blaunch\b",                                     "open_app"),
            (r"\bstart\b",                                      "open_app"),
            (r"\bclose\b",                                      "close_app"),
            (r"\bkill\b",                                       "close_app"),
            (r"\bsearch (for |the web for )?\b",                "search_web"),
            (r"\bgoogle\b",                                     "search_web"),
            (r"\bopen.*website|go to\b",                        "open_website"),
            (r"\bshutdown|shut down\b",                         "shutdown"),
            (r"\brestart|reboot\b",                             "restart"),
            (r"\bsleep\b",                                      "sleep"),
            (r"\block (the )?(screen|computer|pc)\b",           "lock"),
            (r"\bexact time\b",                             "time"),
            (r"\bremind me to\b",                               "set_reminder"),
            (r"\bset (a |an )?alarm\b",                         "set_alarm"),
            (r"\balarm for\b",                                  "set_alarm"),
            (r"\bcancel (my )?(alarm|reminder)\b",              "cancel_reminder"),
            (r"\bstop (the )?(alarm|reminder)\b",               "cancel_reminder"),
            (r"\bsnooze\b",                                     "snooze"),
            (r"\bopen.*whatsapp\b",                             "open_whatsapp"),
            (r"\bopen.*screenshot\b",                           "open_screenshot_folder"),
        ]
        
        # Blocklist for common phrases that should NEVER match dangerous intents
        self._blocklist = [
            re.compile(r"\b(thank you|thanks|bye|goodbye|no thanks)\b", re.IGNORECASE)
        ]
        self._compiled = [(re.compile(p, re.IGNORECASE), intent) for p, intent in self._rules]

    def match(self, text: str) -> str | None:
        # Check blocklist first
        for block in self._blocklist:
            if block.search(text):
                return None # Force conversation/LLM instead of dangerous rule match
                
        for pattern, intent in self._compiled:
            if pattern.search(text):
                return intent
        return None

matcher = FastRuleMatcher()
