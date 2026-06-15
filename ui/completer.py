from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

AXON_COMMANDS: dict[str, str] = {
    "/help": "List available commands",
    "/model": "Switch model — usage: /model <name>",
    "/clear": "Clear chat history and reset cost",
    "/status": "Show model, cost, and session info",
    "/exit": "Exit AXON",
}


class AxonCommandCompleter(Completer):
    """Slash-command completer — Tab to complete, ↑↓ to navigate menu."""

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        if not text.startswith("/"):
            return

        if " " in text.strip() and not text.strip().startswith("/model"):
            return

        word = text.split()[-1] if text.endswith(" ") else text

        for command, description in AXON_COMMANDS.items():
            if command.startswith(word):
                yield Completion(
                    command,
                    start_position=-len(word),
                    display=command,
                    display_meta=description,
                )

        if word.startswith("/mod") and "/model" not in word:
            yield Completion(
                "/model ",
                start_position=-len(word),
                display="/model ",
                display_meta=AXON_COMMANDS["/model"],
            )
