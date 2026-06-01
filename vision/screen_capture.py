"""
vision/screen_capture.py — Handles capturing the screen using mss.
"""

import mss
from PIL import Image
import io
import base64
from loguru import logger

def capture_screen_base64() -> str | None:
    """Captures the primary monitor and returns a base64-encoded JPEG string."""
    try:
        with mss.mss() as sct:
            # sct.monitors[1] is typically the primary monitor
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            # Compress to JPEG to save bandwidth for LLM
            # (Scale down slightly if it's 4K, to stay within API payload limits)
            max_dimension = 1920
            if img.width > max_dimension or img.height > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            
            b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{b64_str}"
            
    except Exception as e:
        logger.error("Screen capture failed: {}", e)
        return None
