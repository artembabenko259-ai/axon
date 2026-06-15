from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CLITheme:
    """Color palette and style tokens. Swap this class to change the look."""

    background: str = "#1e1e2e"
    surface: str = "#2a2a3d"
    border_subtle: str = "#3d3d5c"
    text_primary: str = "#e2e8f0"
    text_muted: str = "#64748b"
    accent: str = "#22d3ee"
    accent_soft: str = "#67e8f9"
    user_prompt: str = "#f8fafc"
    system: str = "#94a3b8"
    error: str = "#f87171"
    success: str = "#4ade80"
    warning: str = "#fbbf24"
    prompt_symbol: str = "❯"
    status_ready: str = "READY"
    status_thinking: str = "THINKING"
    toolbar_bg: str = "#050505"
    toolbar_text: str = "#3f3f46"
    font_dim: str = "dim"

    @property
    def assistant_label(self) -> str:
        return f"[bold {self.accent}]✦ AXON[/]"

    @property
    def user_label(self) -> str:
        return f"[bold {self.user_prompt}]❯ You[/]"

    @property
    def prompt_markup(self) -> str:
        return f"[{self.accent}]{self.prompt_symbol}[/]"

    @property
    def toolbar_markup(self) -> str:
        return (
            f"[{self.toolbar_text}] AXON [/] [{self.border_subtle}]│[/] "
            f"[{self.toolbar_text}]Model:[/] [bold {self.accent_soft}]{{model}}[/] [{self.border_subtle}]│[/] "
            f"[{self.toolbar_text}]Cost:[/] [bold {self.success}]${{cost:.4f}}[/] [{self.border_subtle}]│[/] "
            f"[{self.toolbar_text}]Status:[/] [{{status_style}}]{{status}}[/]"
        )


DEFAULT_THEME = CLITheme()
