from __future__ import annotations

import contextvars

_request_source: contextvars.ContextVar[str] = contextvars.ContextVar(
    "axon_request_source",
    default="terminal",
)


def set_request_source(source: str) -> contextvars.Token[str]:
    return _request_source.set(source if source in {"web", "terminal"} else "terminal")


def reset_request_source(token: contextvars.Token[str]) -> None:
    _request_source.reset(token)


def get_request_source() -> str:
    return _request_source.get()
