"""Desktop TUI for AXON."""

from __future__ import annotations

import asyncio
import os
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from prompt_toolkit.application import Application, get_app, run_in_terminal
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition, has_completions, has_focus
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Dimension as D
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea

from llm_client import LLMManager, TOTAL_COST, TOTAL_TOKENS
from orchestrator import Orchestrator, SubTask
from plugins.loader import discover_plugins, list_plugin_commands
from runtime_policy import POLICY_PATH, load_runtime_policy
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

AppStatus = Literal["ready", "thinking", "streaming", "error"]

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
PROMPT_SYMBOL = "> "


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
        "input-area": "bg:#111111 #e4e4e7",
        "prompt": "bold #67e8f9",
        "completion-menu": "bg:#18181b #a1a1aa",
        "completion-menu.border": "#27272a",
        "completion-menu.completion": "bg:#18181b #a1a1aa",
        "completion-menu.completion.current": "bg:#27272a bold #67e8f9",
        "completion-menu.meta.completion": "bg:#18181b #52525b italic",
        "completion-menu.meta.completion.current": "bg:#27272a #71717a italic",
    }
)


class AxonTUI:
    """Claude/Cursor-style TUI: live stream, task board, steer while busy."""

    def __init__(self, llm: LLMManager) -> None:
        self.llm = llm
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
        self._board_height = 1

        self._transcript_area = TextArea(
            text="",
            read_only=True,
            focusable=False,
            wrap_lines=True,
            scrollbar=True,
            style="class:chat",
        )

        self._board_window = Window(
            FormattedTextControl(self._board_fragments, focusable=False),
            height=D.exact(1),
            style="class:board",
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
                self._transcript_area,
                self._board_window,
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
            mouse_support=True,
            refresh_interval=0.08,
        )

        self.llm.set_approval_callback(self._request_approval)
        self.llm.set_tool_callback(self._on_tool_start)
        set_tool_result_callback(self._on_tool_done)
        set_plan_render_callback(self._on_plan_board_update)
        set_multitask_runner(self._multitask_for_tool)

    def _width(self) -> int:
        try:
            return get_app().output.get_size().columns
        except Exception:
            return 100

    def _board_fragments(self):
        if not self._board.visible:
            return [("class:board", " ")]
        rows = [
            (item.key, item.label, item.status)
            for item in self._board.items
        ]
        text = tui_render.render_task_board(
            self._board.title or "Tasks",
            rows,
            self._width(),
        )
        return [("class:board", text or " ")]

    def _sync_board_height(self) -> None:
        if not self._board.visible:
            self._board_height = 1
        else:
            self._board_height = min(10, max(3, len(self._board.items) + 2))
        self._board_window.height = D.exact(self._board_height)

    def _update_board(
        self,
        title: str,
        items: list[TaskBoardItem],
    ) -> None:
        self._board.set_items(title, items)
        self._sync_board_height()
        get_app().invalidate()

    def _board_from_plan(self) -> None:
        if not task_manager.tasks:
            self._board.clear()
            self._sync_board_height()
            return
        status_map = {
            "pending": "pending",
            "in-progress": "running",
            "done": "done",
        }
        items = [
            TaskBoardItem(
                str(t.id),
                t.name,
                status_map.get(t.status, "pending"),  # type: ignore[arg-type]
            )
            for t in task_manager.tasks
        ]
        self._update_board(task_manager.goal or "Plan", items)

    def _board_from_subtasks(self, goal: str, subtasks: list[SubTask]) -> None:
        items = [
            TaskBoardItem(str(s.id), s.title, s.status, detail=s.agent)
            for s in subtasks
        ]
        self._update_board(goal[:60] or "Multitask", items)

    async def _on_plan_board_update(self) -> None:
        self._board_from_plan()
        get_app().invalidate()

    def _scroll_transcript_to_end(self) -> None:
        text = self._transcript_area.text
        self._transcript_area.buffer.set_document(
            Document(text, len(text)),
            bypass_readonly=True,
        )

    def _append_block(self, block: str) -> None:
        block = block.strip()
        if not block:
            return
        current = self._transcript_area.text
        self._transcript_area.text = f"{current}\n\n{block}" if current else block
        self._scroll_transcript_to_end()

    def _begin_live_response(self) -> None:
        self._live_active = True
        self._stream_buffer.clear()
        self._thinking_buffer.clear()
        self._transcript_prefix = self._transcript_area.text
        if self._transcript_prefix:
            self._transcript_prefix += "\n\n"

    def _refresh_live_response(self) -> None:
        if not self._live_active:
            return
        w = self._width()
        body = "".join(self._stream_buffer)
        thinking = "".join(self._thinking_buffer)
        block = tui_render.render_assistant_live(body, w, thinking=thinking)
        self._transcript_area.text = self._transcript_prefix + block
        self._scroll_transcript_to_end()

    def _end_live_response(self) -> None:
        self._live_active = False

    def _build_keybindings(self) -> KeyBindings:
        kb = KeyBindings()
        input_focused = has_focus(self._input_window)
        send_enter = input_focused & ~has_completions
        agent_busy = Condition(lambda: self._agent_busy)

        def _send(event) -> None:
            event.current_buffer.validate_and_handle()

        def _newline(event) -> None:
            event.current_buffer.insert_text("\n")

        @kb.add("c-c")
        def _(event) -> None:
            if self._agent_busy:
                event.app.create_background_task(self._cancel_agent())
            else:
                event.app.exit()

        @kb.add("c-d")
        def _(event) -> None:
            event.app.exit()

        @kb.add("enter", filter=send_enter & ~agent_busy)
        @kb.add("escape", "enter", filter=input_focused & ~agent_busy)
        def _(event) -> None:
            _send(event)

        @kb.add("enter", "up", filter=input_focused & agent_busy)
        def _(event) -> None:
            text = event.current_buffer.text.strip()
            event.current_buffer.reset()
            event.app.create_background_task(self._steer_agent(text))

        @kb.add("c-j", filter=input_focused)
        def _(event) -> None:
            _newline(event)

        return kb

    async def _cancel_agent(self) -> None:
        self.llm.request_cancel()
        if self._agent_task and not self._agent_task.done():
            self._agent_task.cancel()
        self._stop_spinner()
        self._end_live_response()
        self._agent_busy = False
        self.state.status = "ready"
        self._append_block(tui_render.render_system("Cancelled.", self._width()))
        get_app().invalidate()

    async def _steer_agent(self, text: str) -> None:
        """Enter+Up — interrupt and send a follow-up."""
        await self._cancel_agent()
        if text:
            await self._process_message(text)

    def _header_fragments(self):
        short = self.state.model.rsplit("/", 1)[-1]
        cwd = self.state.cwd
        if len(cwd) > 36:
            cwd = "..." + cwd[-33:]
        line = (
            f" AXON | {cwd} | {short} | "
            f"${self.state.cost:.4f} | {self.state.tokens} tok"
        )
        return [("class:header", line)]

    def _composer_fragments(self):
        if self.state.status == "thinking":
            status = f"{SPINNER[self.state.spinner_index]} thinking"
        elif self.state.status == "streaming":
            status = f"{SPINNER[self.state.spinner_index]} streaming"
        elif self.state.status == "error":
            status = "error"
        elif self._agent_busy:
            status = "working — Enter+Up to steer"
        else:
            status = "ready"
        line = f" {status} | Enter send | Enter+Up steer | Ctrl+J newline | /help"
        return [("class:composer", line)]

    async def _request_approval(self, tool_name: str, detail: str) -> ApprovalDecision:
        from openclaw_mode import is_openclaw_active
        from runtime_policy import load_runtime_policy
        from ui.code_diff import split_approval_message

        policy = load_runtime_policy()
        if is_openclaw_active() or policy.autonomy_enabled:
            return "once"

        command_detail, preview = split_approval_message(detail)
        label = tool_display_label(tool_name)
        summary = f"{label}: {command_detail.strip() or '(no details)'}"
        w = self._width()
        self._append_block(
            tui_render.render_approval_request(summary, w, preview=preview)
        )
        get_app().invalidate()

        def _ask() -> ApprovalDecision:
            from ui.repl import ask_permission

            choice = ask_permission(summary)
            mapping: dict[str, ApprovalDecision] = {
                "1": "once",
                "2": "session",
                "3": "deny",
            }
            return mapping.get(choice, "deny")

        return await run_in_terminal(_ask)

    async def _on_tool_start(self, tool_name: str, detail: str) -> None:
        w = self._width()
        label = tool_display_label(tool_name)
        self._append_block(tui_render.render_agent_activity(label, detail, w))
        get_app().invalidate()

    async def _on_tool_done(self, tool_name: str, detail: str, output: str) -> None:
        w = self._width()
        label = tool_display_label(tool_name)
        self._append_block(
            tui_render.render_tool_event(label, detail, w, phase="done")
        )
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

    def _handle_command(self, text: str) -> None:
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
            get_app().create_background_task(self._run_provider_command(text))
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
            get_app().create_background_task(self._run_plan(goal))
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
            get_app().create_background_task(self._run_multitask(goal_line))
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

        if cmd == "/clear":
            self._transcript_area.text = ""
            self._board.clear()
            self._sync_board_height()
            self.llm.messages = [
                {"role": "system", "content": self.llm.messages[0]["content"]}
            ]
            self.state.cost = 0.0
            self.state.status = "ready"
            return

        if cmd == "/model":
            if args.strip():
                self.llm.set_model(args.strip())
                self.state.model = self.llm.model
            self._append_block(
                tui_render.render_system(f"Model: {self.state.model}", w)
            )
            return

        if cmd in {"/cost", "/usage"}:
            self._append_block(
                tui_render.render_system(
                    f"Session: ${TOTAL_COST:.4f} · {TOTAL_TOKENS} tokens", w
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
            get_app().create_background_task(self._run_gen_skill(description))
            return

        if cmd == "/create-skill":
            get_app().create_background_task(self._run_create_skill())
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
                self._append_block(tui_render.render_system(clean.strip(), w))
            app.invalidate()

        self._agent_busy = True
        self._start_spinner("thinking")
        try:
            result = await orch.run(
                goal,
                on_progress=on_progress,
                on_multitask_event=on_multitask_event,
            )
        finally:
            self._stop_spinner()
            self._agent_busy = False

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
        self._update_board(
            "Plan",
            [TaskBoardItem("1", "Building plan...", "running")],
        )
        self._agent_busy = True
        self._start_spinner("thinking")
        try:
            task_manager.goal = goal
            result = await self.llm.send_plan_async(goal)
        finally:
            self._stop_spinner()
            self._agent_busy = False

        self._board_from_plan()
        self.state.cost = TOTAL_COST
        self.state.tokens = TOTAL_TOKENS

        if result.ok:
            self._append_block(
                tui_render.render_assistant_message(result.content or "Plan created.", w)
            )
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

        self._agent_busy = True
        self._start_spinner("thinking")
        try:
            result = await self.llm.generate_skill_file_async(description.strip())
        finally:
            self._stop_spinner()
            self._agent_busy = False

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
                self._handle_command(text)
                app.invalidate()
                return

            intent = detect_intent(text)
            if intent == "multitask":
                await self._run_multitask(text)
                return
            if intent == "plan":
                await self._run_plan(text)
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
            self._agent_busy = True
            self._start_spinner("thinking")

            self._agent_task = asyncio.current_task()
            result = await self.llm.send_message_async(text)
            self._stop_spinner()
            self.llm.set_stream_callbacks()
            self._end_live_response()
            self._agent_busy = False
            self._agent_task = None

            self.state.cost = TOTAL_COST
            self.state.tokens = TOTAL_TOKENS
            self.state.model = self.llm.model

            if result.ok and (result.content or self._stream_buffer):
                body = result.content or "".join(self._stream_buffer)
                self._transcript_area.text = self._transcript_prefix + tui_render.render_assistant_message(
                    body, w
                )
                explore = get_turn_explore_summary()
                if explore:
                    self._append_block(tui_render.render_explore_summary(explore, w))
                self._append_block(tui_render.render_turn_divider(w))
                self.state.status = "ready"
            elif result.ok:
                self._append_block(tui_render.render_system("(empty response)", w))
                self.state.status = "ready"
            elif "cancelled" in (result.error or "").lower():
                self._append_block(tui_render.render_system("Stopped.", w))
                self.state.status = "ready"
            else:
                self._append_block(tui_render.render_error(result.display_text, w))
                self.state.status = "error"

            app.invalidate()
        except asyncio.CancelledError:
            self._stop_spinner()
            self._end_live_response()
            self._agent_busy = False
            raise
        except Exception:
            self._stop_spinner()
            self._end_live_response()
            self._agent_busy = False
            self._append_block(
                tui_render.render_error(traceback.format_exc(limit=2), w)
            )
            self.state.status = "error"
            app.invalidate()

    def _on_accept(self, buff: Buffer) -> bool:
        text = buff.text.strip()
        if not text:
            return False

        w = self._width()
        if not text.startswith("/"):
            self._append_block(tui_render.render_user_message(text, w))

        get_app().invalidate()
        self._agent_task = get_app().create_background_task(self._process_message(text))
        return False

    def run(self) -> None:
        w = 100
        self._transcript_area.text = tui_render.render_welcome(
            w, model=self.state.model, cwd=self.state.cwd
        )
        self._scroll_transcript_to_end()
        self.app.run()


def run_tui() -> None:
    """Entry point for `axon tui`."""
    from dotenv import load_dotenv

    os.environ.setdefault("PROMPT_TOOLKIT_BELL", "0")
    load_dotenv()
    llm = LLMManager()
    AxonTUI(llm).run()
