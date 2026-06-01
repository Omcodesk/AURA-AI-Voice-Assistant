"""
core/kill_switch.py — Global safety kill switch for automated actions.
"""
import threading
from loguru import logger
from core.event_bus import bus

class KillSwitch:
    def __init__(self):
        self._halt_event = threading.Event()
        
        # Listen for the voice command "Aura Stop"
        bus.subscribe("system.kill_switch.activated", self.trigger)
        
    def trigger(self, payload=None):
        logger.warning("CRITICAL: Kill Switch Activated! Halting all automated actions.")
        self._halt_event.set()
        
    def reset(self):
        self._halt_event.clear()
        
    def check(self):
        """Raises an exception if the kill switch has been triggered."""
        if self._halt_event.is_set():
            raise RuntimeError("Execution aborted by Kill Switch.")
            
kill_switch = KillSwitch()
