"""
core/logger.py — Loguru rotating logger with Qt signal bridge.
"""

import sys
from pathlib import Path
from loguru import logger
from PySide6.QtCore import QObject, Signal


class LogBridge(QObject):
    """Qt signal bridge so GUI panels can subscribe to log messages."""
    log_message = Signal(str, str)   # (level, message)

    def emit_log(self, level: str, message: str):
        self.log_message.emit(level, message)


# Singleton bridge instance
log_bridge = LogBridge()


def _qt_sink(message):
    record = message.record
    level = record["level"].name
    text = record["message"]
    log_bridge.emit_log(level, text)


def setup_logger(log_dir: str = "data/logs", level: str = "DEBUG") -> None:
    """Initialise Loguru. Call once at startup."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.remove()

    # Console sink
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> — {message}",
        colorize=True,
    )

    # Rotating file sink
    logger.add(
        log_path / "jarvis_{time:YYYY-MM-DD}.log",
        level=level,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} — {message}",
    )

    # Qt bridge sink
    logger.add(_qt_sink, level="INFO", format="{message}")

    logger.info("Logger initialised — level={}", level)
