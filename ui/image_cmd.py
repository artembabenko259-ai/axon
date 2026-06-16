"""`/image` — load a local image into vision model context."""

from __future__ import annotations


def normalize_image_path(raw: str) -> str:
    """Strip quotes and optional Cursor-style `@` prefix."""
    cleaned = raw.strip().strip("\"'")
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]
    return cleaned


def parse_image_command(text: str) -> tuple[str, str]:
    """Parse `/image <path|@path> [prompt]` supporting quoted paths."""
    rest = text[6:].strip() if text.lower().startswith("/image") else ""
    if not rest:
        return "", "Analyze this image."

    if rest[0] in "\"'":
        quote = rest[0]
        end = rest.find(quote, 1)
        if end == -1:
            return normalize_image_path(rest.strip(quote)), "Analyze this image."
        path = normalize_image_path(rest[1:end])
        prompt = rest[end + 1 :].strip() or "Analyze this image."
        return path, prompt

    parts = rest.split(maxsplit=1)
    path = normalize_image_path(parts[0])
    prompt = parts[1].strip() if len(parts) > 1 else "Analyze this image."
    return path, prompt
