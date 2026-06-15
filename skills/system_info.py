from __future__ import annotations

import platform
from datetime import datetime
from typing import Any

from skills.base import BaseSkill


class SystemInfoSkill(BaseSkill):
    """Returns basic system information."""

    def get_name(self) -> str:
        return "system_info"

    def get_description(self) -> str:
        return (
            "Returns basic system information including operating system, "
            "machine architecture, Python version, and current local time."
        )

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def execute(self, args: dict[str, Any]) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"OS: {platform.system()} {platform.release()}\n"
            f"Machine: {platform.machine()}\n"
            f"Python: {platform.python_version()}\n"
            f"Local time: {now}"
        )
