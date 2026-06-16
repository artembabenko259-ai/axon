"""LLM provider resolution — OpenRouter, Ollama, and custom OpenAI-compatible APIs."""

from __future__ import annotations

import os

from config_store import (
    get_custom_api_key,
    get_custom_base_url,
    get_openrouter_api_key,
    get_ollama_base_url,
    get_provider,
    load_config,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
OLLAMA_API_KEY = "ollama"
PROVIDERS = ("openrouter", "ollama", "custom")


def normalize_base_url(url: str) -> str:
    """Normalize OpenAI-compatible base URL (strip trailing slash)."""
    cleaned = (url or "").strip().rstrip("/")
    if not cleaned:
        return ""
    # Common shorthand: host without /v1
    if cleaned.endswith("/v1"):
        return cleaned
    if cleaned.endswith("/api"):
        return f"{cleaned}/v1"
    return cleaned


def resolve_llm_endpoint() -> tuple[str, str]:
    """Return (base_url, api_key) for the OpenAI-compatible client."""
    provider = get_provider()
    if provider == "ollama":
        url = normalize_base_url(get_ollama_base_url()) or DEFAULT_OLLAMA_BASE_URL
        return url, OLLAMA_API_KEY

    if provider == "custom":
        url = normalize_base_url(get_custom_base_url())
        key = get_custom_api_key() or "missing-key"
        return url, key

    return OPENROUTER_BASE_URL, get_openrouter_api_key() or "missing-key"


def is_llm_configured() -> bool:
    """True when the active provider has enough settings to call the API."""
    provider = get_provider()
    base_url, api_key = resolve_llm_endpoint()
    if provider == "ollama":
        return bool(base_url)
    if provider == "custom":
        return bool(base_url) and bool(api_key) and api_key != "missing-key"
    return bool(api_key) and api_key != "missing-key"


def provider_label() -> str:
    return get_provider()


def provider_config_hint() -> str:
    try:
        from zenith_server import config_url

        hint = f"Configure at {config_url()} or use /provider"
    except Exception:
        hint = "Edit config.json or use /provider in the terminal"
    return hint


def provider_status() -> dict[str, str]:
    """Non-secret provider snapshot for UI/CLI."""
    provider = get_provider()
    base_url, _ = resolve_llm_endpoint()
    config = load_config()
    return {
        "provider": provider,
        "base_url": base_url,
        "ollama_base_url": (config.get("ollama_base_url") or DEFAULT_OLLAMA_BASE_URL).strip(),
        "custom_base_url": (config.get("custom_base_url") or "").strip(),
        "has_openrouter_api_key": str(bool(get_openrouter_api_key())).lower(),
        "has_custom_api_key": str(bool(get_custom_api_key())).lower(),
    }
