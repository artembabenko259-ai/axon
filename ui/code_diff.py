"""Cursor-style inline diff previews for file edits (TUI + approval flow)."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

APPROVAL_PREVIEW_MARKER = "\n---AXON_DIFF---\n"
MAX_DIFF_LINES = 48


def combine_approval_message(detail: str, preview: str) -> str:
    if preview.strip():
        return f"{detail}{APPROVAL_PREVIEW_MARKER}{preview.strip()}"
    return detail


def split_approval_message(text: str) -> tuple[str, str]:
    if APPROVAL_PREVIEW_MARKER in text:
        detail, preview = text.split(APPROVAL_PREVIEW_MARKER, 1)
        return detail.strip(), preview.strip()
    return text.strip(), ""


def _resolve_path(filepath: str) -> Path | None:
    raw = filepath.strip()
    if not raw:
        return None
    try:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        else:
            path = path.resolve()
        return path
    except OSError:
        return None


def _read_original(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _simulate_patch(original: str, patch: str) -> str | None:
    lines = original.splitlines(keepends=True)
    patch_text = patch.replace("\r\n", "\n")

    ops: list[tuple[str, str]] = []
    for raw in patch_text.splitlines():
        if raw.startswith("@@") or raw.startswith("---") or raw.startswith("+++"):
            continue
        if raw and raw[0] in " -+":
            ops.append((raw[0], raw[1:]))

    out: list[str] = []
    src_i = 0
    src = [ln.rstrip("\n") for ln in lines]
    for op, text in ops:
        if op == " ":
            if src_i < len(src) and src[src_i] == text:
                out.append(src[src_i] + "\n")
                src_i += 1
            elif src_i < len(src):
                return None
            else:
                out.append(text + "\n")
        elif op == "-":
            if src_i < len(src) and src[src_i] == text:
                src_i += 1
            else:
                return None
        elif op == "+":
            out.append(text + "\n")
    out.extend(ln + "\n" for ln in src[src_i:])
    return "".join(out)


def _display_rel_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def _inline_diff_lines(
    path_label: str,
    before: str,
    after: str,
    *,
    max_lines: int = MAX_DIFF_LINES,
) -> list[str]:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    diff = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{path_label}",
            tofile=f"b/{path_label}",
            lineterm="",
        )
    )
    if not diff:
        return []

    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    header = f"@@ {_display_path_label(path_label)} (+{added} -{removed})"

    body: list[str] = [header]
    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("@@"):
            continue
        body.append(line)
        if len(body) >= max_lines:
            body.append(f"... [{len(diff) - max_lines} more diff lines truncated]")
            break
    return body


def _display_path_label(path_label: str) -> str:
    return path_label.replace("\\", "/")


def build_approval_preview(tool_name: str, args: dict[str, Any]) -> str:
    """Build a compact unified-diff preview for write_file / apply_patch."""
    filepath = str(args.get("filepath", "")).strip()
    if not filepath:
        return ""

    path = _resolve_path(filepath)
    if path is None:
        return ""

    rel = _display_rel_path(path)
    original = _read_original(path)

    if tool_name == "write_file":
        new_content = str(args.get("content", ""))
        if original == new_content:
            return f"@@ {rel} (no changes)"
        lines = _inline_diff_lines(rel, original, new_content)
        return "\n".join(lines)

    if tool_name == "apply_patch":
        patch = str(args.get("patch", ""))
        if not patch.strip():
            return ""
        patched = _simulate_patch(original, patch)
        if patched is None:
            patch_lines = [
                line
                for line in patch.replace("\r\n", "\n").splitlines()
                if line and line[0] in " +-"
            ]
            preview = "\n".join(patch_lines[:MAX_DIFF_LINES])
            if len(patch_lines) > MAX_DIFF_LINES:
                preview += f"\n... [{len(patch_lines) - MAX_DIFF_LINES} more patch lines]"
            return f"@@ {rel}\n{preview}"
        lines = _inline_diff_lines(rel, original, patched)
        return "\n".join(lines)

    return ""
