"""
core/config_loader.py — Singleton config loader for all YAML files + .env.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from loguru import logger


class ConfigLoader:
    _instance: ConfigLoader | None = None
    _cfg: dict[str, Any] = {}
    _security: dict[str, Any] = {}

    def __new__(cls) -> ConfigLoader:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, root: Path | None = None) -> None:
        """Load all YAML configs and .env from the project root."""
        if root is None:
            root = Path(__file__).parent.parent

        # Load environment variables first
        env_file = root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(".env loaded from {}", env_file)
        else:
            load_dotenv()  # fall back to system environment

        config_dir = root / "config"

        self._cfg = self._load_yaml(config_dir / "settings.yaml")
        self._security = self._load_yaml(config_dir / "security.yaml")

        logger.info("Config loaded — version={} (Phase 4: Universal Brain & Safety)", self.get("aura.version", "1.0.0-phase4"))

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        if not path.exists():
            logger.warning("Config file not found: {}", path)
            return {}
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    # ── Accessors ──────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Dot-notation access into settings.yaml, e.g. 'audio.sample_rate'."""
        parts = key.split(".")
        node: Any = self._cfg
        for part in parts:
            if not isinstance(node, dict):
                return default
            node = node.get(part, default)
        return node

    def get_security(self, key: str, default: Any = None) -> Any:
        """Dot-notation access into security.yaml."""
        parts = key.split(".")
        node: Any = self._security
        for part in parts:
            if not isinstance(node, dict):
                return default
            node = node.get(part, default)
        return node

    def groq_api_key(self) -> str:
        key = os.getenv("GROQ_API_KEY", "")
        if not key:
            logger.warning("GROQ_API_KEY not set — STT will not work")
        return key

    def ollama_host(self) -> str:
        return os.getenv("OLLAMA_HOST", "http://localhost:11434")

    def news_api_key(self) -> str:
        return os.getenv("NEWS_API_KEY", "")

    def openweather_api_key(self) -> str:
        return os.getenv("OPENWEATHER_API_KEY", "")


# Module-level singleton
config = ConfigLoader()
