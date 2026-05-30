"""
audio/device_manager.py — Enumerate audio devices, select default mic.
"""

import sounddevice as sd
from loguru import logger


def get_default_input_device() -> dict:
    """Return info dict for the default input device."""
    try:
        info = sd.query_devices(kind="input")
        logger.info("Default mic: '{}' ({} ch, {} Hz)",
                    info["name"], info["max_input_channels"], info["default_samplerate"])
        return info
    except Exception as exc:
        logger.error("Could not query default mic: {}", exc)
        return {}


def list_input_devices() -> list[dict]:
    """Return all available input devices."""
    devices = []
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            devices.append({"index": i, **dev})
    return devices


def check_device(device_index: int | None) -> bool:
    """Verify a device index is valid (None = default)."""
    try:
        sd.check_input_settings(
            device=device_index,
            samplerate=16000,
            channels=1,
            dtype="int16",
        )
        return True
    except Exception as exc:
        logger.error("Device check failed: {}", exc)
        return False
