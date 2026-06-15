from __future__ import annotations


def split_command_chain(text: str) -> list[str]:
    """
    Split user input on ``&`` for sequential multi-command execution.

    Respects single and double quotes so ``/plan 'fix a & b'`` stays one command.
    """
    stripped = text.strip()
    if not stripped:
        return []

    if "&" not in stripped:
        return [stripped]

    parts: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    i = 0

    while i < len(stripped):
        ch = stripped[i]

        if quote:
            buf.append(ch)
            if ch == quote and (i == 0 or stripped[i - 1] != "\\"):
                quote = None
            i += 1
            continue

        if ch in "\"'":
            quote = ch
            buf.append(ch)
            i += 1
            continue

        if ch == "&":
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)

    return parts if len(parts) > 1 else [stripped]


def is_command_chain(text: str) -> bool:
    return len(split_command_chain(text)) > 1
