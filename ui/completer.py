from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit.document import Document

SLASH_COMMANDS = [
    "/help",
    "/exit",
    "/clear",
    "/cost",
    "/usage",
    "/compact",
    "/model",
    "/plan",
]

AXON_COMMANDS: dict[str, str] = {
    "/help": "List available slash commands",
    "/exit": "Exit AXON",
    "/clear": "Clear chat context (keeps system prompt)",
    "/cost": "Show session cost and token usage",
    "/usage": "Alias for /cost",
    "/compact": "Compact conversation context (coming soon)",
    "/model": "Switch model — e.g. /model anthropic/claude-3.5-sonnet",
    "/plan": "Plan Mode — /plan <description> to break work into steps",
}


def build_slash_completer() -> WordCompleter:
    return WordCompleter(SLASH_COMMANDS, ignore_case=True)


class AxonCommandCompleter(Completer):
    """Slash-command completer with descriptions — Tab to complete."""

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        if not text.startswith("/"):
            return

        if " " in text.strip() and not text.strip().startswith(("/model", "/plan")):
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

        if word.startswith("/pla") and "/plan" not in word:
            yield Completion(
                "/plan ",
                start_position=-len(word),
                display="/plan ",
                display_meta=AXON_COMMANDS["/plan"],
            )

        if word.startswith("/mod") and "/model" not in word:
            yield Completion(
                "/model ",
                start_position=-len(word),
                display="/model ",
                display_meta=AXON_COMMANDS["/model"],
            )
