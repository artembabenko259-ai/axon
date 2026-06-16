"""REPL/TUI `/claw` — OpenClaw full autonomy (admin + explicit enable)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from openclaw_mode import (
    disable_openclaw,
    enable_openclaw,
    openclaw_status_lines,
)

Emit = Callable[[Any], Awaitable[None]]


async def handle_claw_command(stripped: str, *, emit: Emit) -> bool:
    lower = stripped.lower()
    if not (lower.startswith("/claw") or lower.startswith("/openclaw")):
        return False

    parts = stripped.split(maxsplit=1)
    action = parts[1].strip().lower() if len(parts) > 1 else "status"

    if action in {"", "status"}:
        body = "\n".join(openclaw_status_lines())
        await emit(f"[bold]{body}[/]\n")
        return True

    if action == "on":
        ok, msg = enable_openclaw()
        color = "green" if ok else "red"
        await emit(f"[{color}]{msg}[/]\n")
        return True

    if action == "off":
        await emit(f"[green]{disable_openclaw()}[/]\n")
        return True

    await emit(
        "[yellow]Usage: /claw on | /claw off | /claw status[/]\n"
        "[dim]OpenClaw auto-approves write/shell/patch when running as Administrator.[/]\n"
    )
    return True
