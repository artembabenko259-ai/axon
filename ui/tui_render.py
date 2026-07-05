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
    items: list[tuple[str, str, TaskStatus, str]],
    width: int,
    *,
    header: str = "To-dos",
) -> str:
    """Cursor-style checklist. items: (key, label, status, agent)."""
    if not items:
        return ""
    count = len(items)
    lines = [f"{header}  {count}", ""]
    if title.strip():
        lines.insert(0, title.strip()[: width - 2])
        lines.insert(1, "")
    for _key, label, status, agent in items:
        icon = _status_icon(status)
        text = label.strip()
        if agent.strip():
            text = f"[{agent}] {text}"
        if len(text) > width - 6:
            text = text[: width - 9] + "..."
        prefix = "  " if status != "running" else "> "
        lines.append(f"{prefix}{icon} {text}")
    return "\n".join(lines)


def render_session_timeline(
    *,
    files: list[str],
    skills: list[str],
    events: list[tuple[str, str, str]],
    cost_delta: float,
    width: int,
) -> str:
    """Mini session memory panel (Cursor timeline style)."""
    lines = ["Session", ""]
    if cost_delta < 0.01:
        lines.append(f"Cost  ${cost_delta:.6f}")
    else:
        lines.append(f"Cost  ${cost_delta:.4f}")
    if skills:
        lines.append("")
        lines.append("Skills")
        for name in skills[-6:]:
            lines.append(f"  * {name[: width - 6]}")
    if files:
        lines.append("")
        lines.append("Files")
        for path in files[-6:]:
            short = path if len(path) <= width - 4 else "..." + path[-(width - 7) :]
            lines.append(f"  * {short}")
    if events:
        lines.append("")
        lines.append("Recent")
        for kind, label, agent in events[-8:]:
            tag = kind[:1].upper()
            who = f"@{agent} " if agent and agent != "AXON" else ""
            text = f"{who}{label}"
            if len(text) > width - 6:
                text = text[: width - 9] + "..."
            lines.append(f"  {tag} {text}")
    if len(lines) <= 3:
        lines.append("")
        lines.append("  (empty session)")
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
    """Live assistant block — thinking and answer are separate; omit empty shells."""
    parts: list[str] = []
    if thinking.strip():
        parts.append(render_thinking(thinking, width))
    if text.strip():
        body = _wrap(text.strip(), max(width - 2, 40))
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
        f"| F2 tasks . F3 thinking . F4 session . V diff . 1/2/3 approve\n"
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


def format_cost_usd(cost: float) -> str:
    if cost <= 0:
        return "$0.00"
    if cost < 0.01:
        return f"${cost:.6f}"
    return f"${cost:.4f}"


def format_token_count(count: int) -> str:
    n = max(int(count), 0)
    if n < 10_000:
        return f"{n:,}"
    if n < 1_000_000:
        text = f"{n / 1000:.1f}k"
        return text.replace(".0k", "k")
    return f"{n / 1_000_000:.2f}M"


def format_usage_header(
    *,
    total_tokens: int,
    prompt_tokens: int,
    completion_tokens: int,
    cost: float,
) -> str:
    """Compact header: cost + in/out token split."""
    cost_s = format_cost_usd(cost)
    if total_tokens <= 0:
        return f"{cost_s} | 0 tok"
    if prompt_tokens or completion_tokens:
        return (
            f"{cost_s} | {format_token_count(total_tokens)} tok "
            f"({format_token_count(prompt_tokens)} in · "
            f"{format_token_count(completion_tokens)} out)"
        )
    return f"{cost_s} | {format_token_count(total_tokens)} tok"


def render_turn_usage(
    width: int,
    *,
    turn_prompt: int = 0,
    turn_completion: int = 0,
    turn_total: int = 0,
    session_total: int = 0,
    session_prompt: int = 0,
    session_completion: int = 0,
    session_cost: float = 0.0,
) -> str:
    """Per-turn + session usage line (shown after each assistant reply)."""
    parts: list[str] = []
    if turn_total > 0 or turn_prompt or turn_completion:
        turn_cost_note = ""
        parts.append(
            "Turn: "
            f"{format_token_count(turn_total or turn_prompt + turn_completion)} tok "
            f"({format_token_count(turn_prompt)} in · "
            f"{format_token_count(turn_completion)} out){turn_cost_note}"
        )
    parts.append(
        "Session: "
        f"{format_token_count(session_total)} tok "
        f"({format_token_count(session_prompt)} in · "
        f"{format_token_count(session_completion)} out) · "
        f"{format_cost_usd(session_cost)}"
    )
    return _wrap(" · ".join(parts), width)


def render_session_usage_detail(
    width: int,
    *,
    total_tokens: int,
    prompt_tokens: int,
    completion_tokens: int,
    cost: float,
    model: str = "",
) -> str:
    lines = [
        f"Session tokens: {total_tokens:,} total",
        f"  input:  {prompt_tokens:,}",
        f"  output: {completion_tokens:,}",
        f"Session cost: {format_cost_usd(cost)}",
    ]
    if model:
        lines.append(f"Model: {model}")
    if total_tokens <= 0:
        lines.append("(Usage appears after the first API response with billing data.)")
    return _wrap("\n".join(lines), width)


DIFF_PEEK_LINES = 4


def _format_diff_line(raw: str, width: int) -> str:
    line = raw.rstrip()
    if line.startswith("+++ ") or line.startswith("--- "):
        return f"  {line}"
    if line.startswith("+"):
        body = line[1:]
        prefix = "+ "
    elif line.startswith("-"):
        body = line[1:]
        prefix = "- "
    elif line.startswith("..."):
        return f"  {line}"
    elif line.startswith("@@ "):
        return line
    else:
        body = line[1:] if line.startswith(" ") else line
        prefix = "  "
    if len(body) > width - 6:
        body = body[: width - 9] + "..."
    return f"{prefix}{body}"


def render_change_preview(
    diff_text: str,
    width: int,
    *,
    expanded: bool = False,
    peek_lines: int = DIFF_PEEK_LINES,
) -> str:
    """Cursor-style diff: file header, peek of changes, V to expand."""
    text = diff_text.strip()
    if not text:
        return ""

    raw_lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    header_line = ""
    body_lines: list[str] = []

    for line in raw_lines:
        if line.startswith("@@ ") and not header_line:
            header_line = line
        else:
            body_lines.append(line)

    title = header_line[3:].strip() if header_line.startswith("@@ ") else "changes"
    bar = "─" * min(max(width - 2, 24), 72)
    countable = [line for line in body_lines if not line.startswith("... [")]

    lines_out: list[str] = [f"┌ {title}", bar]

    hidden = max(0, len(countable) - peek_lines)
    if expanded or hidden == 0:
        for raw in body_lines:
            lines_out.append(_format_diff_line(raw, width))
        if expanded and hidden > 0:
            lines_out.append(f"  ▲ свернуть — V")
    else:
        for raw in countable[:peek_lines]:
            lines_out.append(_format_diff_line(raw, width))
        lines_out.append(f"  ▼ ещё {hidden} строк — V развернуть")

    lines_out.append(bar)
    return "\n".join(lines_out)


def render_approval_request(
    detail: str,
    width: int,
    *,
    preview: str = "",
    preview_expanded: bool = False,
) -> str:
    parts: list[str] = []
    if preview.strip():
        parts.append(
            render_change_preview(preview, width, expanded=preview_expanded)
        )
    body = _wrap(detail.strip(), max(width - 4, 40))
    menu = (
        "! Нужно разрешение\n"
        f"{body}\n\n"
        "  [1] Разрешить один раз\n"
        "  [2] Разрешить на всю сессию\n"
        "  [3] Отклонить\n"
        "\n"
        "  Нажми 1, 2 или 3 (или Y / N). Подсказка — в строке статуса внизу."
    )
    parts.append(menu)
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
