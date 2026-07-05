"""REPL/TUI `/autopilot` — Autopilot full autonomy (admin + explicit enable)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from autopilot_mode import (
    disable_autopilot,
    enable_autopilot,
    autopilot_status_lines,
)

Emit = Callable[[Any], Awaitable[None]]


async def handle_autopilot_command(stripped: str, *, emit: Emit) -> bool:
    lower = stripped.lower()
    if not lower.startswith("/autopilot"):
        return False

    parts = stripped.split(maxsplit=1)
    action = parts[1].strip().lower() if len(parts) > 1 else "status"

    if action in {"", "status"}:
        body = "\n".join(autopilot_status_lines())
        await emit(f"[bold]{body}[/]\n")
        return True

    if action == "on":
        ok, msg = enable_autopilot()
        color = "green" if ok else "red"
        await emit(f"[{color}]{msg}[/]\n")
        return True

    if action == "off":
        await emit(f"[green]{disable_autopilot()}[/]\n")
        return True

    await emit(
        "[yellow]Usage: /autopilot on | /autopilot off | /autopilot status[/]\n"
        "[dim]Autopilot auto-approves write/shell/patch when running as Administrator.[/]\n"
    )
    return True
