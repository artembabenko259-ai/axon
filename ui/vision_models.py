"""Vision capability from OpenRouter model metadata (not name guessing)."""

from __future__ import annotations

from typing import Any, Literal

VisionCapability = Literal["yes", "no", "unknown"]

_IMAGE_MODALITIES = frozenset({"image", "file", "video"})

SUGGESTED_VISION_MODELS = (
    "google/gemma-4-31b-it:free",
    "moonshotai/kimi-k2.7-code",
    "google/gemini-2.0-flash-001",
    "openai/gpt-4o-mini",
)


def _model_records() -> dict[str, dict[str, Any]]:
    from pricing import fetch_model_records

    return fetch_model_records()


def _lookup_record(model_id: str) -> dict[str, Any] | None:
    models = _model_records()
    if not model_id:
        return None
    if model_id in models:
        return models[model_id]
    if "/" in model_id:
        slug = model_id.split("/", 1)[1]
        if slug in models:
            return models[slug]
    tail = model_id.rsplit("/", 1)[-1]
    return models.get(tail)


def model_input_modalities(model_id: str) -> list[str] | None:
    """Return OpenRouter input_modalities, or None if model is not in cache."""
    record = _lookup_record(model_id)
    if not record:
        return None
    raw = record.get("input_modalities")
    if not isinstance(raw, list):
        return None
    return [str(item).lower() for item in raw if str(item).strip()]


def vision_capability(model_id: str) -> VisionCapability:
    """Authoritative when OpenRouter cache has the model; otherwise unknown."""
    modalities = model_input_modalities(model_id)
    if modalities is None:
        return "unknown"
    if any(modality in _IMAGE_MODALITIES for modality in modalities):
        return "yes"
    return "no"


def is_confirmed_non_vision(model_id: str) -> bool:
    """True only when OpenRouter lists text-only input (safe to warn)."""
    return vision_capability(model_id) == "no"


def is_vision_model(model_id: str) -> bool:
    """Optimistic for unknown models — avoids false blocks on new multimodal IDs."""
    capability = vision_capability(model_id)
    return capability in {"yes", "unknown"}


def vision_required_message(current_model: str) -> str:
    suggestions = ", ".join(SUGGESTED_VISION_MODELS[:2])
    return (
        f"Model `{current_model}` is text-only on OpenRouter (no image input). "
        f"Switch with /model, e.g.: {suggestions}"
    )


def vision_switch_hint(current_model: str) -> str:
    _ = current_model
    for candidate in SUGGESTED_VISION_MODELS:
        if vision_capability(candidate) != "no":
            return f"/model {candidate}"
    return f"/model {SUGGESTED_VISION_MODELS[0]}"
