"""Resolve OpenRouter model ids (short names → provider/slug)."""

from __future__ import annotations


def normalize_model_id(model: str) -> str:
    """Map aliases like `gemma-4-31b-it:free` to `google/gemma-4-31b-it:free`."""
    cleaned = (model or "").strip()
    if not cleaned:
        return cleaned

    from pricing import fetch_model_records

    records = fetch_model_records()
    if cleaned in records:
        return cleaned

    tail = cleaned.rsplit("/", 1)[-1]
    matches = [mid for mid in records if mid.rsplit("/", 1)[-1] == tail]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        if ":free" in tail:
            free = [mid for mid in matches if mid.endswith(":free")]
            if len(free) == 1:
                return free[0]
        non_free = [mid for mid in matches if not mid.endswith(":free")]
        if len(non_free) == 1:
            return non_free[0]

    return cleaned
