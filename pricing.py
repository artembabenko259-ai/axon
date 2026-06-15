from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import urllib.request

from axon_runtime import user_data_dir

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
CACHE_PATH = user_data_dir() / "model_pricing_cache.json"
CACHE_TTL_SECONDS = 3600


def _load_cache() -> dict[str, Any] | None:
    if not CACHE_PATH.is_file():
        return None
    try:
        raw = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if time.time() - float(raw.get("fetched_at", 0)) > CACHE_TTL_SECONDS:
            return None
        return raw
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _save_cache(models: dict[str, dict[str, float]]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps({"fetched_at": time.time(), "models": models}, indent=2),
        encoding="utf-8",
    )


def _fetch_models() -> dict[str, dict[str, float]]:
    cached = _load_cache()
    if cached and isinstance(cached.get("models"), dict):
        return cached["models"]

    models: dict[str, dict[str, float]] = {}
    try:
        with urllib.request.urlopen(OPENROUTER_MODELS_URL, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        for item in payload.get("data", []):
            model_id = str(item.get("id", ""))
            pricing = item.get("pricing") or {}
            prompt = float(pricing.get("prompt") or 0)
            completion = float(pricing.get("completion") or 0)
            if model_id:
                models[model_id] = {
                    "prompt": prompt,
                    "completion": completion,
                }
        if models:
            _save_cache(models)
    except Exception:
        if cached and isinstance(cached.get("models"), dict):
            return cached["models"]
    return models


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    models = _fetch_models()
    rates = models.get(model) or models.get(model.split("/")[-1])
    if not rates:
        return (prompt_tokens + completion_tokens) * 0.000002
    return (prompt_tokens * rates.get("prompt", 0)) + (
        completion_tokens * rates.get("completion", 0)
    )
