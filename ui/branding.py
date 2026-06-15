from __future__ import annotations

import pyfiglet
from rich.align import Align
from rich.console import Group, RenderableType
from rich.rule import Rule
from rich.style import Style
from rich.text import Text

from ui.theme import CLITheme

APP_NAME = "AXON"
VERSION = "1.0.0"
INSTRUCTIONS = "Type /help for commands • /exit to quit"
LOGO_FONTS = ("slant", "small")


def _interpolate_color(ratio: float, start: tuple[int, int, int], end: tuple[int, int, int]) -> str:
    ratio = max(0.0, min(1.0, ratio))
    channels = tuple(
        int(start[i] + (end[i] - start[i]) * ratio) for i in range(3)
    )
    return f"#{channels[0]:02x}{channels[1]:02x}{channels[2]:02x}"


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def generate_logo_text(font: str = "slant") -> str:
    try:
        return pyfiglet.figlet_format(APP_NAME, font=font)
    except pyfiglet.FontNotFound:
        return pyfiglet.figlet_format(APP_NAME, font="small")


def build_gradient_logo(theme: CLITheme, font: str = "slant") -> Text:
    """Render the AXON ASCII logo with a subtle vertical gradient."""
    raw = generate_logo_text(font)
    lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
    if not lines:
        lines = [APP_NAME]

    start = _hex_to_rgb(theme.text_muted)
    end = _hex_to_rgb(theme.accent_soft)
    total = max(len(lines) - 1, 1)

    logo = Text()
    for index, line in enumerate(lines):
        ratio = index / total
        color = _interpolate_color(ratio, start, end)
        logo.append(line, style=Style(color=color))
        if index < len(lines) - 1:
            logo.append("\n")

    return logo


def build_status_line(theme: CLITheme, model: str, status: str) -> Text:
    line = Text()
    line.append("Version: ", style=Style(color=theme.text_muted))
    line.append(VERSION, style=Style(color=theme.text_primary))
    line.append(" │ ", style=Style(color=theme.border_subtle))
    line.append("Model: ", style=Style(color=theme.text_muted))
    line.append(model or "—", style=Style(color=theme.accent_soft))
    line.append(" │ ", style=Style(color=theme.border_subtle))
    line.append("Status: ", style=Style(color=theme.text_muted))
    line.append(status, style=Style(color=_status_color(theme, status)))
    return line


def _status_color(theme: CLITheme, status: str) -> str:
    lowered = status.lower()
    if lowered in {"ready", "idle"}:
        return theme.success
    if "stream" in lowered or "think" in lowered:
        return theme.accent_soft
    if "running" in lowered or "skill" in lowered:
        return theme.warning
    if "error" in lowered:
        return theme.error
    return theme.text_primary


def build_header(
    theme: CLITheme,
    model: str,
    status: str,
    font: str = "slant",
) -> tuple[RenderableType, int]:
    """Build the static header block and return its layout height."""
    logo = build_gradient_logo(theme, font=font)
    status_line = build_status_line(theme, model, status)
    instructions = Text(
        INSTRUCTIONS,
        style=Style(color=theme.text_muted, italic=True),
        justify="center",
    )

    header = Group(
        Align.center(logo),
        Text(""),
        Align.center(status_line),
        Rule(style=Style(color=theme.border_subtle), characters="─"),
        Align.center(instructions),
    )
    height = len(logo.plain.splitlines()) + 5
    return header, height


def splash_renderable(
    theme: CLITheme,
    model: str,
    status: str = "Ready",
    font: str = "slant",
) -> RenderableType:
    """Full startup splash for initial screen clear."""
    header, _ = build_header(theme, model, status, font=font)
    return Align.center(header, vertical="middle")
