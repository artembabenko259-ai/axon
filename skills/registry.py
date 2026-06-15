from __future__ import annotations

from typing import Any

from skills.base import BaseSkill
from skills.file_read import FileReadSkill
from skills.system_info import SystemInfoSkill


class SkillRegistry:
    """Registry for loaded skills with OpenAI tools schema generation."""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for skill in (SystemInfoSkill(), FileReadSkill()):
            self.register(skill)

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.get_name()] = skill

    def list_skills(self) -> list[BaseSkill]:
        return list(self._skills.values())

    def get_tools_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": skill.get_name(),
                    "description": skill.get_description(),
                    "parameters": skill.get_parameters_schema(),
                },
            }
            for skill in self._skills.values()
        ]

    def execute(self, name: str, args: dict[str, Any]) -> str:
        skill = self._skills.get(name)
        if skill is None:
            return f"Error: unknown skill '{name}'."
        try:
            return skill.execute(args)
        except Exception as exc:
            return f"Error executing skill '{name}': {exc}"
