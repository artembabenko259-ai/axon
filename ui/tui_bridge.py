"""WebSocket bridge host for the fullscreen TUI (Zenith dashboard sync)."""

from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any

from bridge import AxonBridge
from llm_client import TOTAL_COST, TOTAL_TOKENS
from ui import tui_render

if TYPE_CHECKING:
    from ui.axon_tui import AxonTUI


class TuiBridgeHost:
    """Runs AxonBridge on a background asyncio loop; feeds web chat into the TUI."""

    def __init__(self) -> None:
        self._bridge = AxonBridge()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._tui_loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._tui: AxonTUI | None = None
        self._web_inbox: queue.Queue[str] = queue.Queue()
        self._started = False

    def attach(self, tui: AxonTUI) -> None:
        self._tui = tui

    def set_tui_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Prompt-toolkit asyncio loop (main TUI thread)."""
        self._tui_loop = loop

    def enqueue_web_message(self, text: str) -> None:
        cleaned = text.strip()
        if cleaned:
            self._web_inbox.put(cleaned)

    def _schedule(self, coro: Coroutine[Any, Any, Any]) -> None:
        loop = self._loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
            return
        coro.close()

    async def sync_stats(self) -> None:
        await self._bridge.broadcast_stats(TOTAL_TOKENS, TOTAL_COST)

    async def broadcast_model(self, model: str) -> None:
        await self._bridge.broadcast_model(model)

    async def broadcast_chat(
        self,
        *,
        role: str,
        text: str,
        source: str = "terminal",
    ) -> None:
        await self._bridge.broadcast_chat(role=role, text=text, source=source)

    async def broadcast_tool(self, tool: str, status: str, detail: str) -> None:
        await self._bridge.broadcast_tool_event(tool, status, detail)

    def sync_stats_now(self) -> None:
        self._schedule(self.sync_stats())

    def broadcast_model_now(self, model: str) -> None:
        if model.strip():
            self._schedule(self.broadcast_model(model))

    def broadcast_chat_now(
        self,
        *,
        role: str,
        text: str,
        source: str = "terminal",
    ) -> None:
        if text.strip():
            self._schedule(self.broadcast_chat(role=role, text=text, source=source))

    def broadcast_tool_now(self, tool: str, status: str, detail: str) -> None:
        self._schedule(self.broadcast_tool(tool, status, detail))

    def broadcast_plan_now(self, tasks: list[dict[str, object]], goal: str = "") -> None:
        self._schedule(self._bridge.broadcast_plan_update(tasks, goal=goal))

    def broadcast_multitask_now(
        self,
        phase: str,
        goal: str,
        subtasks: list[dict[str, object]],
        synthesis: str = "",
    ) -> None:
        self._schedule(
            self._bridge.broadcast_multitask_update(
                phase, goal, subtasks, synthesis=synthesis
            )
        )

    async def _process_web_chat(self, text: str, source: str) -> None:
        if source != "web":
            return
        self.enqueue_web_message(text)

    def _apply_model_on_tui(self, model: str) -> str:
        """Apply model on the prompt-toolkit thread; return normalized id."""
        from ui.model_registry import normalize_model_id

        tui = self._tui
        target = normalize_model_id(model.strip())
        if tui is None or not target:
            return target

        done = threading.Event()

        def apply() -> None:
            try:
                tui.llm.set_model(target)
                tui.state.model = tui.llm.model
                from prompt_toolkit.application import get_app

                get_app().invalidate()
            finally:
                done.set()

        loop = self._tui_loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(apply)
            done.wait(timeout=3.0)
        else:
            apply()
        return tui.llm.model

    async def _set_model(self, model: str) -> None:
        if not model.strip():
            return
        normalized = self._apply_model_on_tui(model)
        if normalized:
            await self._bridge.broadcast_model(normalized)

    async def _run_bridge(self) -> None:
        tui = self._tui
        if tui is None:
            return

        self._bridge.configure(
            process_chat=self._process_web_chat,
            set_model=self._set_model,
            refresh_ui=lambda: None,
            current_model=tui.llm.model,
        )
        await self._bridge.start()

        while True:
            await asyncio.sleep(10)
            await self.sync_stats()

    def start(self) -> None:
        if self._started:
            return
        self._started = True

        def runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            loop.run_until_complete(self._run_bridge())

        self._thread = threading.Thread(
            target=runner,
            name="axon-tui-bridge",
            daemon=True,
        )
        self._thread.start()

    async def drain_web_inbox(self) -> None:
        """Poll inbox from the TUI asyncio loop (prompt_toolkit)."""
        while True:
            try:
                text = self._web_inbox.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.15)
                continue
            tui = self._tui
            if tui is None:
                continue
            if tui._agent_busy:
                self._web_inbox.put(text)
                await asyncio.sleep(0.25)
                continue
            w = tui._width()
            tui._append_block(tui_render.render_user_message(text, w))
            from prompt_toolkit.application import get_app

            get_app().invalidate()
            await tui._process_message(text)
