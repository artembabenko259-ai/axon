"""Heuristics for vision-capable OpenRouter / local models."""

from __future__ import annotations

_VISION_HINTS = (
    "claude-3",
    "claude-sonnet-4",
    "claude-opus-4",
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-4.1",
    "gemini",
    "pixtral",
    "llava",
    "qwen-vl",
    "qwen2-vl",
    "vision",
    "vl-",
    "-vl",
    "llama-3.2-vision",
    "llama-4",
)

_NON_VISION_BLOCK = (
    "gemma",
    "llama-3.1-8b",
    "llama-3.1-70b",
    "deepseek-r1",
    "mistral-7b",
    "phi-",
)

SUGGESTED_VISION_MODELS = (
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o-mini",
    "google/gemini-2.0-flash-001",
)


def is_vision_model(model_id: str) -> bool:
    lower = (model_id or "").lower()
    if not lower:
        return False
    for block in _NON_VISION_BLOCK:
        if block in lower and "vision" not in lower and "vl" not in lower:
            if "gpt-4o" not in lower:
                return False
    return any(hint in lower for hint in _VISION_HINTS)


def vision_required_message(current_model: str) -> str:
    suggestions = ", ".join(SUGGESTED_VISION_MODELS[:2])
    return (
        f"Model `{current_model}` likely cannot see images. "
        f"Switch with /model, e.g.: {suggestions}"
    )


def vision_switch_hint(current_model: str) -> str:
    """Short offer to switch model for /image."""
    pick = SUGGESTED_VISION_MODELS[0]
    return f"/model {pick}"
