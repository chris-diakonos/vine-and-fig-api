"""
Loader for window construction defaults.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Iterable

from app.services.config_loader import config_value, load_json_config


@lru_cache(maxsize=1)
def load_window_config() -> Dict[str, Any]:
    """Load notebook-derived window construction definitions from JSON."""

    return load_json_config("windows", "WINDOW_CONFIG_PATH")


def window_config_value(path: Iterable[str], default: Any = None) -> Any:
    """Read a nested window config value."""

    return config_value(load_window_config(), path, default)
