from __future__ import annotations

import re
from pathlib import Path

FILE_MENTION_PATTERN = re.compile(r"@([a-zA-Z0-9_./\\-]+)")
MAX_FILE_CONTEXT_BYTES = 48_000
MAX_TREE_ENTRIES = 200


def _resolve_mention(raw: str, cwd: Path) -> Path | None:
    cleaned = raw.strip().strip("\"'")
    if not cleaned or ".." in Path(cleaned).parts:
        return None
    candidate = Path(cleaned)
    if not candidate.is_absolute():
        candidate = cwd / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    return resolved


def _directory_tree(path: Path, *, max_depth: int = 2, _depth: int = 0) -> list[str]:
    if _depth > max_depth:
        return []

    lines: list[str] = []
    indent = "  " * _depth
    try:
        entries = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    except OSError as exc:
        return [f"{indent}(error reading directory: {exc})"]

    for entry in entries:
        if len(lines) >= MAX_TREE_ENTRIES:
            lines.append(f"{indent}… (truncated)")
            break
        if entry.name.startswith(".") and entry.name not in {".axon"}:
            continue
        suffix = "/" if entry.is_dir() else ""
        lines.append(f"{indent}{entry.name}{suffix}")
        if entry.is_dir() and _depth < max_depth:
            lines.extend(_directory_tree(entry, max_depth=max_depth, _depth=_depth + 1))

    return lines


def _read_file_snippet(path: Path) -> str:
    try:
        size = path.stat().st_size
        text = path.read_text(encoding="utf-8", errors="replace")
        if size > MAX_FILE_CONTEXT_BYTES:
            return (
                f"{text[:MAX_FILE_CONTEXT_BYTES]}\n\n"
                f"[Truncated: file is {size} bytes, showing first {MAX_FILE_CONTEXT_BYTES}]"
            )
        return text
    except OSError as exc:
        return f"(error reading file: {exc})"


def build_file_context(text: str, cwd: Path | None = None) -> tuple[str, str]:
    """
    Parse @mentions in user text.

    Returns:
        display_text — user-visible message with @path replaced by tags
        context_block — hidden context appended for the LLM (empty if none)
    """
    root = cwd or Path.cwd()
    matches = list(FILE_MENTION_PATTERN.finditer(text))
    if not matches:
        return text, ""

    display = text
    context_parts: list[str] = []
    attached_tags: list[str] = []

    for match in reversed(matches):
        raw = match.group(1)
        resolved = _resolve_mention(raw, root)
        tag = f"@{raw}"

        if resolved is None or not resolved.exists():
            replacement = f"[missing:@{raw}]"
            display = display[: match.start()] + replacement + display[match.end() :]
            continue

        if resolved.is_file():
            body = _read_file_snippet(resolved)
            context_parts.append(
                f"[Context attached by user from file `{resolved}`]\n```\n{body}\n```"
            )
            replacement = f"[file:{resolved.name}]"
        elif resolved.is_dir():
            tree_lines = _directory_tree(resolved, max_depth=2)
            tree = "\n".join(tree_lines) if tree_lines else "(empty directory)"
            context_parts.append(
                f"[Context attached by user from directory `{resolved}`]\n{tree}"
            )
            replacement = f"[dir:{resolved.name}/]"
        else:
            replacement = f"[missing:@{raw}]"
            display = display[: match.start()] + replacement + display[match.end() :]
            continue

        attached_tags.append(replacement)
        display = display[: match.start()] + replacement + display[match.end() :]

    context_parts.reverse()
    context_block = "\n\n".join(context_parts)
    return display.strip(), context_block
