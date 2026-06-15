from __future__ import annotations

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style as PTStyle
from rich.console import Console
from rich.live import Live

from commands import CommandManager
from llm_client import LLMManager
from ui.branding import splash_renderable
from ui.renderer import UIRenderer
from ui.theme import DEFAULT_THEME


class CLIController:
    """AXON REPL loop with sticky header branding and bottom input."""

    def __init__(
        self,
        console: Console,
        ui: UIRenderer,
        command_manager: CommandManager,
        llm_manager: LLMManager,
        history_path: Path | None = None,
    ) -> None:
        self._console = console
        self._ui = ui
        self._command_manager = command_manager
        self._llm_manager = llm_manager
        self._history_path = history_path or Path.home() / ".axon_history"

    def _show_startup_splash(self) -> None:
        theme = self._ui.theme
        self._console.clear()
        self._ui.set_status(theme.status_ready)
        splash = splash_renderable(
            theme,
            model=self._ui.get_display_model(),
            status=theme.status_ready,
            font=self._ui._logo_font,
        )
        self._console.print(splash)

    def run(self) -> None:
        history = FileHistory(str(self._history_path))
        theme = self._ui.theme

        session = PromptSession(
            history=history,
            style=PTStyle.from_dict(
                {
                    "prompt": f"{theme.accent} bold",
                }
            ),
        )

        self._show_startup_splash()

        with Live(
            self._ui.build_layout(),
            console=self._console,
            screen=True,
            refresh_per_second=12,
            transient=False,
        ) as live:
            self._ui.attach_live(live)
            self._ui.set_status(theme.status_ready)
            live.update(self._ui.build_layout())

            while True:
                self._ui.set_status(theme.status_ready)
                live.update(self._ui.build_layout())

                live.stop()
                try:
                    text = session.prompt(
                        [("class:prompt", f"{theme.prompt_symbol} ")],
                    ).strip()
                except (EOFError, KeyboardInterrupt):
                    self._ui.add_system_message("AXON: Goodbye.")
                    break
                finally:
                    live.start()

                if not text:
                    continue

                self._ui.add_user_message(text)
                live.update(self._ui.build_layout())

                if text.startswith("/"):
                    if not self._command_manager.handle(text):
                        live.update(self._ui.build_layout())
                        break
                else:
                    self._handle_chat(text, live)

                live.update(self._ui.build_layout())

    def _handle_chat(self, text: str, live: Live) -> None:
        self._ui.set_status("Thinking")
        live.update(self._ui.build_layout())

        result = self._llm_manager.send_message(text)

        if not result.ok:
            self._ui.add_system_message(result.error or "AXON: Unknown error.")
            self._ui.set_status("Error")
            return

        if result.content:
            self._ui.add_assistant_message(result.content)

        if result.usage:
            self._ui.add_system_message(
                f"Tokens — in: {result.usage.prompt_tokens} · "
                f"out: {result.usage.completion_tokens} · "
                f"total: {result.usage.total_tokens}"
            )

        self._ui.set_status(self._ui.theme.status_ready)
