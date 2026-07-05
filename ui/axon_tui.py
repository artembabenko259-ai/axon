"""Desktop TUI for AXON."""

from __future__ import annotations

import asyncio
import os
import re
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from prompt_toolkit.application import Application, get_app, run_in_terminal
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition, has_completions, has_focus
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Dimension as D
from prompt_toolkit.layout import HSplit, Layout, ScrollablePane, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.styles import Style

from llm_client import (
    LLMManager,
    SESSION_COMPLETION_TOKENS,
    SESSION_PROMPT_TOKENS,
    TOTAL_COST,
    TOTAL_TOKENS,
    register_usage_listener,
    reset_session_counters,
)
from orchestrator import Orchestrator, SubTask
from plugins.loader import discover_plugins, list_plugin_commands
from runtime_policy import POLICY_PATH, load_runtime_policy
from skills.tasks import set_multitask_runner, set_plan_render_callback
from skills_manager import (
    create_skill_file,
    parse_gen_skill_description,
    save_generated_skill_file,
)
from skills.tools import (
    ApprovalDecision,
    format_tool_activity_line,
    set_tool_result_callback,
    tool_display_label,
)
from task_manager import task_manager
from ui.agent_intent import detect_intent
from ui.axon_completer import build_axon_completer
from ui.completer import AXON_COMMANDS
from ui.explore_stats import get_turn_explore_summary
from ui import tui_render
from ui.tui_taskboard import TaskBoardItem, TaskBoardState

if TYPE_CHECKING:
    from ui.tui_bridge import TuiBridgeHost

AppStatus = Literal["ready", "thinking", "streaming", "error", "approval"]

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
PROMPT_SYMBOL = "> "
BOARD_SIDE_WIDTH = 40
_MOUSE_SGR_RE = re.compile(r"\x1b\[<[^>]*[Mm]|\[\<[^>]*[Mm]")


def _format_session_cost(cost: float) -> str:
    return tui_render.format_cost_usd(cost)


def _usage_header_text() -> str:
    return tui_render.format_usage_header(
        total_tokens=TOTAL_TOKENS,
        prompt_tokens=SESSION_PROMPT_TOKENS,
        completion_tokens=SESSION_COMPLETION_TOKENS,
        cost=TOTAL_COST,
    )


@dataclass
class AxonTUIState:
    model: str
    cwd: str
    cost: float = 0.0
    tokens: int = 0
    status: AppStatus = "ready"
    spinner_index: int = 0
    auto_scroll: bool = True

    def tick_spinner(self) -> None:
        self.spinner_index = (self.spinner_index + 1) % len(SPINNER)


AXON_STYLE = Style.from_dict(
    {
        "header": "bg:#0a0a0a #a1a1aa",
        "chat": "bg:#09090b #e4e4e7",
        "board": "bg:#0c0c0e #a1a1aa",
        "composer": "bg:#111111 #71717a",
        "composer-approval": "bg:#3b2f00 bold #fde68a",
        "input-area": "bg:#111111 #e4e4e7",
        "prompt": "bold #67e8f9",
        "completion-menu": "bg:#18181b #a1a1aa",
        "completion-menu.border": "#27272a",
        "completion-menu.completion": "bg:#18181b #a1a1aa",
        "completion-menu.completion.current": "bg:#27272a bold #67e8f9",
        "completion-menu.meta.completion": "bg:#18181b #52525b italic",
        "completion-menu.meta.completion.current": "bg:#27272a #71717a italic",
        "scrollbar.background": "bg:#18181b",
        "scrollbar.button": "bg:#3f3f46",
        "scrollbar.arrow": "bg:#18181b bold #71717a",
    }
)


class AxonTUI:
    """Claude/Cursor-style TUI: live stream, task board, steer while busy."""

    def __init__(self, llm: LLMManager, *, bridge_host: TuiBridgeHost | None = None) -> None:
        self.llm = llm
        self._bridge_host = bridge_host
        self.state = AxonTUIState(
            model=llm.model,
            cwd=str(Path.cwd()),
        )
        self._thinking = False
        self._spinner_task: asyncio.Task | None = None
        self._stream_buffer: list[str] = []
        self._thinking_buffer: list[str] = []
        self._plugins = discover_plugins(Path.cwd())
        self._board = TaskBoardState()
        self._agent_busy = False
        self._agent_task: asyncio.Task | None = None
        self._live_active = False
        self._transcript_prefix = ""
        self._transcript_canonical = ""
        self._board_open = False
        self._timeline_open = False
        self._show_thinking = True
        self._approval_waiter: asyncio.Future[ApprovalDecision] | None = None
        self._approval_summary = ""
        self._approval_preview = ""
        self._approval_preview_expanded = False
        self._approval_transcript_prefix = ""

        self._transcript_buffer = Buffer(read_only=True)
        self._chat_window = Window(
            BufferControl(self._transcript_buffer, focusable=False),
            wrap_lines=True,
            style="class:chat",
        )
        self._chat_pane = ScrollablePane(
            self._chat_window,
            width=D(weight=1),
            height=D(weight=1),
            keep_cursor_visible=False,
            keep_focused_window_visible=False,
            show_scrollbar=True,
            display_arrows=True,
        )

        self._board_window = Window(
            FormattedTextControl(self._board_fragments, focusable=False),
            width=D.exact(0),
            style="class:board",
            wrap_lines=True,
        )

        self._main_row = VSplit(
            [
                self._chat_pane,
                self._board_window,
            ],
            height=D(weight=1),
        )

        self.input_buffer = Buffer(
            completer=build_axon_completer(),
            history=FileHistory(os.path.expanduser("~/.axon_history")),
            complete_while_typing=True,
            multiline=True,
            accept_handler=self._on_accept,
        )

        self._input_window = Window(
            BufferControl(
                self.input_buffer,
                input_processors=[BeforeInput(PROMPT_SYMBOL, style="class:prompt")],
            ),
            height=D(min=1, max=3),
            style="class:input-area",
            wrap_lines=True,
        )

        self._root = HSplit(
            [
                Window(
                    FormattedTextControl(self._header_fragments, focusable=False),
                    height=D.exact(1),
                    style="class:header",
                ),
                self._main_row,
                Window(
                    FormattedTextControl(self._composer_fragments, focusable=False),
                    height=D.exact(1),
                    style="class:composer",
                ),
                self._input_window,
                CompletionsMenu(max_height=6, scroll_offset=1),
            ]
        )

        self._layout = Layout(self._root, focused_element=self._input_window)
        self.app = Application(
            layout=self._layout,
            key_bindings=self._build_keybindings(),
            style=AXON_STYLE,
            full_screen=True,
            mouse_support=False,
            refresh_interval=0.08,
        )

        self.llm.set_approval_callback(self._request_approval)
        self.llm.set_tool_callback(self._on_tool_start)
        set_tool_result_callback(self._on_tool_done)
        set_plan_render_callback(self._on_plan_board_update)
        set_multitask_runner(self._multitask_for_tool)
        register_usage_listener(self._on_usage_counters_changed)

    def _on_usage_counters_changed(self) -> None:
        self.state.cost = TOTAL_COST
        self.state.tokens = TOTAL_TOKENS
        if self._bridge_host:
            self._bridge_host.sync_stats_now()
        try:
            get_app().invalidate()
        except Exception:
            pass

    def _append_turn_usage(self, result_usage) -> None:
        w = self._render_width()
        turn_prompt = turn_completion = turn_total = 0
        if result_usage is not None:
            turn_prompt = result_usage.prompt_tokens
            turn_completion = result_usage.completion_tokens
            turn_total = result_usage.total_tokens
        self._append_block(
            tui_render.render_turn_usage(
                w,
                turn_prompt=turn_prompt,
                turn_completion=turn_completion,
                turn_total=turn_total,
                session_total=TOTAL_TOKENS,
                session_prompt=SESSION_PROMPT_TOKENS,
                session_completion=SESSION_COMPLETION_TOKENS,
                session_cost=TOTAL_COST,
            )
        )

    def _width(self) -> int:
        try:
            return get_app().output.get_size().columns
        except Exception:
            return 100

    def _render_width(self) -> int:
        """Chat column width (narrows when F2/F4 side panel is open)."""
        return self._chat_width()

    @staticmethod
    def _strip_mouse_garbage(text: str) -> str:
        return _MOUSE_SGR_RE.sub("", text).strip()

    def _side_panel_open(self) -> bool:
        if self._timeline_open:
            return True
        return self._board_open and self._board.visible

    def _board_fragments(self):
        if not self._side_panel_open():
            return [("class:board", " ")]

        w = min(BOARD_SIDE_WIDTH - 2, self._width() - 4)
        if self._timeline_open:
            from ui.session_timeline import session_timeline

            text = tui_render.render_session_timeline(
                files=sorted(session_timeline.files_touched),
                skills=sorted(session_timeline.skills_used),
                events=[
                    (e.kind, e.label, e.agent)
                    for e in session_timeline.events[-12:]
                ],
                cost_delta=session_timeline.session_cost_delta(TOTAL_COST),
                width=max(w, 24),
            )
            return [("class:board", text or " ")]

        rows = [
            (item.key, item.label, item.status, item.detail)
            for item in self._board.items
        ]
        text = tui_render.render_task_board(
            self._board.title or "Tasks",
            rows,
            max(w, 24),
        )
        return [("class:board", text or " ")]

    def _sync_board_layout(self) -> None:
        if self._side_panel_open():
            self._board_window.width = D.exact(BOARD_SIDE_WIDTH)
        else:
            self._board_window.width = D.exact(0)

    def _task_panel_hint(self) -> str:
        if self._timeline_open:
            return "F4 hide session"
        if task_manager.tasks:
            done = sum(1 for t in task_manager.tasks if t.status == "done")
            total = len(task_manager.tasks)
            remaining = total - done
            if self._board_open:
                return "F2 hide tasks"
            if remaining:
                return f"F2 tasks ({remaining}/{total})"
            return "F2 tasks"
        if self._board.visible:
            if self._board_open:
                return "F2 hide tasks"
            return "F2 tasks"
        return ""

    def _toggle_timeline_panel(self) -> None:
        self._timeline_open = not self._timeline_open
        if self._timeline_open:
            self._board_open = False
        self._sync_board_layout()
        get_app().invalidate()

    def _toggle_task_board(self) -> None:
        if not self._board.visible and not task_manager.tasks:
            w = self._width()
            self._append_block(
                tui_render.render_system("No active plan. Use /plan <goal> first.", w)
            )
            get_app().invalidate()
            return
        self._board_open = not self._board_open
        if self._board_open:
            self._timeline_open = False
        self._sync_board_layout()
        get_app().invalidate()

    def _finish_plan_if_done(self) -> bool:
        if not task_manager.tasks:
            return False
        if not task_manager.all_done():
            return False
        self._board.clear()
        self._board_open = False
        task_manager.clear()
        self._sync_board_layout()
        if self._bridge_host:
            self._bridge_host.broadcast_plan_now([], goal="")
        return True

    def _update_board(
        self,
        title: str,
        items: list[TaskBoardItem],
        *,
        auto_open: bool = False,
    ) -> None:
        active = [item for item in items if item.status != "done"]
        if not active:
            self._board.clear()
            self._board_open = False
            self._sync_board_layout()
            get_app().invalidate()
            return
        self._board.set_items(title, active)
        if auto_open:
            self._board_open = True
        self._sync_board_layout()
        get_app().invalidate()

    def _board_from_plan(self) -> None:
        if self._finish_plan_if_done():
            return
        if not task_manager.tasks:
            self._board.clear()
            self._sync_board_layout()
            return
        status_map = {
            "pending": "pending",
            "in-progress": "running",
            "done": "done",
        }
        active_tasks = [t for t in task_manager.tasks if t.status != "done"]
        if not active_tasks:
            self._finish_plan_if_done()
            return
        done = sum(1 for t in task_manager.tasks if t.status == "done")
        total = len(task_manager.tasks)
        items = [
            TaskBoardItem(
                str(t.id),
                t.name,
                status_map.get(t.status, "pending"),  # type: ignore[arg-type]
            )
            for t in active_tasks
        ]
        title = task_manager.goal or "Plan"
        if done:
            title = f"{title} ({done}/{total})"
        self._update_board(title, items)

    def _board_from_subtasks(self, goal: str, subtasks: list[SubTask]) -> None:
        active = [s for s in subtasks if s.status != "done"]
        if not active:
            self._board.clear()
            self._board_open = False
            self._sync_board_layout()
            return
        items = [
            TaskBoardItem(str(s.id), s.title, s.status, detail=s.agent)
            for s in active
        ]
        done = sum(1 for s in subtasks if s.status == "done")
        title = goal[:60] or "Multitask"
        if done:
            title = f"{title} ({done}/{len(subtasks)})"
        self._update_board(title, items)

    async def _on_plan_board_update(self) -> None:
        self._board_from_plan()
        if self._bridge_host and task_manager.tasks:
            self._bridge_host.broadcast_plan_now(
                [
                    {"id": t.id, "name": t.name, "status": t.status}
                    for t in task_manager.tasks
                ],
                goal=task_manager.goal,
            )
        get_app().invalidate()

    def _chat_width(self) -> int:
        w = self._width()
        if self._side_panel_open():
            w -= BOARD_SIDE_WIDTH
        return max(w - 2, 24)

    def _count_wrapped_lines(self, text: str, width: int) -> int:
        if not text:
            return 1
        total = 0
        for line in text.split("\n"):
            length = len(line)
            total += max(1, (length + width - 1) // width) if length else 1
        return total

    def _chat_visible_rows(self) -> int:
        try:
            rows = get_app().output.get_size().rows
        except Exception:
            rows = 24
        # header + composer + input (+ completion margin)
        return max(6, rows - 6)

    def _sync_chat_scroll(self) -> None:
        width = self._chat_width()
        lines = self._count_wrapped_lines(self._transcript_buffer.text, width)
        visible = self._chat_visible_rows()
        max_scroll = max(0, lines - visible)
        if self.state.auto_scroll:
            self._chat_pane.vertical_scroll = max_scroll
        else:
            self._chat_pane.vertical_scroll = min(
                self._chat_pane.vertical_scroll, max_scroll
            )

    def _paint_transcript(self, text: str) -> None:
        """Update scroll pane only (canonical history unchanged)."""
        self._transcript_buffer.set_document(
            Document(text, len(text)),
            bypass_readonly=True,
        )
        self._sync_chat_scroll()

    def _set_transcript_text(self, text: str) -> None:
        """Replace canonical transcript and repaint."""
        self._transcript_canonical = text
        self._paint_transcript(text)

    def _redraw_transcript(self) -> None:
        """Rebuild visible transcript after terminal resize."""
        if self._approval_pending() and self._approval_transcript_prefix:
            self._refresh_approval_block()
        elif self._live_active:
            self._refresh_live_response()
        else:
            self._paint_transcript(self._transcript_canonical)

    def _scroll_transcript_to_end(self) -> None:
        self._sync_chat_scroll()

    def _scroll_transcript_lines(self, delta: int) -> None:
        """Scroll chat history (PgUp/PgDn). Disables auto-scroll until bottom."""
        visible = self._chat_visible_rows()
        width = self._chat_width()
        core = self._transcript_canonical
        lines = self._count_wrapped_lines(core, width)
        max_scroll = max(0, lines - visible)
        if delta < 0:
            self._chat_pane.vertical_scroll = max(
                0, self._chat_pane.vertical_scroll + delta
            )
            self.state.auto_scroll = False
        else:
            self._chat_pane.vertical_scroll = min(
                max_scroll, self._chat_pane.vertical_scroll + delta
            )
            if self._chat_pane.vertical_scroll >= max_scroll:
                self.state.auto_scroll = True
        get_app().invalidate()

    def _append_block(self, block: str) -> None:
        block = block.strip()
        if not block:
            return
        if self._live_active:
            base = self._transcript_prefix.rstrip()
            self._transcript_prefix = f"{base}\n\n{block}\n\n" if base else f"{block}\n\n"
            self._transcript_canonical = self._transcript_prefix.rstrip()
            self._stream_buffer.clear()
            self._thinking_buffer.clear()
            self._paint_transcript(self._transcript_canonical)
        else:
            current = self._transcript_canonical
            self._set_transcript_text(f"{current}\n\n{block}" if current else block)
        self._scroll_transcript_to_end()

    def _sync_live_prefix(self) -> None:
        """No-op — prefix is extended incrementally in _append_block."""

    def _commit_assistant_turn(
        self,
        *,
        body: str,
        thinking: str,
        width: int,
        tool_steps: int,
    ) -> None:
        """Finalize assistant output without wiping tool/approval blocks."""
        self._end_live_response()
        block = tui_render.render_assistant_live(
            body,
            width,
            thinking=thinking,
        )
        base = self._transcript_prefix.rstrip()
        if block.strip():
            final = f"{base}\n\n{block}" if base else block
            self._set_transcript_text(final)
        elif tool_steps > 0:
            self._set_transcript_text(base)
            if body:
                self._append_block(tui_render.render_assistant_message(body, width))
        elif base:
            self._set_transcript_text(base)
        self._scroll_transcript_to_end()

    def _begin_live_response(self) -> None:
        self._live_active = True
        self._stream_buffer.clear()
        self._thinking_buffer.clear()
        self._transcript_prefix = self._transcript_canonical
        if self._transcript_prefix:
            self._transcript_prefix += "\n\n"

    def _refresh_live_response(self) -> None:
        if not self._live_active:
            return
        from skills.text_tool_calls import strip_text_tool_calls

        w = self._render_width()
        body = strip_text_tool_calls("".join(self._stream_buffer))
        thinking = "".join(self._thinking_buffer)
        if not self._show_thinking:
            thinking = ""
        block = tui_render.render_assistant_live(body, w, thinking=thinking)
        if block.strip():
            self._paint_transcript(self._transcript_prefix + block)
        else:
            self._paint_transcript(self._transcript_prefix.rstrip())
        self._scroll_transcript_to_end()

    def _end_live_response(self) -> None:
        self._live_active = False

    def _build_keybindings(self) -> KeyBindings:
        kb = KeyBindings()
        input_focused = has_focus(self._input_window)
        send_enter = input_focused & ~has_completions
        agent_busy = Condition(lambda: self._agent_busy)
        approval_pending = Condition(lambda: self._approval_pending())

        def _send(event) -> None:
            event.current_buffer.validate_and_handle()

        def _newline(event) -> None:
            event.current_buffer.insert_text("\n")

        @kb.add("c-c")
        def _(event) -> None:
            if self._approval_pending():
                self._resolve_approval("deny")
                return
            if self._agent_busy:
                event.app.create_background_task(self._cancel_agent())
            else:
                event.app.exit()

        @kb.add("c-d")
        def _(event) -> None:
            event.app.exit()

        @kb.add("enter", filter=send_enter & ~agent_busy & ~approval_pending)
        @kb.add("escape", "enter", filter=input_focused & ~agent_busy & ~approval_pending)
        def _(event) -> None:
            _send(event)

        @kb.add("1", filter=approval_pending)
        def _(event) -> None:
            self._resolve_approval("once")

        @kb.add("2", filter=approval_pending)
        def _(event) -> None:
            self._resolve_approval("session")

        @kb.add("3", filter=approval_pending)
        def _(event) -> None:
            self._resolve_approval("deny")

        @kb.add("y", filter=approval_pending)
        @kb.add("Y", filter=approval_pending)
        def _(event) -> None:
            self._resolve_approval("once")

        @kb.add("n", filter=approval_pending)
        @kb.add("N", filter=approval_pending)
        def _(event) -> None:
            self._resolve_approval("deny")

        @kb.add("v", filter=approval_pending)
        @kb.add("V", filter=approval_pending)
        def _(event) -> None:
            self._toggle_approval_diff()

        @kb.add("enter", "up", filter=input_focused & agent_busy)
        def _(event) -> None:
            text = self._strip_mouse_garbage(event.current_buffer.text)
            event.current_buffer.reset()
            if text:
                event.app.create_background_task(self._steer_agent(text))

        @kb.add("c-j", filter=input_focused)
        def _(event) -> None:
            _newline(event)

        @kb.add("pageup")
        def _(event) -> None:
            self._scroll_transcript_lines(-12)

        @kb.add("pagedown")
        def _(event) -> None:
            self._scroll_transcript_lines(12)

        @kb.add("f2")
        def _(event) -> None:
            self._toggle_task_board()

        @kb.add("f3")
        def _(event) -> None:
            self._toggle_thinking_panel()

        @kb.add("f4")
        def _(event) -> None:
            self._toggle_timeline_panel()

        return kb

    async def _cancel_agent(self) -> None:
        self.llm.request_cancel()
        self.llm.set_stream_callbacks()
        if self._agent_task and not self._agent_task.done():
            self._agent_task.cancel()
        self._stop_spinner()
        self._end_live_response()
        self._stream_buffer.clear()
        self._thinking_buffer.clear()
        self._paint_transcript(self._transcript_canonical)
        self._agent_busy = False
        self.state.status = "ready"
        self._append_block(tui_render.render_system("Cancelled.", self._render_width()))
        get_app().invalidate()

    def _spawn_agent(self, coro) -> None:
        """Run one agent job; blocks overlap (plan/chat/tools)."""
        if self._agent_busy:
            self._append_block(
                tui_render.render_error(
                    "AXON занят — дождитесь ответа или нажмите Ctrl+C.",
                    self._render_width(),
                )
            )
            get_app().invalidate()
            return

        async def runner() -> None:
            self._agent_busy = True
            self._agent_task = asyncio.current_task()
            try:
                await coro
            finally:
                self._agent_busy = False
                self._agent_task = None

        get_app().create_background_task(runner())

    async def _steer_agent(self, text: str) -> None:
        """Enter+Up — interrupt and send a follow-up."""
        await self._cancel_agent()
        if text:
            self._spawn_agent(self._process_message(text))

    def _header_fragments(self):
        short = self.state.model.rsplit("/", 1)[-1]
        cwd = self.state.cwd
        if len(cwd) > 36:
            cwd = "..." + cwd[-33:]
        line = (
            f" AXON | {cwd} | {short} | "
            f"{_usage_header_text()}"
        )
        return [("class:header", line)]

    def _composer_fragments(self):
        if self._approval_pending():
            line = (
                " ! РАЗРЕШЕНИЕ | [1] один раз | [2] на сессию | [3] отмена"
                " — или Y / N"
            )
            if self._approval_preview.strip():
                line += " | V diff"
            return [("class:composer-approval", line)]

        if self.state.status == "thinking":
            status = f"{SPINNER[self.state.spinner_index]} thinking"
        elif self.state.status == "streaming":
            status = f"{SPINNER[self.state.spinner_index]} streaming"
        elif self.state.status == "approval":
            status = "ожидание разрешения — нажми 1 / 2 / 3"
        elif self.state.status == "error":
            status = "error"
        elif self._agent_busy:
            status = "working — Enter+Up to steer"
        else:
            status = "ready"
        line = f" {status} | Enter send | Enter+Up steer | Ctrl+J newline | /help"
        hint = self._task_panel_hint()
        if hint:
            line += f" | {hint}"
        think_hint = "F3 hide thinking" if self._show_thinking else "F3 show thinking"
        line += f" | {think_hint}"
        line += " | PgUp/PgDn scroll"
        if not self._timeline_open:
            line += " | F4 session"
        return [("class:composer", line)]

    def _approval_pending(self) -> bool:
        waiter = self._approval_waiter
        return waiter is not None and not waiter.done()

    def _resolve_approval(self, decision: ApprovalDecision) -> None:
        labels = {
            "once": "Разрешено один раз",
            "session": "Разрешено на сессию",
            "deny": "Отклонено",
        }
        w = self._render_width()
        self._append_block(
            tui_render.render_system(f"→ {labels.get(decision, decision)}", w)
        )
        waiter = self._approval_waiter
        if waiter is not None and not waiter.done():
            waiter.set_result(decision)
        if self._agent_busy and self.state.status == "approval":
            self.state.status = "thinking"
            self._start_spinner("thinking")
        get_app().invalidate()

    def _toggle_thinking_panel(self) -> None:
        self._show_thinking = not self._show_thinking
        if self._live_active:
            self._refresh_live_response()
        get_app().invalidate()

    def _toggle_approval_diff(self) -> None:
        if not self._approval_pending() or not self._approval_preview.strip():
            return
        self._approval_preview_expanded = not self._approval_preview_expanded
        self._refresh_approval_block()
        get_app().invalidate()

    def _refresh_approval_block(self) -> None:
        w = self._render_width()
        block = tui_render.render_approval_request(
            self._approval_summary,
            w,
            preview=self._approval_preview,
            preview_expanded=self._approval_preview_expanded,
        )
        self._paint_transcript(self._approval_transcript_prefix + block)
        self._scroll_transcript_to_end()

    async def _request_approval(self, tool_name: str, detail: str) -> ApprovalDecision:
        from openclaw_mode import is_openclaw_active
        from runtime_policy import load_runtime_policy
        from ui.code_diff import split_approval_message

        policy = load_runtime_policy()
        if is_openclaw_active() or policy.autonomy_enabled:
            return "once"

        self._end_live_response()
        self._stream_buffer.clear()
        self._thinking_buffer.clear()
        self._stop_spinner()
        self.state.status = "approval"
        self.input_buffer.reset()

        command_detail, preview = split_approval_message(detail)
        label = tool_display_label(tool_name)
        summary = f"{label}: {command_detail.strip() or '(no details)'}"
        self._approval_summary = summary
        self._approval_preview = preview
        self._approval_preview_expanded = False
        committed = self._transcript_canonical.rstrip()
        self._approval_transcript_prefix = f"{committed}\n\n" if committed else ""
        self._paint_transcript(committed)
        self._refresh_approval_block()

        loop = asyncio.get_running_loop()
        self._approval_waiter = loop.create_future()
        get_app().invalidate()

        try:
            return await self._approval_waiter
        finally:
            self._approval_waiter = None
            self._approval_summary = ""
            self._approval_preview = ""
            self._approval_preview_expanded = False
            self._approval_transcript_prefix = ""
            if self._agent_busy:
                self._live_active = True
                self._transcript_prefix = self._transcript_canonical
                if self._transcript_prefix:
                    self._transcript_prefix += "\n\n"
                self._refresh_live_response()
            if self.state.status == "approval":
                self.state.status = "thinking" if self._agent_busy else "ready"
            get_app().invalidate()

    async def _on_tool_start(self, tool_name: str, detail: str) -> None:
        w = self._width()
        label = tool_display_label(tool_name)
        self._append_block(tui_render.render_agent_activity(label, detail, w))
        if self._bridge_host:
            self._bridge_host.broadcast_tool_now(tool_name, "start", detail)
        get_app().invalidate()

    async def _on_tool_done(self, tool_name: str, detail: str, output: str) -> None:
        w = self._width()
        if tool_name == "take_screenshot":
            self._append_block(tui_render.render_system(output, w))
        else:
            label = tool_display_label(tool_name)
            self._append_block(
                tui_render.render_tool_event(label, detail, w, phase="done")
            )
        if self._bridge_host:
            self._bridge_host.broadcast_tool_now(tool_name, "done", detail)
        if self._timeline_open:
            get_app().invalidate()
        get_app().invalidate()

    async def _spinner_loop(self) -> None:
        while self._thinking:
            self.state.tick_spinner()
            get_app().invalidate()
            await asyncio.sleep(0.08)

    def _start_spinner(self, status: AppStatus = "thinking") -> None:
        self._thinking = True
        self.state.status = status
        get_app().invalidate()
        self._spinner_task = get_app().create_background_task(self._spinner_loop())

    def _stop_spinner(self) -> None:
        self._thinking = False
        if self._spinner_task is not None:
            self._spinner_task.cancel()
            self._spinner_task = None

    async def _handle_command(self, text: str) -> None:
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        w = self._width()

        if cmd in {"/exit", "/quit"}:
            get_app().exit()
            return

        if cmd == "/help":
            merged = dict(AXON_COMMANDS)
            merged.update(list_plugin_commands(Path.cwd()))
            lines = "\n".join(f"  {c:<14} {d}" for c, d in merged.items())
            self._append_block(tui_render.render_system(f"Commands:\n{lines}", w))
            return

        if cmd == "/config":
            from openclaw_mode import is_openclaw_active, is_process_elevated

            policy = load_runtime_policy()
            claw = "ON" if is_openclaw_active() else (
                "armed" if policy.openclaw_enabled else "off"
            )
            body = (
                f"Policy: {POLICY_PATH}\n"
                f"parallel={policy.allow_parallel_agents}  "
                f"auto_save={policy.auto_save_session}\n"
                f"openclaw={claw}  elevated={'yes' if is_process_elevated() else 'no'}\n"
                f"Use /claw on|off or REPL /config set for other keys."
            )
            self._append_block(tui_render.render_system(body, w))
            return

        if cmd == "/provider" or text.lower().startswith("/provider"):
            await self._run_provider_command(text)
            return

        if cmd in {"/claw", "/openclaw"}:
            from openclaw_mode import (
                disable_openclaw,
                enable_openclaw,
                openclaw_status_lines,
            )

            verb = args.strip().lower() or "status"
            if verb == "on":
                ok, msg = enable_openclaw()
                kind = "system" if ok else "error"
                self._append_block(
                    tui_render.render_system(msg, w)
                    if kind == "system"
                    else tui_render.render_error(msg, w)
                )
            elif verb == "off":
                self._append_block(
                    tui_render.render_system(disable_openclaw(), w)
                )
            else:
                body = "\n".join(openclaw_status_lines())
                self._append_block(tui_render.render_system(body, w))
            return

        if cmd == "/plan":
            goal = args.strip()
            if not goal:
                self._append_block(tui_render.render_error("Usage: /plan <goal>", w))
                return
            await self._run_plan(goal)
            return

        if cmd == "/execute":
            await self._run_execute()
            return

        if cmd == "/multitask":
            goal_line = args.strip() if args.strip() else text.strip()
            if goal_line.lower().startswith("/multitask"):
                goal_line = goal_line[len("/multitask") :].strip()
            if not goal_line:
                self._append_block(
                    tui_render.render_error("Usage: /multitask <goal>", w)
                )
                return
            await self._run_multitask(goal_line)
            return

        if cmd == "/image":
            from ui.image_cmd import load_image_with_vision_check, parse_image_command

            image_path, prompt = parse_image_command(text)
            if not image_path:
                self._append_block(
                    tui_render.render_error(
                        "Usage: /image <path|@file> [prompt]", w
                    )
                )
                return
            error = load_image_with_vision_check(self.llm, image_path, prompt)
            if error:
                extra = ""
                if "text-only" in error.lower():
                    from ui.vision_models import vision_switch_hint

                    extra = f"\nTry: {vision_switch_hint(self.llm.model)}"
                self._append_block(tui_render.render_error(f"{error}{extra}", w))
            else:
                self._append_block(
                    tui_render.render_system(
                        f"Image loaded: {image_path}. Ask a question about it.",
                        w,
                    )
                )
            return

        if cmd == "/export-skill":
            from ui.skill_export import export_skill

            name = args.strip()
            if not name:
                self._append_block(
                    tui_render.render_error("Usage: /export-skill <name>", w)
                )
                return
            try:
                dest = export_skill(name, workspace=Path.cwd())
                self._append_block(
                    tui_render.render_system(f"Skill exported: {dest}", w)
                )
            except (OSError, ValueError) as exc:
                self._append_block(tui_render.render_error(str(exc), w))
            return

        if cmd == "/session":
            self._toggle_timeline_panel()
            state = "shown" if self._timeline_open else "hidden"
            self._append_block(
                tui_render.render_system(f"Session timeline {state} (F4).", w)
            )
            return

        if cmd.startswith("/"):
            cmd_name = cmd.lstrip("/")
            for plugin in self._plugins:
                if cmd_name in plugin.commands:
                    try:
                        out = str(plugin.run(cmd_name, *args.split()))
                        self._append_block(tui_render.render_system(out, w))
                    except Exception as exc:
                        self._append_block(tui_render.render_error(str(exc), w))
                    return

        if cmd == "/thinking":
            self._toggle_thinking_panel()
            state = "on" if self._show_thinking else "off"
            self._append_block(
                tui_render.render_system(f"Thinking trace: {state} (F3)", w)
            )
            return

        if cmd == "/tasks":
            had_tasks = bool(task_manager.tasks) or self._board.visible
            self._toggle_task_board()
            if not had_tasks:
                self._append_block(
                    tui_render.render_system("No active plan tasks.", w)
                )
            elif self._board_open:
                self._append_block(tui_render.render_system("Task panel shown (F2 to hide).", w))
            else:
                self._append_block(tui_render.render_system("Task panel hidden (F2 to show).", w))
            return

        if cmd == "/clear":
            from skills.tools import clear_session_approvals
            from ui.session_timeline import session_timeline

            self._set_transcript_text("")
            self._board.clear()
            self._board_open = False
            self._timeline_open = False
            task_manager.clear()
            session_timeline.clear()
            reset_session_counters()
            session_timeline.set_cost_anchor(TOTAL_COST)
            clear_session_approvals()
            self._sync_board_layout()
            self.llm.messages = [
                {"role": "system", "content": self.llm.messages[0]["content"]}
            ]
            self.state.cost = 0.0
            self.state.tokens = 0
            self.state.status = "ready"
            return

        if cmd == "/model":
            if args.strip():
                self.llm.set_model(args.strip())
                self.state.model = self.llm.model
                if self._bridge_host:
                    self._bridge_host.broadcast_model_now(self.state.model)
            self._append_block(
                tui_render.render_system(f"Model: {self.state.model}", w)
            )
            get_app().invalidate()
            return

        if cmd in {"/cost", "/usage"}:
            self._append_block(
                tui_render.render_session_usage_detail(
                    w,
                    total_tokens=TOTAL_TOKENS,
                    prompt_tokens=SESSION_PROMPT_TOKENS,
                    completion_tokens=SESSION_COMPLETION_TOKENS,
                    cost=TOTAL_COST,
                    model=self.state.model,
                )
            )
            return

        if cmd == "/gen-skill":
            description = parse_gen_skill_description(text) or args
            if not description.strip():
                self._append_block(
                    tui_render.render_error('Usage: /gen-skill "description"', w)
                )
                return
            await self._run_gen_skill(description)
            return

        if cmd == "/create-skill":
            await self._run_create_skill()
            return

        self._append_block(
            tui_render.render_error(f"Unknown command {cmd}. /help", w)
        )
        self.state.status = "error"

    async def _multitask_for_tool(self, goal: str) -> str:
        result = await self._run_multitask(goal, from_tool=True)
        if result.error and not result.synthesis:
            return result.error or "multitask failed"
        return result.synthesis or "(empty)"

    async def _run_multitask(self, goal: str, *, from_tool: bool = False):
        from orchestrator import OrchestratorResult

        app = get_app()
        w = self._width()
        policy = load_runtime_policy()
        orch = Orchestrator(
            llm=self.llm,
            workspace=Path.cwd(),
            allow_parallel=policy.allow_parallel_agents,
        )

        phase_items = [
            TaskBoardItem("1", "Decompose goal", "running"),
            TaskBoardItem("2", "Run subtasks", "pending"),
            TaskBoardItem("3", "Synthesize", "pending"),
        ]
        self._update_board(goal[:50], phase_items)

        subtasks_holder: list[SubTask] = []

        async def on_multitask_event(
            phase: str,
            event_goal: str,
            subtasks: list,
            synthesis: str = "",
        ) -> None:
            nonlocal subtasks_holder
            if subtasks:
                subtasks_holder = list(subtasks)
                self._board_from_subtasks(event_goal, subtasks_holder)
            if phase == "decompose_done" and subtasks:
                self._board_from_subtasks(event_goal, subtasks)
            if phase == "synthesis_done":
                items = list(self._board.items)
                for item in items:
                    if "Synthesize" in item.label:
                        item.status = "done"
                self._update_board(event_goal[:50], items)
            if self._bridge_host:
                payload = [
                    {
                        "id": s.id,
                        "title": s.title,
                        "agent": s.agent,
                        "status": s.status,
                    }
                    for s in (subtasks or subtasks_holder)
                ]
                self._bridge_host.broadcast_multitask_now(
                    phase, event_goal, payload, synthesis=synthesis
                )
            from ui.session_timeline import session_timeline

            for s in subtasks or subtasks_holder:
                if s.status == "running":
                    session_timeline.record_agent(s.agent, s.title)

        async def on_progress(message: str) -> None:
            clean = (
                message.replace("[bold]", "")
                .replace("[/bold]", "")
                .replace("[cyan]", "")
                .replace("[/cyan]", "")
                .replace("[green]", "")
                .replace("[/green]", "")
                .replace("[red]", "")
                .replace("[/red]", "")
                .replace("[dim]", "")
                .replace("[/dim]", "")
            )
            if "Decomposing" in clean:
                self._update_board(
                    goal[:50],
                    [
                        TaskBoardItem("1", "Decompose goal", "running"),
                        TaskBoardItem("2", "Run subtasks", "pending"),
                        TaskBoardItem("3", "Synthesize", "pending"),
                    ],
                )
            elif "Synthesizing" in clean:
                items = [
                    TaskBoardItem(str(s.id), s.title, s.status) for s in subtasks_holder
                ]
                items.append(TaskBoardItem("z", "Synthesize results", "running"))
                self._update_board(goal[:50], items)
            elif clean.strip().startswith("▶") or clean.strip().startswith(">"):
                line = clean.strip()
                self._append_block(tui_render.render_system(line, w))
                if "[" in line and "]" in line:
                    from ui.session_timeline import session_timeline

                    try:
                        agent = line.split("[", 1)[1].split("]", 1)[0]
                        title = line.split("]", 1)[-1].strip()
                        session_timeline.record_agent(agent, title)
                    except IndexError:
                        pass
            app.invalidate()

        self._start_spinner("thinking")
        try:
            result = await orch.run(
                goal,
                on_progress=on_progress,
                on_multitask_event=on_multitask_event,
            )
        finally:
            self._stop_spinner()

        self.state.cost = TOTAL_COST
        self.state.tokens = TOTAL_TOKENS

        if subtasks_holder:
            self._board_from_subtasks(goal, subtasks_holder)
            for item in self._board.items:
                if item.status == "running":
                    item.status = "done"
            self._update_board(self._board.title, self._board.items)

        if not from_tool:
            if result.error and not result.synthesis:
                self._append_block(tui_render.render_error(result.error, w))
                self.state.status = "error"
            else:
                self._append_block(
                    tui_render.render_assistant_message(result.synthesis or "", w)
                )
                self.state.status = "ready"
            app.invalidate()
        return result

    async def _run_plan(self, goal: str) -> None:
        app = get_app()
        w = self._width()
        from ui.session_timeline import session_timeline

        session_timeline.record_plan(goal)
        self._update_board(
            "Plan",
            [TaskBoardItem("1", "Building plan...", "running")],
        )
        self._start_spinner("thinking")
        try:
            task_manager.goal = goal
            result = await self.llm.send_plan_async(goal)
        finally:
            self._stop_spinner()

        self._board_from_plan()
        self.state.cost = TOTAL_COST
        self.state.tokens = TOTAL_TOKENS

        if result.ok and task_manager.has_plan():
            self._append_block(
                tui_render.render_assistant_message(
                    result.content or "Plan ready. Use /execute to run it.",
                    w,
                )
            )
            self.state.status = "ready"
        elif result.ok:
            task_manager.goal = ""
            self._append_block(
                tui_render.render_error(
                    "Plan mode finished but no tasks were created. Try /plan again.",
                    w,
                )
            )
            self.state.status = "error"
        else:
            self._append_block(tui_render.render_error(result.display_text, w))
            self.state.status = "error"
        app.invalidate()

    async def _run_execute(self) -> None:
        app = get_app()
        w = self._width()
        if not task_manager.has_plan():
            self._append_block(
                tui_render.render_error("No active plan. Use /plan first.", w)
            )
            return
        self._start_spinner("thinking")
        try:
            result = await self.llm.send_execute_async()
        finally:
            self._stop_spinner()
        self._board_from_plan()
        self.state.cost = TOTAL_COST
        self.state.tokens = TOTAL_TOKENS
        if result.ok:
            msg = result.content or "Done."
            if task_manager.has_plan() and not task_manager.all_done():
                done = sum(1 for t in task_manager.tasks if t.status == "done")
                total = len(task_manager.tasks)
                msg += f"\n\nПлан: {done}/{total} — снова /execute для следующего шага."
            self._append_block(tui_render.render_assistant_message(msg, w))
            self.state.status = "ready"
        else:
            self._append_block(tui_render.render_error(result.display_text, w))
            self.state.status = "error"
        app.invalidate()

    async def _run_provider_command(self, text: str) -> None:
        import re

        from ui.provider_cmd import handle_provider_command

        app = get_app()
        w = self._width()

        async def emit(message: object) -> None:
            plain = re.sub(r"\[/?[^\]]+\]", "", str(message)).strip()
            if not plain:
                return
            if plain.startswith("!"):
                self._append_block(tui_render.render_error(plain.lstrip("! "), w))
            elif "[✓]" in plain or plain.startswith("✓"):
                self._append_block(tui_render.render_system(plain, w))
            else:
                self._append_block(tui_render.render_system(plain, w))

        await handle_provider_command(text, emit=emit)
        app.invalidate()

    async def _run_gen_skill(self, description: str) -> None:
        app = get_app()
        w = self._width()
        self._append_block(tui_render.render_system("Generating skill with AI...", w))
        app.invalidate()

        self._start_spinner("thinking")
        try:
            result = await self.llm.generate_skill_file_async(description.strip())
        finally:
            self._stop_spinner()

        self.state.cost = TOTAL_COST
        self.state.tokens = TOTAL_TOKENS

        if not result.ok:
            self._append_block(tui_render.render_error(result.display_text, w))
            self.state.status = "error"
            app.invalidate()
            return

        try:
            _path, skill_name = save_generated_skill_file(
                result.content,
                workspace=Path.cwd(),
            )
        except (OSError, ValueError) as exc:
            self._append_block(tui_render.render_error(f"Failed to save skill — {exc}", w))
            self.state.status = "error"
            app.invalidate()
            return

        self.llm.reload_skills()
        self._append_block(
            tui_render.render_system(
                f'Skill "{skill_name}" created and loaded. Use !{skill_name}.',
                w,
            )
        )
        self.state.status = "ready"
        app.invalidate()

    async def _run_create_skill(self) -> None:
        app = get_app()
        w = self._width()
        self._append_block(tui_render.render_system("Creating a new AXON skill...", w))
        app.invalidate()

        def _prompt_fields() -> tuple[str, str, str]:
            name = input("Skill Name (e.g., check-logs): ").strip()
            description = input("Description: ").strip()
            shell_cmd = input(
                "Auto-execute shell command (optional, press Enter to skip): "
            ).strip()
            return name, description, shell_cmd

        try:
            name, description, shell_cmd = await run_in_terminal(_prompt_fields)
        except Exception as exc:
            self._append_block(tui_render.render_error(f"Skill wizard cancelled — {exc}", w))
            self.state.status = "error"
            app.invalidate()
            return

        if not name:
            self._append_block(tui_render.render_error("Skill name is required.", w))
            self.state.status = "error"
            app.invalidate()
            return
        if not description:
            self._append_block(tui_render.render_error("Description is required.", w))
            self.state.status = "error"
            app.invalidate()
            return

        try:
            path = create_skill_file(
                name,
                description,
                shell_cmd,
                workspace=Path.cwd(),
            )
        except OSError as exc:
            self._append_block(tui_render.render_error(f"Failed to create skill — {exc}", w))
            self.state.status = "error"
            app.invalidate()
            return

        self.llm.reload_skills()
        self._append_block(
            tui_render.render_system(
                f"Skill created: {path.parent.name}",
                w,
            )
        )
        self.state.status = "ready"
        app.invalidate()

    async def _process_message(self, text: str) -> None:
        app = get_app()
        w = self._width()

        try:
            if text.startswith("/"):
                await self._handle_command(text)
                app.invalidate()
                return

            intent = detect_intent(text, has_active_plan=task_manager.has_plan())
            if intent == "multitask":
                await self._run_multitask(text)
                return
            if intent == "plan":
                await self._run_plan(text)
                return
            if intent == "execute":
                await self._run_execute()
                return

            self.llm.clear_cancel()
            self._begin_live_response()

            async def on_start() -> None:
                self._start_spinner("streaming")

            async def on_token(token: str) -> None:
                self._stream_buffer.append(token)
                self._refresh_live_response()
                app.invalidate()

            async def on_thinking(token: str) -> None:
                self._thinking_buffer.append(token)
                self._refresh_live_response()
                app.invalidate()

            async def on_end() -> None:
                pass

            self.llm.set_stream_callbacks(
                on_token=on_token,
                on_thinking=on_thinking,
                on_start=on_start,
                on_end=on_end,
            )
            self._start_spinner("thinking")

            result = await self.llm.send_message_async(text)
            self._stop_spinner()
            self.llm.set_stream_callbacks()

            self.state.cost = TOTAL_COST
            self.state.tokens = TOTAL_TOKENS
            self.state.model = self.llm.model

            if result.ok:
                body = (result.content or "".join(self._stream_buffer)).strip()
                thinking_text = (
                    "".join(self._thinking_buffer) if self._show_thinking else ""
                )
                self._commit_assistant_turn(
                    body=body,
                    thinking=thinking_text,
                    width=w,
                    tool_steps=result.tool_steps or 0,
                )

                if self._bridge_host and body:
                    self._bridge_host.broadcast_chat_now(
                        role="assistant",
                        text=body,
                        source="terminal",
                    )

                explore = get_turn_explore_summary()
                if explore:
                    self._append_block(tui_render.render_explore_summary(explore, w))

                if body or (result.tool_steps or 0) > 0:
                    self._append_block(tui_render.render_turn_divider(w))
                    self._append_turn_usage(result.usage)
                else:
                    self._append_block(tui_render.render_system("(empty response)", w))
                self.state.status = "ready"
            elif "cancelled" in (result.error or "").lower():
                self._append_block(tui_render.render_system("Stopped.", w))
                self.state.status = "ready"
            else:
                self._end_live_response()
                self._append_block(tui_render.render_error(result.display_text, w))
                self.state.status = "error"

            if self._bridge_host:
                self._bridge_host.sync_stats_now()

            app.invalidate()
        except asyncio.CancelledError:
            self._stop_spinner()
            self.llm.set_stream_callbacks()
            self._end_live_response()
            self._stream_buffer.clear()
            self._thinking_buffer.clear()
            raise
        except Exception:
            self._stop_spinner()
            self.llm.set_stream_callbacks()
            self._end_live_response()
            self._append_block(
                tui_render.render_error(traceback.format_exc(limit=2), w)
            )
            self.state.status = "error"
            app.invalidate()

    def _on_accept(self, buff: Buffer) -> bool:
        text = self._strip_mouse_garbage(buff.text)
        if not text:
            return False

        self.state.auto_scroll = True

        if self._approval_pending():
            lowered = text.lower()
            mapping: dict[str, ApprovalDecision] = {
                "1": "once",
                "2": "session",
                "3": "deny",
                "y": "once",
                "yes": "once",
                "да": "once",
                "n": "deny",
                "no": "deny",
                "нет": "deny",
                "ні": "deny",
            }
            if lowered in mapping:
                buff.reset()
                self._resolve_approval(mapping[lowered])
                return False
            if lowered == "v" and self._approval_preview.strip():
                buff.reset()
                self._toggle_approval_diff()
                return False
            buff.reset()
            w = self._render_width()
            self._append_block(
                tui_render.render_error(
                    "Ожидается 1, 2, 3, Y или N для разрешения.", w
                )
            )
            get_app().invalidate()
            return False

        w = self._render_width()
        if not text.startswith("/"):
            self._append_block(tui_render.render_user_message(text, w))
            if self._bridge_host:
                self._bridge_host.broadcast_chat_now(
                    role="user",
                    text=text,
                    source="terminal",
                )

        buff.reset()
        get_app().invalidate()
        self._spawn_agent(self._process_message(text))
        return False

    def run(self) -> None:
        from ui.session_timeline import session_timeline

        session_timeline.set_cost_anchor(TOTAL_COST)
        w = 100
        self._set_transcript_text(
            tui_render.render_welcome(
                w, model=self.state.model, cwd=self.state.cwd
            )
        )
        self._scroll_transcript_to_end()

        if self._bridge_host:
            self._bridge_host.attach(self)
            self._bridge_host.start()

        async def main() -> None:
            if self._bridge_host:
                self._bridge_host.set_tui_loop(asyncio.get_running_loop())
                asyncio.create_task(self._bridge_host.drain_web_inbox())
                self._bridge_host.sync_stats_now()
                self._bridge_host.broadcast_model_now(self.state.model)

            async def _on_terminal_resize() -> None:
                last_rows = 0
                last_cols = 0
                while True:
                    await asyncio.sleep(0.15)
                    try:
                        size = get_app().output.get_size()
                        rows, cols = size.rows, size.columns
                    except Exception:
                        continue
                    if rows != last_rows or cols != last_cols:
                        last_rows, last_cols = rows, cols
                        self._redraw_transcript()
                        get_app().invalidate()

            asyncio.create_task(_on_terminal_resize())
            await self.app.run_async()

        asyncio.run(main())


def run_tui() -> None:
    """Entry point for `axon tui`."""
    from dotenv import load_dotenv

    from ui.tui_bridge import TuiBridgeHost

    os.environ.setdefault("PROMPT_TOOLKIT_BELL", "0")
    load_dotenv()
    llm = LLMManager()
    bridge_host = TuiBridgeHost()
    AxonTUI(llm, bridge_host=bridge_host).run()
