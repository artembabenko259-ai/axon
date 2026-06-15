from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

from rich.align import Align
from rich.box import HORIZONTALS
from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.markdown import Markdown
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from llm_client import LLMResult

MessageRole = Literal["user", "assistant", "error"]
AppStatus = Literal["ready", "thinking", "error"]

SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# Fallback cost estimate ($ per 1M tokens) when API omits pricing
INPUT_COST_PER_M = 0.50
OUTPUT_COST_PER_M = 1.50


@dataclass
class ChatEntry:
    role: MessageRole
    content: str


@dataclass
class AxonTerminalUI:
    """Claude Code–inspired permanent frame for the AXON CLI."""

    console: Console
    model: str
    cost_so_far: float = 0.0
    status: AppStatus = "ready"
    spinner_index: int = 0
    messages: list[ChatEntry] = field(default_factory=list)
    _header_size: int = 3
    _footer_size: int = 2

    def set_model(self, model: str) -> None:
        self.model = model

    def set_thinking(self, thinking: bool) -> None:
        self.status = "thinking" if thinking else "ready"

    def tick_spinner(self) -> None:
        self.spinner_index = (self.spinner_index + 1) % len(SPINNER_FRAMES)

    def add_user(self, content: str) -> None:
        self.messages.append(ChatEntry("user", content))

    def add_assistant(self, content: str) -> None:
        self.messages.append(ChatEntry("assistant", content))

    def add_error(self, content: str) -> None:
        self.messages.append(ChatEntry("error", content))
        self.status = "error"

    def apply_result(self, result: LLMResult) -> None:
        if not result.ok:
            self.add_error(result.error or "Unknown error")
            return
        if result.content:
            self.add_assistant(result.content)
        if result.usage:
            self.cost_so_far += estimate_cost(result.usage.prompt_tokens, result.usage.completion_tokens)
        self.status = "ready"

    def build_layout(self) -> Layout:
        root = Layout(name="root")
        root.split_column(
            Layout(name="header", size=self._header_size),
            Layout(name="chat", ratio=1),
            Layout(name="footer", size=self._footer_size),
        )
        root["header"].update(self._render_header())
        root["chat"].update(self._render_chat())
        root["footer"].update(self._render_footer())
        return root

    def _render_header(self) -> RenderableType:
        short_model = self.model.rsplit("/", 1)[-1]
        header = Text()
        header.append("AXON", style=Style(color="#e8eaf0", bold=True))
        header.append("  ·  ", style=Style(color="#3f3f46"))
        header.append(short_model, style=Style(color="#a1a1aa"))
        header.append("  ·  ", style=Style(color="#3f3f46"))
        header.append(f"${self.cost_so_far:.4f}", style=Style(color="#67e8f9"))
        return Panel(
            Align.left(header),
            box=HORIZONTALS,
            style=Style(bgcolor="#0c0c0c"),
            border_style=Style(color="#27272a"),
            padding=(0, 1),
        )

    def _render_chat(self) -> RenderableType:
        if not self.messages:
            placeholder = Align.center(
                Text(
                    "Ask AXON anything",
                    style=Style(color="#52525b", italic=True),
                ),
                vertical="middle",
            )
            body: RenderableType = placeholder
        else:
            items: list[RenderableType] = []
            visible = self._visible_messages()
            for entry in visible:
                items.append(self._render_message(entry))
            body = Group(*items)

        return Panel(
            body,
            box=HORIZONTALS,
            style=Style(bgcolor="#09090b"),
            border_style=Style(color="#27272a"),
            padding=(1, 1),
        )

    def _render_message(self, entry: ChatEntry) -> RenderableType:
        if entry.role == "user":
            line = Text()
            line.append("You  ", style=Style(color="#71717a", dim=True))
            line.append(entry.content, style=Style(color="#fafafa"))
            return Align.right(line)

        if entry.role == "error":
            line = Text()
            line.append("AXON  ", style=Style(color="#f87171", dim=True))
            line.append(entry.content, style=Style(color="#fca5a5"))
            return line

        block = Group(
            Text("AXON", style=Style(color="#67e8f9", dim=True)),
            Markdown(entry.content, code_theme="monokai"),
        )
        return block

    def _render_footer(self) -> RenderableType:
        status_line = Text()
        if self.status == "thinking":
            frame = SPINNER_FRAMES[self.spinner_index]
            status_line.append(f"{frame} ", style=Style(color="#67e8f9"))
            status_line.append("Thinking…", style=Style(color="#a1a1aa"))
        elif self.status == "error":
            status_line.append("● ", style=Style(color="#f87171"))
            status_line.append("Error", style=Style(color="#fca5a5"))
        else:
            status_line.append("● ", style=Style(color="#4ade80"))
            status_line.append("Ready", style=Style(color="#71717a"))

        status_line.append("    ", style=Style())
        status_line.append("❯ input below", style=Style(color="#52525b", italic=True))

        return Panel(
            status_line,
            box=HORIZONTALS,
            style=Style(bgcolor="#0c0c0c"),
            border_style=Style(color="#27272a"),
            padding=(0, 1),
        )

    def _visible_messages(self) -> list[ChatEntry]:
        height = max(self.console.size.height - self._header_size - self._footer_size - 6, 8)
        max_items = max(height // 4, 6)
        return self.messages[-max_items:]


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (prompt_tokens / 1_000_000) * INPUT_COST_PER_M + (
        completion_tokens / 1_000_000
    ) * OUTPUT_COST_PER_M


def run_with_spinner(
    ui: AxonTerminalUI,
    live,
    fn,
    refresh_interval: float = 0.08,
):
    """Run a blocking call while animating the thinking spinner in the live frame."""
    import threading

    ui.set_thinking(True)
    result_box: dict[str, object] = {}

    def worker() -> None:
        result_box["result"] = fn()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    while thread.is_alive():
        ui.tick_spinner()
        live.update(ui.build_layout())
        time.sleep(refresh_interval)

    thread.join()
    ui.set_thinking(False)
    return result_box.get("result")
