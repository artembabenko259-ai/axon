from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    """Abstract base class for CLI skills exposed as LLM tools."""

    @abstractmethod
    def get_name(self) -> str:
        """Return the stable tool identifier."""

    @abstractmethod
    def get_description(self) -> str:
        """Return a description for the LLM."""

    @abstractmethod
    def get_parameters_schema(self) -> dict[str, Any]:
        """Return JSON Schema for function arguments."""

    @abstractmethod
    def execute(self, args: dict[str, Any]) -> str:
        """Execute the skill and return a string result."""
