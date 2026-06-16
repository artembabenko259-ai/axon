"""LLM provider resolution — OpenRouter (cloud) and Ollama (local)."""

from __future__ import annotations

import os

from config_store import load_config

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
OLLAMA_API_KEY = "ollama"


def get_provider() -> str:
    config = load_config()
    provider = (config.get("provider") or "openrouter").strip().lower()
    return provider if provider in {"openrouter", "ollama"} else "openrouter"


def get_ollama_base_url() -> str:
    config = load_config()
    url = (config.get("ollama_base_url") or "").strip()
    if url:
        return url.rstrip("/")
    env = (os.environ.get("OLLAMA_BASE_URL") or "").strip()
    if env:
        return env.rstrip("/")
    return DEFAULT_OLLAMA_BASE_URL


def resolve_llm_endpoint() -> tuple[str, str]:
    """Return (base_url, api_key) for the OpenAI-compatible client."""
    if get_provider() == "ollama":
        return get_ollama_base_url(), OLLAMA_API_KEY

    from config_store import get_openrouter_api_key

    return OPENROUTER_BASE_URL, get_openrouter_api_key() or "missing-key"
