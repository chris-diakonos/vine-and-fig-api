"""Joinery defaults loaded from framing configuration."""
from __future__ import annotations

from typing import Any, Dict

from app.services.config_loader import load_json_config


def joinery_config() -> Dict[str, Any]:
    return load_json_config("framing", "FRAMING_CONFIG_PATH").get("joinery", {})


def joinery_defaults(name: str) -> Dict[str, Any]:
    config = joinery_config()
    value = config.get(name)
    if not isinstance(value, dict):
        raise KeyError(f"Missing framing joinery config section: {name}")
    return value.copy()
