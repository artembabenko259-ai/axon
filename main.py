from __future__ import annotations

import asyncio
import io
import sys
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

from llm_client import LLMManager
from ui.axon_terminal import estimate_cost
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
    cost: float = 0.0
    status: str = "Ready"


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


def _handle_slash_command(
    text: str,
    *,
    chat_history: TextArea,
    llm_manager: LLMManager,
    state: SessionState,
    application: Application,
) -> bool:
    """Handle slash commands. Returns True if handled (skip LLM)."""
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if cmd == "/exit":
        application.exit()
        return True

    if cmd == "/help":
        lines = [f"  {name:<10} {desc}" for name, desc in AXON_COMMANDS.items()]
        chat_history.text += "AXON: Commands:\n" + "\n".join(lines) + "\n"
        return True

    if cmd == "/clear":
        chat_history.text = CHAT_PLACEHOLDER
        state.cost = 0.0
        llm_manager.messages = [llm_manager.messages[0]]
        return True

    if cmd == "/model":
        if args.strip():
            llm_manager.set_model(args.strip())
            state.model = llm_manager.model
            chat_history.text += f"AXON: Model set to {llm_manager.model}\n"
        else:
            chat_history.text += f"AXON: Current model: {llm_manager.model}\n"
        return True

    chat_history.text += f"AXON: Unknown command {cmd}. Type /help.\n"
    return True


def main() -> None:
    load_dotenv()

    llm_manager = LLMManager()
    state = SessionState(model=llm_manager.model)

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

    def accept_input(buff):
        text = buff.text
        if not text.strip():
            return False

        chat_history.text += f"\n❯ {text}\n"
        get_app().invalidate()

        async def process_ai():
            if text.strip().startswith("/"):
                _handle_slash_command(
                    text,
                    chat_history=chat_history,
                    llm_manager=llm_manager,
                    state=state,
                    application=get_app(),
                )
                get_app().invalidate()
                return

            state.status = "Thinking..."
            chat_history.text += "AXON: Thinking...\n"
            get_app().invalidate()

            try:
                llm_manager.reload_credentials()
                state.model = llm_manager.model
                result = await llm_manager.send_message_async(text)

                chat_history.text = chat_history.text.replace("AXON: Thinking...\n", "")
                chat_history.text += f"AXON: {result.display_text}\n"

                if result.usage:
                    state.cost += estimate_cost(
                        result.usage.prompt_tokens,
                        result.usage.completion_tokens,
                    )
                state.status = "Ready" if result.ok else "Error"
            except Exception as exc:
                chat_history.text = chat_history.text.replace("AXON: Thinking...\n", "")
                chat_history.text += f"[ERROR]: {str(exc)}\n"
                state.status = "Error"

            get_app().invalidate()

        get_app().create_background_task(process_ai())
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

    asyncio.run(app.run_async())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
