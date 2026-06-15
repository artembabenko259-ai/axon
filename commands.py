from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_client import LLMManager
    from skills.registry import SkillRegistry
    from ui.renderer import UIRenderer


class CommandManager:
    """Handles slash commands routed from the REPL."""

    def __init__(
        self,
        ui: UIRenderer,
        llm_manager: LLMManager,
        skill_registry: SkillRegistry,
    ) -> None:
        self._ui = ui
        self._llm_manager = llm_manager
        self._skill_registry = skill_registry

    def handle(self, command_line: str) -> bool:
        """Process a slash command. Returns False if the REPL should exit."""
        parts = command_line.strip().split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command == "/help":
            self._cmd_help()
        elif command == "/model":
            self._cmd_model(args)
        elif command == "/clear":
            self._cmd_clear()
        elif command == "/skills":
            self._cmd_skills()
        elif command == "/exit":
            self._ui.add_system_message("AXON: Goodbye.")
            return False
        else:
            self._ui.add_system_message(
                f"Unknown command: {command}. Type /help for available commands."
            )
        return True

    def _cmd_help(self) -> None:
        rows = [
            ("/help", "List available commands"),
            ("/model <name>", "Change the active AI model"),
            ("/clear", "Clear the chat pane"),
            ("/skills", "List loaded skills"),
            ("/exit", "Exit the REPL"),
        ]
        self._ui.add_system_message(self._ui.format_help(rows))

    def _cmd_model(self, args: str) -> None:
        name = args.strip()
        if not name:
            self._ui.add_system_message(
                f"Usage: /model <name>\nCurrent model: {self._llm_manager.model}"
            )
            return
        self._llm_manager.set_model(name)
        self._ui.set_model(name)
        self._ui.add_system_message(f"Model switched to {name}")

    def _cmd_clear(self) -> None:
        self._ui.clear_messages()

    def _cmd_skills(self) -> None:
        skills = self._skill_registry.list_skills()
        rows = [(skill.get_name(), skill.get_description()) for skill in skills]
        self._ui.add_system_message(self._ui.format_skills(rows))
