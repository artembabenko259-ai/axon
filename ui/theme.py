from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CLITheme:
    """Color palette and style tokens. Swap this class to change the look."""

    background: str = "#121212"
    surface: str = "#1a1a1a"
    border_subtle: str = "#333333"
    text_primary: str = "#d4d4d4"
    text_muted: str = "#525252"
    accent: str = "#a3a3a3"
    accent_soft: str = "#737373"
    user_prompt: str = "#e5e5e5"
    system: str = "#737373"
    error: str = "#ef4444"
    success: str = "#a3a3a3"
    warning: str = "#737373"
    prompt_symbol: str = "❯"
    status_ready: str = "READY"
    status_thinking: str = "THINKING"
    toolbar_bg: str = "#171717"
    toolbar_text: str = "#737373"
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
