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
    "/image",
    "/create-skill",
    "/review",
    "/undo",
    "/commit",
    "/docs",
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
    "/image": "Load image for vision — /image <path> [prompt]",
    "/create-skill": "Interactive wizard to create a new SKILL.md",
    "/review": "Review current git diff for bugs and code smells",
    "/undo": "Restore last file overwritten by write_file",
    "/commit": "AI-generated Conventional Commit with confirmation",
    "/docs": "Generate and serve interactive project docs at localhost:8000",
}


def build_slash_completer() -> WordCompleter:
    return WordCompleter(SLASH_COMMANDS, ignore_case=True)


class AxonCommandCompleter(Completer):
    """Slash-command completer with descriptions — Tab to complete."""

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        if not text.startswith("/"):
            return

        if " " in text.strip() and not text.strip().startswith(
            ("/model", "/plan", "/image")
        ):
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

        if word.startswith("/doc") and "/docs" not in word:
            yield Completion(
                "/docs",
                start_position=-len(word),
                display="/docs",
                display_meta=AXON_COMMANDS["/docs"],
            )

        if word.startswith("/com") and "/commit" not in word:
            yield Completion(
                "/commit",
                start_position=-len(word),
                display="/commit",
                display_meta=AXON_COMMANDS["/commit"],
            )

        if word.startswith("/und") and "/undo" not in word:
            yield Completion(
                "/undo",
                start_position=-len(word),
                display="/undo",
                display_meta=AXON_COMMANDS["/undo"],
            )

        if word.startswith("/cre") and "/create-skill" not in word:
            yield Completion(
                "/create-skill",
                start_position=-len(word),
                display="/create-skill",
                display_meta=AXON_COMMANDS["/create-skill"],
            )

        if word.startswith("/rev") and "/review" not in word:
            yield Completion(
                "/review",
                start_position=-len(word),
                display="/review",
                display_meta=AXON_COMMANDS["/review"],
            )

        if word.startswith("/ima") and "/image" not in word:
            yield Completion(
                "/image ",
                start_position=-len(word),
                display="/image ",
                display_meta=AXON_COMMANDS["/image"],
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
