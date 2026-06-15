from __future__ import annotations

import os
from pathlib import Path

from rich import box
from rich.align import Align
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text

from ui.branding import APP_NAME, INSTRUCTIONS, VERSION, build_gradient_logo
from ui.theme import CLITheme

HISTORY_PATH = Path.home() / ".axon_history"

WELCOME_TIPS: tuple[tuple[str, str], ...] = (
    ("@path", "Attach files or directories to your prompt"),
    ("/plan", "Decompose complex tasks into tracked steps"),
    ("Shift+Tab", "Review recent tool executions"),
    ("/model", "Hot-swap models without restarting"),
    ("/docs", "Generate and serve project documentation"),
)

AXON_GLYPH = """\
 +------+
 |  <>  |  AXON
 +------+"""

_PANEL_BOX = box.ASCII if os.name == "nt" else box.ROUNDED
_RULE_CHAR = "-" if os.name == "nt" else "─"


def should_show_welcome() -> bool:
    return os.environ.get("AXON_NO_SPLASH", "").strip().lower() not in {
        "1",
        "true",
        "yes",
    }


def _username() -> str:
    return (
        os.environ.get("USERNAME")
        or os.environ.get("USER")
        or os.environ.get("LOGNAME")
        or "there"
    )


def _compact_path(path: Path, max_len: int = 44) -> str:
    text = str(path)
    if len(text) <= max_len:
        return text
    return f"…{text[-(max_len - 1) :]}"


def _load_recent_history(limit: int = 4) -> list[str]:
    if not HISTORY_PATH.exists():
        return []

    entries: list[str] = []
    try:
        for raw in HISTORY_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if len(line) > 72:
                line = f"{line[:69]}…"
            entries.append(line)
    except OSError:
        return []

    if not entries:
        return []

    deduped: list[str] = []
    for item in entries:
        if deduped and deduped[-1] == item:
            continue
        deduped.append(item)
    return deduped[-limit:]


def _panel_border(theme: CLITheme) -> str:
    return theme.accent


def _build_welcome_column(theme: CLITheme, model: str, workspace: Path) -> RenderableType:
    short_model = model.rsplit("/", 1)[-1]
    provider = model.split("/", 1)[0] if "/" in model else "default"

    body = Text()
    body.append("Welcome back ", style=Style(color=theme.text_muted))
    body.append(f"{_username()}!\n\n", style=Style(color=theme.text_primary, bold=True))
    body.append(AXON_GLYPH, style=Style(color=theme.accent_soft))
    body.append("\n\n", style=Style())
    body.append("Model\n", style=Style(color=theme.text_muted))
    body.append(f"{short_model}\n", style=Style(color=theme.accent_soft, bold=True))
    body.append(f"{provider}\n\n", style=Style(color=theme.text_muted, dim=True))
    body.append("Workspace\n", style=Style(color=theme.text_muted))
    body.append(f"{_compact_path(workspace)}\n\n", style=Style(color=theme.text_primary))
    body.append("Bridge\n", style=Style(color=theme.text_muted))
    body.append("ws://localhost:8765\n", style=Style(color=theme.success))

    return Panel(
        body,
        title=f"[{theme.accent}]{APP_NAME}[/]",
        border_style=_panel_border(theme),
        box=_PANEL_BOX,
        padding=(1, 2),
    )


def _build_tips_column(theme: CLITheme) -> RenderableType:
    tips = Text()
    tips.append("Tips for getting started\n\n", style=Style(color=theme.accent_soft, bold=True))
    for key, desc in WELCOME_TIPS:
        tips.append(f"  {key:<12}", style=Style(color=theme.accent))
        tips.append(f"{desc}\n", style=Style(color=theme.text_muted))

    recent = _load_recent_history()
    tips.append("\nRecent activity\n\n", style=Style(color=theme.accent_soft, bold=True))
    if recent:
        for line in recent:
            tips.append("  * ", style=Style(color=theme.border_subtle))
            tips.append(f"{line}\n", style=Style(color=theme.text_primary))
    else:
        tips.append("  No recent activity\n", style=Style(color=theme.text_muted, italic=True))
        tips.append(
            "  Run a prompt or /help to begin\n",
            style=Style(color=theme.text_muted, italic=True),
        )

    logo = build_gradient_logo(theme, font="small")
    return Panel(
        Group(Align.right(logo), Text(""), tips),
        title="[dim]Session[/]",
        border_style=_panel_border(theme),
        box=_PANEL_BOX,
        padding=(1, 2),
    )


def build_welcome_screen(
    theme: CLITheme,
    *,
    model: str,
    workspace: Path,
) -> RenderableType:
    """Structured startup screen — dashboard-style, AXON-branded."""
    header = Text()
    header.append(f"{APP_NAME} ", style=Style(color=theme.text_primary, bold=True))
    header.append(f"v{VERSION}", style=Style(color=theme.accent_soft))

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_row(
        _build_welcome_column(theme, model, workspace),
        _build_tips_column(theme),
    )

    footer_hint = Text(
        '/model to switch · @file for context · Type "?" in prompt for shortcuts',
        style=Style(color=theme.text_muted, italic=True),
        justify="center",
    )
    instructions = Text(
        INSTRUCTIONS,
        style=Style(color=theme.text_muted),
        justify="center",
    )

    return Group(
        Align.left(header),
        Rule(style=Style(color=theme.accent), characters=_RULE_CHAR),
        Text(""),
        grid,
        Text(""),
        Rule(style=Style(color=theme.border_subtle), characters=_RULE_CHAR),
        footer_hint,
        instructions,
    )
