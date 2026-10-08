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


BOOL_KEYS = {"headless"}
INT_KEYS = {
    "default_limit",
    "retry_attempts",
    "retry_delay",
    "retry_backoff",
}


def _coerce(key: str, value: Any) -> Any:
    """Coerce raw .env / YAML values into proper Python types."""
    if isinstance(value, str):
        if key in BOOL_KEYS:
            return value.strip().lower() in {"1", "true", "yes", "on"}
        if key in INT_KEYS:
            try:
                return int(value.strip())
            except (TypeError, ValueError):
                return DEFAULT_SETTINGS.get(key, value)
    return value


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
        # Real environment variables override values from the .env file
        for key in DEFAULT_SETTINGS:
            env_key = key.upper()
            if env_key in os.environ:
                self._env[env_key] = os.environ[env_key]

    def _load_config(self, config_path: Optional[Path]) -> None:
        if config_path is None:
            config_path = DEFAULT_CONFIG_PATH
        if config_path and config_path.exists():
            import yaml
            with open(config_path, "r") as f:
                self._config = yaml.safe_load(f) or {}

    def _merge_settings(self) -> None:
        for key, default in DEFAULT_SETTINGS.items():
            env_key = key.upper()
            if env_key in self._env and self._env[env_key]:
                value = self._env[env_key]
            elif key in self._config:
                value = self._config[key]
            else:
                value = default
            setattr(self, key, _coerce(key, value))

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(f"Settings has no attribute {name!r}")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


settings = Settings()