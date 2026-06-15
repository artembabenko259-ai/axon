from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from axon_runtime import user_data_dir

GLOBAL_PROMPT_PATH = user_data_dir() / "system_prompt.md"


def _read_file(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def get_global_system_prompt() -> str:
    """Persistent user-level instructions (all sessions)."""
    return _read_file(GLOBAL_PROMPT_PATH)


def save_global_system_prompt(text: str) -> Path:
    GLOBAL_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned = text.strip()
    if cleaned:
        GLOBAL_PROMPT_PATH.write_text(cleaned + "\n", encoding="utf-8")
    elif GLOBAL_PROMPT_PATH.exists():
        GLOBAL_PROMPT_PATH.unlink()
    return GLOBAL_PROMPT_PATH


def clear_global_system_prompt() -> None:
    save_global_system_prompt("")


def global_prompt_path() -> Path:
    return GLOBAL_PROMPT_PATH


def edit_text_in_editor(initial: str, *, comment: str = "") -> str | None:
    """Open the user's editor and return updated text, or None if unchanged/cancelled."""
    editor = (os.environ.get("EDITOR") or os.environ.get("VISUAL") or "").strip()
    if not editor and os.name == "nt":
        editor = "notepad"

    if not editor:
        return None

    header = ""
    if comment:
        header = "\n".join(f"# {line}" for line in comment.splitlines()) + "\n\n"

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".md",
        delete=False,
    ) as handle:
        handle.write(header + initial.strip() + "\n")
        temp_path = Path(handle.name)

    try:
        before = temp_path.read_text(encoding="utf-8")
        if os.name == "nt" and Path(editor).stem.lower() == "notepad":
            subprocess.run(["notepad", "/wait", str(temp_path)], check=False)
        else:
            subprocess.run([editor, str(temp_path)], check=False)
        after = temp_path.read_text(encoding="utf-8")
    finally:
        temp_path.unlink(missing_ok=True)

    if after == before:
        return None

    lines = after.splitlines()
    body = "\n".join(line for line in lines if not line.lstrip().startswith("#"))
    return body.strip()


def preview_text(text: str, limit: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact or "(empty)"
    return compact[: limit - 1] + "…"
