from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from axon_runtime import install_root, user_data_dir

ROOT_DIR = install_root()
CONFIG_PATH = user_data_dir() / "config.json"
LEGACY_CONFIG_PATHS = (ROOT_DIR / "config.json",)

DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct"

DEFAULT_CONFIG: dict[str, str] = {
    "openrouter_api_key": "",
    "model": DEFAULT_MODEL,
    "provider": "openrouter",
    "ollama_base_url": "http://127.0.0.1:11434/v1",
}


def _migrate_legacy_config() -> None:
    if CONFIG_PATH.exists():
        return
    for legacy in LEGACY_CONFIG_PATHS:
        try:
            resolved = legacy.resolve()
        except OSError:
            continue
        if not resolved.is_file():
            continue
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolved, CONFIG_PATH)
        return


def _ensure_config_file() -> None:
    _migrate_legacy_config()
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)


def load_config() -> dict[str, str]:
    """Load shared AXON config from %APPDATA%\\AXON\\config.json."""
    _ensure_config_file()
    try:
        with CONFIG_PATH.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        data = {}

    merged = {**DEFAULT_CONFIG, **data}
    return merged


def save_config(data: dict[str, str]) -> None:
    """Persist shared AXON config."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
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


def get_provider() -> str:
    config = load_config()
    value = (config.get("provider") or "openrouter").strip().lower()
    return value if value in {"openrouter", "ollama"} else "openrouter"


def get_ollama_base_url() -> str:
    config = load_config()
    return (config.get("ollama_base_url") or "http://127.0.0.1:11434/v1").strip()


def save_model(model: str) -> None:
    """Persist the active model selection to config.json."""
    save_config({"model": model.strip()})
