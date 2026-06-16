"""Plain-text TUI transcript blocks (no ANSI — safe inside prompt_toolkit buffers)."""

from __future__ import annotations

import textwrap

from skills.tools import format_tool_activity_line


def _wrap(text: str, width: int) -> str:
    if width < 20:
        return text
    lines: list[str] = []
    for paragraph in text.strip().splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(
            textwrap.wrap(
                paragraph,
                width=width,
                break_long_words=False,
                break_on_hyphens=False,
            )
            or [""]
        )
    return "\n".join(lines)


from typing import Literal

TaskStatus = Literal["pending", "running", "done", "failed"]


def _status_icon(status: TaskStatus) -> str:
    return {
        "pending": "o",
        "running": ">",
        "done": "x",
        "failed": "!",
    }.get(status, "o")


def render_task_board(
    title: str,
    items: list[tuple[str, str, TaskStatus]],
    width: int,
    *,
    header: str = "To-dos",
) -> str:
    """Cursor-style checklist (plain ASCII). items: (key, label, status)."""
    if not items:
        return ""
    count = len(items)
    lines = [f"{header}  {count}", ""]
    for _key, label, status in items:
        icon = _status_icon(status)
        text = label.strip()
        if len(text) > width - 6:
            text = text[: width - 9] + "..."
        prefix = "  " if status != "running" else "> "
        lines.append(f"{prefix}{icon} {text}")
    return "\n".join(lines)


def render_agent_activity(label: str, detail: str, width: int) -> str:
    """Cursor-style tool activity line in the transcript."""
    line = format_tool_activity_line(label, detail)
    if len(line) > width - 2:
        line = line[: width - 5] + "..."
    return f"  › {line}"


def render_thinking(text: str, width: int) -> str:
    body = _wrap(text.strip(), max(width - 4, 40))
    return f"~ thinking\n{body}"


def render_assistant_live(
    text: str,
    width: int,
    *,
    thinking: str = "",
) -> str:
    parts: list[str] = []
    if thinking.strip():
        parts.append(render_thinking(thinking, width))
    body = _wrap(text, max(width - 2, 40)) if text else "..."
    parts.append(f"* AXON\n{body}")
    return "\n\n".join(parts)


def render_welcome(width: int, *, model: str, cwd: str) -> str:
    short = model.rsplit("/", 1)[-1]
    if len(cwd) > width - 4:
        cwd = "..." + cwd[-(width - 8) :]
    bar = "-" * min(max(width - 2, 24), 56)
    return (
        f"+{bar}+\n"
        f"| AXON - agentic terminal\n"
        f"| {short}\n"
        f"| {cwd}\n"
        f"| Enter send . Enter+Up steer . /help\n"
        f"+{bar}+"
    )


def render_user_message(text: str, width: int) -> str:
    body = _wrap(text, max(width - 2, 40))
    return f"> You\n{body}"


def render_assistant_message(text: str, width: int) -> str:
    body = _wrap(text.strip(), max(width - 2, 40))
    return f"* AXON\n{body}"


def render_tool_event(tool: str, detail: str, width: int, *, phase: str = "run") -> str:
    mark = "›" if phase == "run" else "✓"
    line = format_tool_activity_line(tool, detail)
    if len(line) > width - 4:
        line = line[: width - 7] + "..."
    return f"  {mark} {line}"


def render_turn_divider(width: int) -> str:
    return "-" * min(max(width - 2, 20), 72)


def render_change_preview(diff_text: str, width: int) -> str:
    """Cursor-style inline diff block (plain text for prompt_toolkit buffers)."""
    text = diff_text.strip()
    if not text:
        return ""

    lines: list[str] = []
    bar = "─" * min(max(width - 2, 24), 72)

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("@@ "):
            lines.append(line)
            lines.append(bar)
            continue
        if line.startswith("+"):
            body = line[1:]
            if len(body) > width - 6:
                body = body[: width - 9] + "..."
            lines.append(f"+ {body}")
        elif line.startswith("-"):
            body = line[1:]
            if len(body) > width - 6:
                body = body[: width - 9] + "..."
            lines.append(f"- {body}")
        elif line.startswith("..."):
            lines.append(f"  {line}")
        else:
            if len(line) > width - 4:
                line = line[: width - 7] + "..."
            lines.append(f"  {line}")

    return "\n".join(lines)


def render_approval_request(detail: str, width: int, *, preview: str = "") -> str:
    parts: list[str] = []
    if preview.strip():
        parts.append(render_change_preview(preview, width))
    body = _wrap(detail.strip(), max(width - 4, 40))
    parts.append(f"! Allow change?\n{body}\n  1 once  2 session  3 deny")
    return "\n\n".join(part for part in parts if part)


def render_system(text: str, width: int) -> str:
    return _wrap(text, max(width - 2, 40))


def render_error(text: str, width: int) -> str:
    return f"! {_wrap(text, max(width - 4, 40))}"


def render_explore_summary(summary: str, width: int) -> str:
    text = summary.strip()
    if len(text) > width - 2:
        text = text[: width - 5] + "..."
    return f"  {text}"
