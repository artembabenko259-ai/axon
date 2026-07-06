from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from axon_runtime import install_root, user_data_dir

ROOT_DIR = install_root()
CONFIG_PATH = user_data_dir() / "config.json"
LEGACY_CONFIG_PATHS = (ROOT_DIR / "config.json",)

from typing import Any

DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct"
PROVIDERS = ("openrouter", "ollama", "custom", "antigravity")

DEFAULT_CONFIG: dict[str, Any] = {
    "openrouter_api_key": "",
    "model": DEFAULT_MODEL,
    "provider": "openrouter",
    "ollama_base_url": "http://127.0.0.1:11434/v1",
    "custom_base_url": "",
    "custom_api_key": "",
    "antigravity_api_key": "",
    "last_workspace": "",
    "custom_providers": {},
    "reverse_engineering_depth": "deep",
    "decompiler_backend": "radare2",
    "interactive_autocompletion": True,
    "custom_system_prompt_overrides": {},
    "dart_reverse_symbol_filters": [],
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


def load_config() -> dict[str, Any]:
    """Load shared AXON config from %APPDATA%\\AXON\\config.json."""
    _ensure_config_file()
    try:
        with CONFIG_PATH.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        data = {}

    merged = {**DEFAULT_CONFIG, **data}
    return merged


def save_config(data: dict[str, Any]) -> None:
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


def get_valid_providers() -> list[str]:
    config = load_config()
    customs = list(config.get("custom_providers", {}) or {})
    return list(PROVIDERS) + customs


def get_provider() -> str:
    config = load_config()
    value = (config.get("provider") or "").strip().lower()
    
    # Auto-switch trigger envs
    has_custom_env = (
        os.environ.get("CUSTOM_BASE_URL") or 
        os.environ.get("ANTHROPIC_BASE_URL") or 
        os.environ.get("AXON_BASE_URL") or
        os.environ.get("OPENAI_BASE_URL") or
        os.environ.get("DEEPSEEK_BASE_URL") or
        os.environ.get("GROQ_BASE_URL") or
        os.environ.get("MISTRAL_BASE_URL")
    )
    
    if not value:
        if has_custom_env:
            return "custom"
        if os.environ.get("OLLAMA_BASE_URL"):
            return "ollama"
        return "openrouter"
    if value == "openrouter" and has_custom_env:
        return "custom"
    valid = get_valid_providers()
    return value if value in valid else "openrouter"


def get_ollama_base_url() -> str:
    config = load_config()
    url = (config.get("ollama_base_url") or "http://127.0.0.1:11434/v1").strip()
    env = (os.environ.get("OLLAMA_BASE_URL") or "").strip()
    return env or url


def get_custom_base_url() -> str:
    config = load_config()
    url = (config.get("custom_base_url") or "").strip()
    if url:
        return url
    return (
        os.environ.get("CUSTOM_BASE_URL") or 
        os.environ.get("AXON_BASE_URL") or 
        os.environ.get("ANTHROPIC_BASE_URL") or 
        os.environ.get("OPENAI_BASE_URL") or 
        os.environ.get("DEEPSEEK_BASE_URL") or 
        os.environ.get("GROQ_BASE_URL") or 
        os.environ.get("MISTRAL_BASE_URL") or 
        ""
    ).strip()


def get_custom_api_key() -> str:
    config = load_config()
    key = (config.get("custom_api_key") or "").strip()
    if key:
        return key
    return (
        os.environ.get("CUSTOM_API_KEY") or 
        os.environ.get("AXON_API_KEY") or 
        os.environ.get("ANTHROPIC_API_KEY") or 
        os.environ.get("OPENAI_API_KEY") or 
        os.environ.get("DEEPSEEK_API_KEY") or 
        os.environ.get("GROQ_API_KEY") or 
        os.environ.get("MISTRAL_API_KEY") or 
        ""
    ).strip()


def get_custom_headers() -> dict[str, str]:
    headers = {}
    config = load_config()
    config_headers = config.get("custom_headers") or ""
    
    env_headers = (
        os.environ.get("AXON_CUSTOM_HEADERS") or 
        os.environ.get("CUSTOM_HEADERS") or 
        os.environ.get("ANTHROPIC_CUSTOM_HEADERS") or 
        os.environ.get("OPENAI_CUSTOM_HEADERS") or 
        config_headers
    ).strip()
    
    if env_headers:
        normalized = env_headers.replace("\n", ",").replace(";", ",")
        for item in normalized.split(","):
            if ":" in item:
                k, v = item.split(":", 1)
                headers[k.strip()] = v.strip()
    return headers


def get_antigravity_api_key() -> str:
    config = load_config()
    key = (config.get("antigravity_api_key") or "").strip()
    if key:
        return key
    return (os.environ.get("ANTIGRAVITY_API_KEY") or "").strip()


def save_provider_settings(
    *,
    provider: str | None = None,
    openrouter_api_key: str | None = None,
    ollama_base_url: str | None = None,
    custom_base_url: str | None = None,
    custom_api_key: str | None = None,
    antigravity_api_key: str | None = None,
) -> None:
    payload: dict[str, Any] = {}
    if provider is not None:
        cleaned = provider.strip().lower()
        if cleaned in get_valid_providers():
            payload["provider"] = cleaned
    if openrouter_api_key is not None:
        payload["openrouter_api_key"] = openrouter_api_key.strip()
    if ollama_base_url is not None:
        payload["ollama_base_url"] = ollama_base_url.strip()
    if custom_base_url is not None:
        payload["custom_base_url"] = custom_base_url.strip()
    if custom_api_key is not None:
        payload["custom_api_key"] = custom_api_key.strip()
    if antigravity_api_key is not None:
        payload["antigravity_api_key"] = antigravity_api_key.strip()
    if payload:
        save_config(payload)


def save_custom_provider(name: str, url: str, key: str) -> None:
    config = load_config()
    custom_providers = dict(config.get("custom_providers", {}) or {})
    custom_providers[name] = {"base_url": url, "api_key": key}
    save_config({
        "provider": name,
        "custom_providers": custom_providers
    })


def save_model(model: str) -> None:
    """Persist the active model selection to config.json."""
    save_config({"model": model.strip()})
