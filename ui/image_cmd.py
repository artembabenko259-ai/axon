"""`/image` — load a local image into vision model context."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})


def normalize_image_path(raw: str) -> str:
    """Strip quotes and optional Cursor-style `@` prefix."""
    cleaned = raw.strip().strip("\"'")
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]
    return cleaned


def _is_existing_image(path_str: str) -> bool:
    try:
        path = Path(path_str).expanduser()
        if not path.is_file():
            return False
        return path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    except OSError:
        return False


def _split_path_and_prompt(rest: str) -> tuple[str, str]:
    """Split `/image` tail into path + prompt; handles Windows paths with spaces."""
    cleaned = rest.strip()
    if not cleaned:
        return "", "Analyze this image."

    if _is_existing_image(cleaned):
        return normalize_image_path(cleaned), "Analyze this image."

    parts = cleaned.split()
    if len(parts) > 1:
        for end in range(len(parts), 0, -1):
            candidate = " ".join(parts[:end])
            if _is_existing_image(candidate):
                prompt = " ".join(parts[end:]).strip() or "Analyze this image."
                return normalize_image_path(candidate), prompt
        first = normalize_image_path(parts[0])
        prompt = " ".join(parts[1:]).strip() or "Analyze this image."
        return first, prompt

    return normalize_image_path(cleaned), "Analyze this image."


def parse_image_command(text: str) -> tuple[str, str]:
    """Parse `/image <path|@path> [prompt]` supporting quoted paths and spaces."""
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

    return _split_path_and_prompt(rest)


def resolve_image_path(raw: str) -> tuple[Path | None, str | None]:
    """Resolve image path; tolerate missing extensions and Windows screenshot names."""
    cleaned = normalize_image_path(raw)
    if not cleaned:
        return None, "AXON: Image path is required."

    path = Path(cleaned).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path)

    try:
        path = path.resolve()
    except OSError as exc:
        return None, f"AXON: Invalid image path — {exc}"

    if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
        return path, None

    stem_path = path
    if path.suffix and path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        stem_path = path.with_suffix("")

    if not stem_path.suffix:
        for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
            candidate = Path(f"{stem_path}{ext}")
            if candidate.is_file():
                return candidate.resolve(), None

    parent = stem_path.parent
    name = stem_path.name
    if parent.is_dir() and name:
        matches: list[Path] = []
        for ext in SUPPORTED_IMAGE_SUFFIXES:
            matches.extend(sorted(parent.glob(f"{name}*{ext}")))
        unique = list(dict.fromkeys(matches))
        if len(unique) == 1:
            return unique[0].resolve(), None
        if len(unique) > 1:
            sample = ", ".join(item.name for item in unique[:4])
            extra = f" (+{len(unique) - 4} more)" if len(unique) > 4 else ""
            return None, (
                f"AXON: Ambiguous image name `{name}` — {sample}{extra}. "
                "Use quotes: /image \"path\\file name.png\""
            )

    return None, (
        f"AXON: Image not found — {path}. "
        "Quote paths with spaces: /image \"C:\\folder\\Снимок экрана.png\""
    )


def load_image_with_vision_check(
    llm: object,
    image_path: str,
    prompt: str,
) -> str | None:
    """Load image into context; warn only for OpenRouter-confirmed text-only models."""
    from ui.vision_models import is_confirmed_non_vision, vision_required_message

    model = str(getattr(llm, "model", ""))
    if model and is_confirmed_non_vision(model):
        return vision_required_message(model)

    resolved, resolve_error = resolve_image_path(image_path)
    if resolve_error:
        return resolve_error

    loader = getattr(llm, "load_image_into_context", None)
    if not callable(loader):
        return "AXON: image loader unavailable."
    return loader(str(resolved), prompt)
