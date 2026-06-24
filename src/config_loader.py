import json
from typing import Any, Dict

class ConfigLoader:
    def __init__(self, config_path: str = "config/production_agent_spec.json"):
        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at {self.config_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in configuration file at {self.config_path}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def get_section(self, section: str) -> Dict[str, Any]:
        return self._config.get(section, {})

    @property
    def config(self) -> Dict[str, Any]:
        return self._config
