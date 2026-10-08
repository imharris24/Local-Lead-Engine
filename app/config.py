import os
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).parent.parent
DEFAULT_ENV_PATH = BASE_DIR / ".env"
DEFAULT_CONFIG_PATH = BASE_DIR / "config.yaml"
DEFAULT_SETTINGS: Dict[str, Any] = {
    "headless": False,
    "database_path": "data/database/leads.db",
    "export_path": "data/exports",
    "log_level": "INFO",
    "default_limit": 100,
    "retry_attempts": 3,
    "retry_delay": 2,
    "retry_backoff": 2,
}


class Settings:
    def __init__(self, env_path: Optional[Path] = None, config_path: Optional[Path] = None):
        self._env: Dict[str, str] = {}
        self._config: Dict[str, Any] = {}
        self._load_env(env_path)
        self._load_config(config_path)
        self._merge_settings()

    def _load_env(self, env_path: Optional[Path]) -> None:
        if env_path is None:
            env_path = DEFAULT_ENV_PATH
        if env_path and env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    self._env[key.strip()] = value.strip()

    def _load_config(self, config_path: Optional[Path]) -> None:
        if config_path is None:
            config_path = DEFAULT_CONFIG_PATH
        if config_path and config_path.exists():
            import yaml
            with open(config_path, "r") as f:
                self._config = yaml.safe_load(f) or {}

    def _merge_settings(self) -> None:
        for key, value in DEFAULT_SETTINGS.items():
            env_key = key.upper()
            if env_key in self._env and self._env[env_key]:
                setattr(self, key, self._env[env_key])
            elif key in self._config:
                setattr(self, key, self._config[key])
            else:
                setattr(self, key, value)

    def __getattr__(self, name: str) -> Any:
        return getattr(self, name, None)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


settings = Settings()