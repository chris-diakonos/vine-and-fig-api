"""
Loader for window construction defaults.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable


@lru_cache(maxsize=1)
def load_window_config() -> Dict[str, Any]:
    """Load notebook-derived window construction definitions from JSON."""

    config_path = Path(os.environ.get("WINDOW_CONFIG_PATH", _default_config_path()))
    with open(config_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def window_config_value(path: Iterable[str], default: Any = None) -> Any:
    """Read a nested window config value."""

    current: Any = load_window_config()
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _default_config_path() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "config" / "windows.json"
