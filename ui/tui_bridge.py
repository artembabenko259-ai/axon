"""TUI event broadcaster stub (no-op without web bridge)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ui.axon_tui import AxonTUI


class TuiBridgeHost:
    """Decoupled stub for TUI events."""

    def __init__(self) -> None:
        self._tui: AxonTUI | None = None
        self._tui_loop: asyncio.AbstractEventLoop | None = None

    def attach(self, tui: AxonTUI) -> None:
        self._tui = tui

    def set_tui_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._tui_loop = loop

    def sync_stats_now(self) -> None:
        pass

    def broadcast_model_now(self, model: str) -> None:
        pass

    def broadcast_chat_now(
        self,
        *,
        role: str,
        text: str,
        source: str = "terminal",
    ) -> None:
        pass

    def broadcast_tool_now(self, tool: str, status: str, detail: str) -> None:
        pass

    def broadcast_plan_now(self, tasks: list[dict[str, object]], goal: str = "") -> None:
        pass

    def broadcast_multitask_now(
        self,
        phase: str,
        goal: str,
        subtasks: list[dict[str, object]],
        synthesis: str = "",
    ) -> None:
        pass

    def start(self) -> None:
        pass

    async def drain_web_inbox(self) -> None:
        while True:
            await asyncio.sleep(3600)

