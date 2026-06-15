from __future__ import annotations

import asyncio
import io
import sys
import uuid
from dataclasses import dataclass

from dotenv import load_dotenv
from prompt_toolkit.application import Application, get_app
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.layout import Dimension as D
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea
from rich.align import Align
from rich.box import HORIZONTALS
from rich.console import Console
from rich.panel import Panel
from rich.style import Style as RichStyle
from rich.text import Text

from bridge import AxonBridge
from llm_client import (
    LLMManager,
    TOTAL_COST,
    TOTAL_TOKENS,
    reset_session_counters,
)
from ui.branding import build_gradient_logo, generate_logo_text
from ui.completer import AXON_COMMANDS, AxonCommandCompleter
from ui.theme import DEFAULT_THEME

CHAT_PLACEHOLDER = "Ask AXON anything — type /help for commands\n"

AXON_STYLE = Style.from_dict(
    {
        "header": "bg:#0c0c0c",
        "status-bar": "bg:#0c0c0c",
        "chat": "bg:#09090b #e4e4e7",
        "input": "bg:#111111 #e4e4e7",
        "separator": "bg:#27272a",
        "text-area.prompt": "bold #67e8f9",
        "completion-menu": "bg:#18181b #a1a1aa",
        "completion-menu.border": "#27272a",
        "completion-menu.completion": "bg:#18181b #a1a1aa",
        "completion-menu.completion.current": "bg:#27272a bold #67e8f9",
        "completion-menu.meta.completion": "bg:#18181b #52525b italic",
        "completion-menu.meta.completion.current": "bg:#27272a #71717a italic",
    }
)


@dataclass
class SessionState:
    model: str
    status: str = "Ready"

    @property
    def total_tokens(self) -> int:
        return TOTAL_TOKENS

    @property
    def cost(self) -> float:
        return TOTAL_COST


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


def _build_header_ansi(state: SessionState, width: int) -> str:
    logo = build_gradient_logo(DEFAULT_THEME, font="slant")
    short_model = state.model.rsplit("/", 1)[-1]

    status = Text()
    status.append("Model: ", style=RichStyle(color="#71717a"))
    status.append(short_model, style=RichStyle(color="#a1a1aa"))
    status.append("   Cost: ", style=RichStyle(color="#71717a"))
    status.append(f"${state.cost:.4f}", style=RichStyle(color="#67e8f9"))
    status.append("   Tokens: ", style=RichStyle(color="#71717a"))
    status.append(str(state.total_tokens), style=RichStyle(color="#a1a1aa"))
    status.append("   Status: ", style=RichStyle(color="#71717a"))
    status.append(state.status, style=RichStyle(color="#4ade80"))

    body = Text()
    body.append_text(logo)
    body.append("\n")
    body.append_text(status)

    return _rich_to_ansi(
        Panel(
            Align.center(body),
            box=HORIZONTALS,
            border_style=RichStyle(color="#27272a"),
            padding=(0, 1),
        ),
        width,
    )


async def start_axon() -> None:
    load_dotenv()

    llm_manager = LLMManager()
    state = SessionState(model=llm_manager.model)
    bridge = AxonBridge()

    logo_lines = len([ln for ln in generate_logo_text().splitlines() if ln.strip()]) or 4
    header_height = logo_lines + 4

    def header_fragments():
        return ANSI(_build_header_ansi(state, _terminal_width()))

    chat_history = TextArea(
        text=CHAT_PLACEHOLDER,
        read_only=True,
        scrollbar=True,
        focusable=False,
        wrap_lines=True,
        style="class:chat",
    )

    user_input = TextArea(
        text="",
        prompt="❯ ",
        multiline=False,
        completer=AxonCommandCompleter(),
        complete_while_typing=True,
        wrap_lines=True,
        style="class:input",
    )
    user_input.window.height = D.exact(1)

    def refresh_ui() -> None:
        try:
            get_app().invalidate()
        except Exception:
            pass

    async def sync_stats() -> None:
        await bridge.broadcast_stats(TOTAL_TOKENS, TOTAL_COST)

    async def apply_model(model: str, *, announce_cli: bool = True) -> None:
        llm_manager.set_model(model)
        state.model = model
        bridge._current_model = model
        if announce_cli:
            chat_history.text += f"AXON: Model set to {model}\n"
        await bridge.broadcast_model(model)
        refresh_ui()

    async def process_user_message(text: str, source: str = "terminal") -> None:
        stripped = text.strip()
        if not stripped:
            return

        if stripped.startswith("/"):
            parts = stripped.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            if cmd == "/exit":
                try:
                    get_app().exit()
                except Exception:
                    pass
                return

            if cmd == "/help":
                lines = [f"  {name:<10} {desc}" for name, desc in AXON_COMMANDS.items()]
                chat_history.text += "AXON: Commands:\n" + "\n".join(lines) + "\n"
                refresh_ui()
                return

            if cmd == "/clear":
                chat_history.text = CHAT_PLACEHOLDER
                reset_session_counters()
                llm_manager.messages = [llm_manager.messages[0]]
                await sync_stats()
                refresh_ui()
                return

            if cmd == "/model":
                if args.strip():
                    await apply_model(args.strip())
                else:
                    chat_history.text += f"AXON: Current model: {llm_manager.model}\n"
                    refresh_ui()
                return

            chat_history.text += f"AXON: Unknown command {cmd}. Type /help.\n"
            refresh_ui()
            return

        prefix = "[Web] " if source == "web" else ""
        chat_history.text += f"\n{prefix}❯ {stripped}\n"

        if source == "terminal":
            await bridge.broadcast_chat(
                role="user",
                text=stripped,
                source="terminal",
                message_id=f"terminal-user-{uuid.uuid4().hex[:8]}",
            )

        state.status = "Thinking..."
        chat_history.text += "AXON: Thinking...\n"
        refresh_ui()

        try:
            llm_manager.reload_credentials()
            state.model = llm_manager.model
            result = await llm_manager.send_message_async(stripped)

            chat_history.text = chat_history.text.replace("AXON: Thinking...\n", "")
            chat_history.text += f"AXON: {result.display_text}\n"

            if result.usage:
                await sync_stats()

            state.status = "Ready" if result.ok else "Error"

            await bridge.broadcast_chat(
                role="assistant",
                text=result.display_text,
                source=source,
                message_id=f"{source}-axon-{uuid.uuid4().hex[:8]}",
            )
        except Exception as exc:
            chat_history.text = chat_history.text.replace("AXON: Thinking...\n", "")
            error_text = f"[ERROR]: {str(exc)}"
            chat_history.text += f"{error_text}\n"
            state.status = "Error"
            await bridge.broadcast_chat(role="assistant", text=error_text, source=source)
        finally:
            refresh_ui()

    bridge.configure(
        process_chat=process_user_message,
        set_model=lambda model: apply_model(model, announce_cli=True),
        refresh_ui=refresh_ui,
        current_model=state.model,
    )

    def accept_input(buff):
        text = buff.text
        if not text.strip():
            return False
        get_app().create_background_task(process_user_message(text, "terminal"))
        return False

    user_input.accept_handler = accept_input

    root = HSplit(
        [
            Window(
                FormattedTextControl(header_fragments, focusable=False),
                height=D.exact(header_height),
                style="class:header",
            ),
            chat_history,
            Window(height=D.exact(1), char="─", style="class:separator"),
            user_input,
            CompletionsMenu(max_height=8, scroll_offset=1),
        ]
    )

    layout = Layout(root, focused_element=user_input.window)
    app = Application(
        layout=layout,
        style=AXON_STYLE,
        full_screen=True,
        mouse_support=True,
        refresh_interval=0.12,
    )

    # websockets.serve runs concurrently on this event loop while the CLI is active
    ws_server = await bridge.start()

    try:
        await app.run_async()
    finally:
        ws_server.close()
        await ws_server.wait_closed()


def main() -> None:
    asyncio.run(start_axon())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
