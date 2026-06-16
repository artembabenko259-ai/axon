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
from prompt_toolkit.completion import merge_completers
from prompt_toolkit.document import Document
from prompt_toolkit.filters import has_completions, has_focus
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
from skills.tools import ApprovalDecision, tool_display_label
from ui.completer import AXON_COMMANDS, AxonCommandCompleter
from ui import tui_render

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
    """Claude Code–style TUI: transcript scrolls, slim pinned composer."""

    def __init__(self, llm: LLMManager) -> None:
        self.llm = llm
        self.state = AxonTUIState(
            model=llm.model,
            cwd=str(Path.cwd()),
        )
        self._thinking = False
        self._spinner_task: asyncio.Task | None = None
        self._stream_buffer: list[str] = []

        self._transcript_area = TextArea(
            text="",
            read_only=True,
            focusable=False,
            wrap_lines=True,
            scrollbar=True,
            style="class:chat",
        )

        self.input_buffer = Buffer(
            completer=merge_completers([AxonCommandCompleter()]),
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

    def _width(self) -> int:
        try:
            return get_app().output.get_size().columns
        except Exception:
            return 100

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

    def _build_keybindings(self) -> KeyBindings:
        kb = KeyBindings()
        input_focused = has_focus(self._input_window)
        send_enter = input_focused & ~has_completions

        def _send(event) -> None:
            event.current_buffer.validate_and_handle()

        def _newline(event) -> None:
            event.current_buffer.insert_text("\n")

        @kb.add("c-c")
        def _(event) -> None:
            event.app.exit()

        @kb.add("c-d")
        def _(event) -> None:
            event.app.exit()

        @kb.add("enter", filter=send_enter)
        @kb.add("escape", "enter", filter=input_focused)
        def _(event) -> None:
            _send(event)

        @kb.add("c-j", filter=input_focused)
        def _(event) -> None:
            _newline(event)

        return kb

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
        else:
            status = "ready"
        line = f" {status} | Enter send | Ctrl+J newline | /help"
        return [("class:composer", line)]

    async def _request_approval(self, tool_name: str, detail: str) -> ApprovalDecision:
        label = tool_display_label(tool_name)
        command_detail = f"{label}: {detail.strip() or '(no details)'}"
        w = self._width()
        self._append_block(tui_render.render_approval_request(command_detail, w))
        get_app().invalidate()

        def _ask() -> ApprovalDecision:
            from ui.repl import ask_permission

            choice = ask_permission(command_detail)
            mapping: dict[str, ApprovalDecision] = {
                "1": "once",
                "2": "session",
                "3": "deny",
            }
            return mapping.get(choice, "deny")

        return await run_in_terminal(_ask)

    async def _on_tool_start(self, tool_name: str, detail: str) -> None:
        w = self._width()
        self._append_block(
            tui_render.render_tool_event(tool_name, detail, w, phase="run")
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
            lines = "\n".join(f"  {c:<12} {d}" for c, d in AXON_COMMANDS.items())
            self._append_block(tui_render.render_system(f"Commands:\n{lines}", w))
            return

        if cmd == "/clear":
            self._transcript_area.text = ""
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

        self._append_block(tui_render.render_error(f"Unknown command {cmd}. /help"), w)
        self.state.status = "error"

    async def _process_message(self, text: str) -> None:
        app = get_app()
        w = self._width()

        try:
            if text.startswith("/"):
                self._handle_command(text)
                app.invalidate()
                return

            self._stream_buffer.clear()

            async def on_start() -> None:
                self._start_spinner("streaming")

            async def on_token(token: str) -> None:
                self._stream_buffer.append(token)

            async def on_end() -> None:
                pass

            self.llm.set_stream_callbacks(
                on_token=on_token,
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

            if result.ok and (result.content or self._stream_buffer):
                body = result.content or "".join(self._stream_buffer)
                self._append_block(tui_render.render_assistant_message(body, w))
                self._append_block(tui_render.render_turn_divider(w))
                self.state.status = "ready"
            elif result.ok:
                self._append_block(tui_render.render_system("(empty response)", w))
                self.state.status = "ready"
            else:
                self._append_block(tui_render.render_error(result.display_text, w))
                self.state.status = "error"

            app.invalidate()
        except Exception:
            self._stop_spinner()
            self._append_block(
                tui_render.render_error(traceback.format_exc(limit=2)),
                w,
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
        get_app().create_background_task(self._process_message(text))
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
