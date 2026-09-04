"""
Shared JSON configuration loading for CAD builders.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def config_path(name: str, env_var: Optional[str] = None) -> Path:
    """Resolve a config file path from an optional override or repo config folder."""

    if env_var and os.environ.get(env_var):
        return Path(os.environ[env_var])
    return _default_config_dir() / f"{name}.json"


@lru_cache(maxsize=None)
def load_json_config(name: str, env_var: Optional[str] = None) -> Dict[str, Any]:
    """Load a named JSON config from the repo config folder."""

    with open(config_path(name, env_var), "r", encoding="utf-8") as handle:
        return json.load(handle)


def config_value(config: Dict[str, Any], path: Iterable[str], default: Any = None) -> Any:
    """Read a nested value from an already loaded config dictionary."""

    current: Any = config
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _default_config_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "config"
