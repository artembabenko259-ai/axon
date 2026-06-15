from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion, PathCompleter, WordCompleter
from prompt_toolkit.document import Document

from ui.completer import SLASH_COMMANDS

_slash_completer = WordCompleter(SLASH_COMMANDS, ignore_case=True)
_path_completer = PathCompleter(expanduser=True)


class AtPathCompleter(Completer):
    """Complete file paths after `@` in the input line."""

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        if "@" not in text:
            return

        at_index = text.rfind("@")
        prefix = text[at_index + 1 :]
        if not prefix or " " in prefix or "\t" in prefix:
            return

        sub_document = Document(prefix, len(prefix))
        for completion in _path_completer.get_completions(sub_document, complete_event):
            yield Completion(
                completion.text,
                start_position=-len(prefix),
                display=f"@{completion.text}",
                display_meta=completion.display_meta,
            )


class AxonInputCompleter(Completer):
    """Slash commands when line starts with `/`, else `@` path completion."""

    def __init__(self) -> None:
        self._at_paths = AtPathCompleter()

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        stripped = text.lstrip()

        if stripped.startswith("/"):
            yield from _slash_completer.get_completions(document, complete_event)
            return

        if "@" in text:
            yield from self._at_paths.get_completions(document, complete_event)


def build_axon_completer() -> AxonInputCompleter:
    return AxonInputCompleter()
