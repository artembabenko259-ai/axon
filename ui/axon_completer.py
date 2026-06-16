from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion, PathCompleter
from prompt_toolkit.document import Document

from ui.completer import AxonCommandCompleter

_path_completer = PathCompleter(expanduser=True, only_directories=False)


def _active_at_token(text: str) -> bool:
    """True when cursor is in a Cursor-style @file token (not email@host)."""
    if "@" not in text:
        return False
    at_index = text.rfind("@")
    tail = text[at_index + 1 :]
    if " " in tail or "\t" in tail or "\n" in tail:
        return False
    if at_index > 0:
        prev = text[at_index - 1]
        if prev.isalnum() or prev in "._-+":
            return False
    return True


class AtPathCompleter(Completer):
    """Complete file paths after `@` — Cursor-style file references."""

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        if not _active_at_token(text):
            return

        at_index = text.rfind("@")
        prefix = text[at_index + 1 :]

        sub_document = Document(prefix, len(prefix))
        for completion in _path_completer.get_completions(sub_document, complete_event):
            display = f"@{completion.text}"
            meta = completion.display_meta or "path"
            yield Completion(
                completion.text,
                start_position=-len(prefix),
                display=display,
                display_meta=meta,
            )


class AxonInputCompleter(Completer):
    """Slash commands (`/`) and file references (`@`) while typing."""

    def __init__(self) -> None:
        self._slash = AxonCommandCompleter()
        self._at_paths = AtPathCompleter()

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        if _active_at_token(text):
            yield from self._at_paths.get_completions(document, complete_event)
            return

        stripped = text.lstrip()
        if stripped.startswith("/"):
            yield from self._slash.get_completions(document, complete_event)


def build_axon_completer() -> AxonInputCompleter:
    return AxonInputCompleter()
