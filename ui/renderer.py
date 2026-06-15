from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from rich.align import Align
from rich.box import HORIZONTALS
from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.style import Style
from rich.text import Text

from ui.branding import APP_NAME, VERSION, build_header
from ui.theme import CLITheme, DEFAULT_THEME

MessageRole = Literal["user", "assistant", "system"]


@dataclass
class ChatMessage:
    role: MessageRole
    content: str


@dataclass
class UIRenderer:
    """Builds and updates the split-pane terminal layout."""

    console: Console
    theme: CLITheme = field(default_factory=lambda: DEFAULT_THEME)
    _messages: list[ChatMessage] = field(default_factory=list)
    _model: str = ""
    _status: str = field(default_factory=lambda: DEFAULT_THEME.status_ready)
    _streaming: str = ""
    _is_streaming: bool = False
    _live: Live | None = field(default=None, repr=False)
    _input_size: int = 2
    _header_size: int = 12
    _logo_font: str = "slant"

    def attach_live(self, live: Live) -> None:
        self._live = live

    def set_model(self, model: str) -> None:
        self._model = model
        self._recalculate_header_size()
        self.refresh()

    def set_status(self, status: str) -> None:
        self._status = status
        self.refresh()

    def add_user_message(self, content: str) -> None:
        self._messages.append(ChatMessage("user", content))
        self.refresh()

    def add_assistant_message(self, content: str) -> None:
        self._messages.append(ChatMessage("assistant", content))
        self.refresh()

    def add_system_message(self, content: str) -> None:
        self._messages.append(ChatMessage("system", content))
        self.refresh()

    def clear_messages(self) -> None:
        self._messages.clear()
        self._streaming = ""
        self._is_streaming = False
        self.refresh()

    def stream_begin(self) -> None:
        self._is_streaming = True
        self._streaming = ""
        self.set_status("Streaming")

    def stream_update(self, content: str) -> None:
        self._streaming = content
        self.refresh()

    def stream_end(self, content: str) -> None:
        self._is_streaming = False
        self._streaming = ""
        if content:
            self._messages.append(ChatMessage("assistant", content))
        self.refresh()

    def stream_cancel(self) -> None:
        self._is_streaming = False
        self._streaming = ""
        self.refresh()

    def refresh(self) -> None:
        if self._live is not None:
            self._live.update(self.build_layout())

    def _recalculate_header_size(self) -> None:
        _, height = build_header(
            self.theme,
            self._short_model_name(),
            self._status,
            font=self._logo_font,
        )
        self._header_size = height

    def build_layout(self) -> Layout:
        self._recalculate_header_size()

        layout = Layout(name="root")
        layout.split_column(
            Layout(name="header", size=self._header_size),
            Layout(name="chat", ratio=1),
            Layout(name="separator", size=1),
            Layout(name="input", size=self._input_size),
        )

        layout["header"].update(self._render_header_pane())
        layout["chat"].update(self._render_chat_pane())
        layout["separator"].update(
            Rule(style=Style(color=self.theme.border_subtle), characters="─")
        )
        layout["input"].update(self._render_input_pane())
        return layout

    def _render_header_pane(self) -> RenderableType:
        header, _ = build_header(
            self.theme,
            self._short_model_name(),
            self._status,
            font=self._logo_font,
        )
        return Panel(
            header,
            box=HORIZONTALS,
            style=Style(bgcolor=self.theme.background),
            border_style=Style(color=self.theme.border_subtle),
            padding=(0, 1),
            title=f"[{self.theme.text_muted}]{APP_NAME}[/]",
            title_align="left",
        )

    def _render_chat_pane(self) -> RenderableType:
        items: list[RenderableType] = []

        if not self._messages and not self._is_streaming:
            items.append(
                Text(
                    "Start a conversation…",
                    style=Style(color=self.theme.text_muted, italic=True),
                )
            )
        else:
            for message in self._visible_messages():
                items.append(self._render_message(message))

            if self._is_streaming:
                items.append(self._render_streaming_block())

        content = Group(*items) if items else Text("")
        return Panel(
            content,
            box=HORIZONTALS,
            style=Style(bgcolor=self.theme.background),
            border_style=Style(color=self.theme.border_subtle),
            padding=(0, 1),
            title="[chat]",
            title_align="left",
        )

    def _render_message(self, message: ChatMessage) -> RenderableType:
        if message.role == "user":
            line = Text()
            line.append(
                f"{self.theme.prompt_symbol} ",
                style=Style(color=self.theme.accent),
            )
            line.append(message.content, style=Style(color=self.theme.user_prompt))
            return line

        if message.role == "assistant":
            return Markdown(
                message.content,
                style=Style(color=self.theme.text_primary),
                code_theme="monokai",
            )

        return Text(message.content, style=Style(color=self.theme.system))

    def _render_streaming_block(self) -> RenderableType:
        body = self._streaming or "▌"
        return Panel(
            Markdown(body, code_theme="monokai"),
            box=HORIZONTALS,
            style=Style(bgcolor=self.theme.surface),
            border_style=Style(color=self.theme.accent, dim=True),
            padding=(0, 1),
            title="[streaming]",
            title_align="left",
        )

    def _render_input_pane(self) -> RenderableType:
        prompt = Text()
        prompt.append(
            f"{self.theme.prompt_symbol} ",
            style=Style(color=self.theme.accent, bold=True),
        )
        prompt.append(
            "input",
            style=Style(color=self.theme.text_muted, italic=True),
        )
        return Panel(
            prompt,
            box=HORIZONTALS,
            style=Style(bgcolor=self.theme.surface),
            border_style=Style(color=self.theme.border_subtle),
            padding=(0, 1),
        )

    def get_display_model(self) -> str:
        return self._short_model_name()

    def _short_model_name(self) -> str:
        if not self._model:
            return "—"
        return self._model.rsplit("/", 1)[-1]

    def _visible_messages(self) -> list[ChatMessage]:
        """Return the tail of chat history that fits the chat pane."""
        available = max(
            self.console.size.height - self._header_size - self._input_size - 5,
            6,
        )
        max_messages = max(available // 3, 4)
        return self._messages[-max_messages:]

    def format_help(self, rows: list[tuple[str, str]]) -> str:
        lines = ["**Commands**", ""]
        for command, description in rows:
            lines.append(f"- `{command}` — {description}")
        return "\n".join(lines)

    def format_skills(self, rows: list[tuple[str, str]]) -> str:
        if not rows:
            return "_No skills loaded._"
        lines = ["**Skills**", ""]
        for name, description in rows:
            lines.append(f"- **{name}** — {description}")
        return "\n".join(lines)
