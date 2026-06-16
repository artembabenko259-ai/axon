"""Plain-text TUI transcript blocks (no ANSI — safe inside prompt_toolkit buffers)."""

from __future__ import annotations

import textwrap


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
        f"| Enter send . Ctrl+J newline . /help\n"
        f"+{bar}+"
    )


def render_user_message(text: str, width: int) -> str:
    body = _wrap(text, max(width - 2, 40))
    return f"> You\n{body}"


def render_assistant_message(text: str, width: int) -> str:
    body = _wrap(text.strip(), max(width - 2, 40))
    return f"* AXON\n{body}"


def render_tool_event(tool: str, detail: str, width: int, *, phase: str = "run") -> str:
    mark = "*" if phase == "run" else "+"
    extra = f" {detail.strip()}" if detail.strip() else ""
    return f"  {mark} {tool}{extra}"


def render_approval_request(detail: str, width: int) -> str:
    body = _wrap(detail.strip(), max(width - 4, 40))
    return f"! Permission required\n{body}\n  1 once  2 session  3 deny"


def render_system(text: str, width: int) -> str:
    return _wrap(text, max(width - 2, 40))


def render_error(text: str, width: int) -> str:
    return f"! {_wrap(text, max(width - 4, 40))}"


def render_turn_divider(width: int) -> str:
    return "-" * min(max(width - 2, 20), 72)
