"""
app.py — JARVIS entry point.

Usage:
    python app.py

Prerequisites:
    1. pip install -r requirements.txt
    2. Copy .env.example to .env and fill in GROQ_API_KEY
    3. Download Vosk model:
         https://alphacephei.com/vosk/models → vosk-model-small-en-us-0.15
         Unzip into:  models/vosk-model-small-en-us/
    4. Ensure Ollama is running:
         ollama run llama3.2:1b
"""

import sys
import os
from pathlib import Path

# ── Ensure project root is on path ──────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

# ── Ensure required data directories exist ──────────────────────────────────
for _dir in ("data/logs", "data/memory", "data/screenshots", "data/faces",
             "data/routines", "models"):
    (ROOT / _dir).mkdir(parents=True, exist_ok=True)

# ── High-DPI support (must be set before QApplication) ──────────────────────
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from core.logger import setup_logger
from core.config_loader import config
from brain.memory_manager import memory


# Global socket reference to prevent garbage collection
_lock_socket = None

def main():
    # ── Single Instance Lock ────────────────────────────────────────────────
    import socket
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(('127.0.0.1', 47747))
        _lock_socket.listen(1)
    except socket.error:
        from loguru import logger
        logger.error("Another instance of AURA is already running. Exiting.")
        print("Another instance of AURA is already running. Exiting.")
        sys.exit(0)

    # ── Load config ─────────────────────────────────────────────────────────
    config.load(ROOT)

    # ── Logging ─────────────────────────────────────────────────────────────
    setup_logger(
        log_dir=str(ROOT / config.get("logging.directory", "data/logs")),
        level=config.get("logging.level", "INFO"),
    )

    from loguru import logger
    logger.info("=" * 60)
    logger.info("AURA v{} starting up", config.get("aura.version", "1.0"))
    logger.info("=" * 60)

    # ── Integrity Check ─────────────────────────────────────────────────────
    from loguru import logger
    logger.info("Startup Diagnostics:")
    logger.info("  - CWD: {}", os.getcwd())
    logger.info("  - Python: {}", sys.executable)
    
    # Import modules to check their source paths
    import core.command_parser
    import brain.core.slot_extractor
    import actions.app_control
    import actions.time_service
    import actions.weather_service
    
    modules = [
        ("Command Parser", core.command_parser),
        ("Slot Extractor", brain.core.slot_extractor),
        ("App Control", actions.app_control),
        ("Time Service", actions.time_service),
        ("Weather Service", actions.weather_service),
    ]
    
    for name, mod in modules:
        logger.info("  - {}: {}", name.ljust(15), getattr(mod, "__file__", "BUILT-IN"))
        
    # Check for legacy duplicates
    if (ROOT / "parser.py").exists():
        logger.warning("  - Found legacy 'parser.py' in root! This may cause import conflicts.")

    # ── DB init ─────────────────────────────────────────────────────────────
    memory.init_db()

    # ── Qt application ───────────────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("AURA")
    app.setApplicationVersion("1.0-phase1")
    app.setOrganizationName("AURA AI")

    # Dark application palette to avoid white flashes during load
    app.setStyle("Fusion")
    from PySide6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(7, 11, 20))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(232, 244, 254))
    palette.setColor(QPalette.ColorRole.Base, QColor(13, 25, 40))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(10, 15, 30))
    palette.setColor(QPalette.ColorRole.Text, QColor(232, 244, 254))
    palette.setColor(QPalette.ColorRole.Button, QColor(13, 25, 40))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(232, 244, 254))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 212, 255, 80))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(232, 244, 254))
    app.setPalette(palette)

    # ── Main window ──────────────────────────────────────────────────────────
    from gui.main_window import MainWindow
    window = MainWindow()  # Initialises the audio pipeline & wake detector
    # Window will open when wake phrase is spoken
    # window.show()

    logger.info("GUI displayed — entering event loop")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
