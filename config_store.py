from __future__ import annotations

import json
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "config.json"

DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct"

DEFAULT_CONFIG: dict[str, str] = {
    "openrouter_api_key": "",
    "model": DEFAULT_MODEL,
    "provider": "openrouter",
}


def _ensure_config_file() -> None:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)


def load_config() -> dict[str, str]:
    """Load shared AXON config from config.json (created on first access)."""
    _ensure_config_file()
    try:
        with CONFIG_PATH.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        data = {}

    merged = {**DEFAULT_CONFIG, **data}
    return merged


def save_config(data: dict[str, str]) -> None:
    """Persist shared AXON config to config.json."""
    current = load_config() if CONFIG_PATH.exists() else dict(DEFAULT_CONFIG)
    current.update(data)
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(current, handle, indent=2)


def get_openrouter_api_key() -> str:
    """Read API key from config.json, falling back to environment."""
    config = load_config()
    key = (config.get("openrouter_api_key") or "").strip()
    if key:
        return key
    return (os.environ.get("OPENROUTER_API_KEY") or "").strip()


def get_model() -> str:
    config = load_config()
    return (config.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def save_model(model: str) -> None:
    """Persist the active model selection to config.json."""
    save_config({"model": model.strip()})
