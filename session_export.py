"""Export AXON chat sessions to Markdown reports."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from axon_runtime import user_data_dir
from session_store import SessionData, load_session

EXPORTS_DIR = user_data_dir() / "exports"


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif block.get("type") == "image_url":
                    parts.append("[image attached]")
        return "\n".join(p for p in parts if p).strip()
    return str(content).strip()


def messages_to_markdown(
    messages: list[dict[str, Any]],
    *,
    title: str = "AXON Session",
    model: str = "",
    tokens: int = 0,
) -> str:
    lines = [
        f"# {title}",
        "",
        f"- **Exported:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    if model:
        lines.append(f"- **Model:** `{model}`")
    if tokens:
        lines.append(f"- **Tokens:** {tokens}")
    lines.extend(["", "---", ""])

    for msg in messages:
        role = str(msg.get("role", "unknown")).lower()
        if role == "system":
            continue
        text = _message_text(msg.get("content", ""))
        if not text:
            continue
        heading = {"user": "You", "assistant": "AXON", "tool": "Tool"}.get(
            role, role.title()
        )
        lines.append(f"## {heading}")
        lines.append("")
        lines.append(text)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def export_session_markdown(
    session_id: str,
    *,
    output: Path | None = None,
) -> Path:
    data = load_session(session_id)
    if not data:
        raise FileNotFoundError(f"Session not found: {session_id}")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(
        c if c.isalnum() or c in "-_" else "-" for c in data.meta.title[:40]
    ).strip("-") or "session"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = output or (EXPORTS_DIR / f"{safe_title}-{data.meta.id[:8]}-{stamp}.md")

    body = messages_to_markdown(
        data.messages,
        title=data.meta.title,
        model=data.meta.model,
        tokens=data.meta.tokens,
    )
    target.write_text(body, encoding="utf-8")
    return target


def export_messages_markdown(
    messages: list[dict[str, Any]],
    *,
    title: str = "AXON Session",
    model: str = "",
    tokens: int = 0,
    output: Path | None = None,
) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = output or (EXPORTS_DIR / f"export-{stamp}.md")
    body = messages_to_markdown(
        messages, title=title, model=model, tokens=tokens
    )
    target.write_text(body, encoding="utf-8")
    return target
