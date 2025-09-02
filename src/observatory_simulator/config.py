import logging
import shutil
import threading
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent / "config"


class Config:
    """Thread-safe lazy-loading singleton that parses the YAML config."""

    _instance = None
    _lock = threading.Lock()
    _DEFAULT_PATH = CONFIG_DIR / "template.yaml"
    CONFIG_DIR = CONFIG_DIR

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_name="config.yaml"):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.config_name = self._standardise_config_name(config_name)
        self._config_path = self.CONFIG_DIR / self.config_name

        self._config = None
        self._load_lock = threading.Lock()
        logging.info(f"Loading config {self.config_name}.")

    def get(self) -> dict:
        """Return the loaded config. Loads on first access."""
        if self._config is None:
            with self._load_lock:
                if self._config is None:
                    self._config = self._ensure_and_load()
        return self._config

    def _ensure_and_load(self):
        if not self.CONFIG_DIR.exists():
            raise FileNotFoundError(f"Config directory not found: {self.CONFIG_DIR!s}")

        if not self._config_path.exists():
            self._initialise_with_default_config()

        with open(self._config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _initialise_with_default_config(self):
        """Copy default config to config.yaml if not present"""
        if not self.CONFIG_DIR.exists():
            raise FileNotFoundError(f"Config directory not found: {self.CONFIG_DIR!s}")
        if not self._DEFAULT_PATH.exists():
            raise FileNotFoundError(f"Default config not found at {self._DEFAULT_PATH!s}")

        shutil.copyfile(self._DEFAULT_PATH, self._config_path)

    def __getitem__(self, key):
        return self.get()[key]

    def reload(self):
        """Force reload from disk"""
        with self._load_lock:
            self._config = self._ensure_and_load()
        return self._config

    @staticmethod
    def _standardise_config_name(config_name: str) -> str:
        if config_name.endswith(".yml"):
            config_name = config_name.removesuffix(".yml")

        if not config_name.endswith(".yaml"):
            config_name += ".yaml"

        return config_name
