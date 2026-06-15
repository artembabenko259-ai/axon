from __future__ import annotations

import asyncio
import io
import os
import traceback
from dataclasses import dataclass, field
from typing import Literal

from prompt_toolkit.application import Application, get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import merge_completers
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Dimension as D
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.layout.scrollable_pane import ScrollablePane
from prompt_toolkit.styles import Style
from rich.align import Align
from rich.box import HORIZONTALS
from rich.console import Console
from rich.panel import Panel
from rich.style import Style as RichStyle
from rich.text import Text

from llm_client import LLMManager, LLMResult
from ui.axon_terminal import estimate_cost
from ui.branding import build_gradient_logo, generate_logo_text
from ui.completer import AXON_COMMANDS, AxonCommandCompleter
from ui.theme import DEFAULT_THEME

MessageRole = Literal["user", "assistant", "error", "system"]
AppStatus = Literal["ready", "thinking", "error"]

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
PROMPT_SYMBOL = "❯ "
CHAT_PLACEHOLDER = "Ask AXON anything — type /help for commands"


@dataclass
class ChatEntry:
    role: MessageRole
    content: str


@dataclass
class AxonTUIState:
    model: str
    cost_so_far: float = 0.0
    status: AppStatus = "ready"
    spinner_index: int = 0
    messages: list[ChatEntry] = field(default_factory=list)

    def tick_spinner(self) -> None:
        self.spinner_index = (self.spinner_index + 1) % len(SPINNER)

    def add_user(self, text: str) -> None:
        self.messages.append(ChatEntry("user", text))

    def add_assistant(self, text: str) -> None:
        self.messages.append(ChatEntry("assistant", text))

    def add_system(self, text: str) -> None:
        self.messages.append(ChatEntry("system", text))

    def add_error(self, text: str) -> None:
        self.messages.append(ChatEntry("error", text))
        self.status = "error"


def _terminal_width() -> int:
    try:
        return get_app().output.get_size().columns
    except Exception:
        return 100


def _rich_to_ansi(renderable, width: int) -> str:
    buffer = io.StringIO()
    console = Console(
        file=buffer,
        force_terminal=True,
        width=max(width, 40),
        legacy_windows=True,
    )
    console.print(renderable)
    return buffer.getvalue()


def _build_logo_ansi(width: int) -> str:
    logo = build_gradient_logo(DEFAULT_THEME, font="slant")
    return _rich_to_ansi(Align.center(logo), width)


def _build_header_ansi(state: AxonTUIState, width: int) -> str:
    short = state.model.rsplit("/", 1)[-1]
    header = Text()
    header.append("AXON", style=RichStyle(color="#e8eaf0", bold=True))
    header.append("  ·  ", style=RichStyle(color="#3f3f46"))
    header.append(short, style=RichStyle(color="#a1a1aa"))
    header.append("  ·  ", style=RichStyle(color="#3f3f46"))
    header.append(f"${state.cost_so_far:.4f}", style=RichStyle(color="#67e8f9"))
    return _rich_to_ansi(
        Panel(header, box=HORIZONTALS, border_style=RichStyle(color="#27272a"), padding=(0, 1)),
        width,
    )


def _build_status_ansi(state: AxonTUIState, width: int) -> str:
    line = Text()
    if state.status == "thinking":
        line.append(f"{SPINNER[state.spinner_index]} ", style=RichStyle(color="#67e8f9"))
        line.append("Thinking…", style=RichStyle(color="#a1a1aa"))
    elif state.status == "error":
        line.append("● ", style=RichStyle(color="#f87171"))
        line.append("Error", style=RichStyle(color="#fca5a5"))
    else:
        line.append("● ", style=RichStyle(color="#4ade80"))
        line.append("Ready", style=RichStyle(color="#71717a"))
    line.append("   Tab · ↑↓ menu", style=RichStyle(color="#52525b", dim=True))
    return _rich_to_ansi(line, width)


AXON_STYLE = Style.from_dict(
    {
        "header": "bg:#0c0c0c",
        "chat": "bg:#09090b #e4e4e7",
        "status": "bg:#0c0c0c",
        "input-area": "bg:#111111 #e4e4e7",
        "input-rule": "bg:#27272a",
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
    """Full-screen AXON TUI with bottom-bar input and slash-command completion."""

    def __init__(self, llm: LLMManager) -> None:
        self.llm = llm
        self.state = AxonTUIState(model=llm.model)
        self._thinking = False
        self._spinner_task: asyncio.Task | None = None
        self._logo_ansi = ""

        self._chat_buffer = Buffer(
            read_only=True,
            document=Document(CHAT_PLACEHOLDER),
        )

        self.input_buffer = Buffer(
            completer=merge_completers([AxonCommandCompleter()]),
            history=FileHistory(os.path.expanduser("~/.axon_history")),
            complete_while_typing=True,
            accept_handler=self._on_accept,
        )

        logo_lines = len([ln for ln in generate_logo_text().splitlines() if ln.strip()]) or 4

        self._chat_window = Window(
            BufferControl(self._chat_buffer, focusable=False),
            style="class:chat",
            wrap_lines=True,
            dont_extend_height=True,
        )
        self._chat_pane = ScrollablePane(
            self._chat_window,
            show_scrollbar=False,
            keep_cursor_visible=False,
            keep_focused_window_visible=False,
        )

        self._input_window = Window(
            BufferControl(
                self.input_buffer,
                input_processors=[BeforeInput(PROMPT_SYMBOL, style="class:prompt")],
            ),
            height=D.exact(1),
            style="class:input-area",
        )

        self._root = HSplit(
            [
                Window(
                    FormattedTextControl(self._logo_fragments, focusable=False),
                    height=D.exact(logo_lines),
                    style="class:header",
                ),
                Window(
                    FormattedTextControl(self._header_fragments, focusable=False),
                    height=D.exact(3),
                    style="class:header",
                ),
                self._chat_pane,
                Window(
                    FormattedTextControl(self._status_fragments, focusable=False),
                    height=D.exact(1),
                    style="class:status",
                ),
                Window(height=D.exact(1), char="─", style="class:input-rule"),
                self._input_window,
                CompletionsMenu(max_height=7, scroll_offset=1),
            ]
        )

        self._layout = Layout(self._root, focused_element=self._input_window)
        self.app = Application(
            layout=self._layout,
            key_bindings=self._build_keybindings(),
            style=AXON_STYLE,
            full_screen=True,
            mouse_support=True,
            refresh_interval=0.1,
        )

    def _build_keybindings(self) -> KeyBindings:
        kb = KeyBindings()

        @kb.add("c-c")
        def _(event) -> None:
            event.app.exit()

        @kb.add("c-d")
        def _(event) -> None:
            event.app.exit()

        return kb

    def _logo_fragments(self):
        width = _terminal_width()
        if not self._logo_ansi:
            self._logo_ansi = _build_logo_ansi(width)
        return ANSI(self._logo_ansi)

    def _header_fragments(self):
        return ANSI(_build_header_ansi(self.state, _terminal_width()))

    def _status_fragments(self):
        return ANSI(_build_status_ansi(self.state, _terminal_width()))

    def _append_to_chat_display(self, line: str) -> None:
        """Append one line to the read-only chat history buffer."""
        current = self._chat_buffer.document.text
        if current == CHAT_PLACEHOLDER:
            current = ""

        new_text = f"{current}\n{line}".strip() if current else line
        self._chat_buffer.set_document(
            Document(new_text, cursor_position=len(new_text)),
            bypass_readonly=True,
        )
        self._chat_pane.vertical_scroll = 10_000_000

    def _scroll_chat_to_bottom(self) -> None:
        self._chat_pane.vertical_scroll = 10_000_000

    async def _spinner_loop(self) -> None:
        while self._thinking:
            self.state.tick_spinner()
            get_app().invalidate()
            await asyncio.sleep(0.08)

    def _start_spinner(self) -> None:
        self._thinking = True
        self.state.status = "thinking"
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

        if cmd == "/exit":
            get_app().exit()
            return

        if cmd == "/help":
            lines = [f"  {c:<10} {d}" for c, d in AXON_COMMANDS.items()]
            self._append_to_chat_display("AXON: Commands:\n" + "\n".join(lines))
            self.state.add_system("help")
            return

        if cmd == "/clear":
            self.state.messages.clear()
            self.state.cost_so_far = 0.0
            self.state.status = "ready"
            self._chat_buffer.set_document(
                Document(CHAT_PLACEHOLDER),
                bypass_readonly=True,
            )
            self._chat_pane.vertical_scroll = 0
            return

        if cmd == "/status":
            self._append_to_chat_display(
                "AXON: "
                f"Model: {self.state.model} | "
                f"Cost: ${self.state.cost_so_far:.4f} | "
                f"Messages: {len(self.state.messages)}"
            )
            return

        if cmd == "/model":
            if not args.strip():
                self._append_to_chat_display(f"AXON: Current model: {self.state.model}")
            else:
                self.llm.set_model(args.strip())
                self.state.model = self.llm.model
                self._append_to_chat_display(f"AXON: Model set to {self.llm.model}")
            return

        self._append_to_chat_display(f"AXON: Unknown command: {cmd}. Type /help.")
        self.state.status = "error"

    async def _process_ai_response(self, text: str) -> None:
        """Background coroutine: call LLM without blocking the UI loop."""
        app = get_app()

        try:
            if text.startswith("/"):
                self._handle_command(text)
                app.invalidate()
                return

            self._start_spinner()
            result = await asyncio.to_thread(self.llm.send_message, text)

            if result.ok and result.content:
                self._append_to_chat_display(f"AXON: {result.content}")
                self.state.add_assistant(result.content)
                if result.usage:
                    self.state.cost_so_far += estimate_cost(
                        result.usage.prompt_tokens,
                        result.usage.completion_tokens,
                    )
                self.state.status = "ready"
            elif result.ok:
                self._append_to_chat_display("AXON: (empty response)")
                self.state.status = "ready"
            else:
                self._append_to_chat_display(f"AXON: {result.error}")
                self.state.add_error(result.error or "Unknown error")

            self._scroll_chat_to_bottom()
            app.invalidate()
        except Exception:
            self._append_to_chat_display(
                "AXON: Unexpected error while processing your message.\n"
                + traceback.format_exc(limit=2).strip()
            )
            self.state.status = "error"
            app.invalidate()
        finally:
            self._stop_spinner()
            app.invalidate()

    def _on_accept(self, buff: Buffer) -> bool:
        """
        Enter handler:
        1. Capture input text
        2. Append 'User: ...' to chat and redraw immediately
        3. Schedule async LLM call as a background task
        4. Return False so prompt_toolkit clears the input field
        """
        text = buff.text.strip()
        if not text:
            return False

        app = get_app()

        if not text.startswith("/"):
            self._append_to_chat_display(f"User: {text}")
            self.state.add_user(text)
            self._scroll_chat_to_bottom()
            app.invalidate()

        app.create_background_task(self._process_ai_response(text))
        return False

    def run(self) -> None:
        self.app.run()
