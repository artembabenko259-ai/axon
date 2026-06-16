from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from orchestrator import Orchestrator, SubTask, _extract_json


def test_extract_json_from_fence() -> None:
    raw = 'Here you go:\n```json\n{"subtasks": [{"title": "A", "agent": "axon", "task": "do a"}]}\n```'
    data = _extract_json(raw)
    assert isinstance(data, dict)
    assert len(data["subtasks"]) == 1


def test_parse_multitask_command_basic() -> None:
    orch = Orchestrator(llm=MagicMock(), workspace=Path("."))
    goal, agents = orch.parse_command("/multitask review auth and write tests")
    assert goal == "review auth and write tests"
    assert agents == []


def test_parse_multitask_command_with_agents() -> None:
    orch = Orchestrator(llm=MagicMock(), workspace=Path("."))
    goal, agents = orch.parse_command(
        "/multitask --agents reviewer,test-writer audit module and add tests"
    )
    assert goal == "audit module and add tests"
    assert agents == ["reviewer", "test-writer"]


def test_normalize_unknown_agent_to_axon() -> None:
    orch = Orchestrator(llm=MagicMock(), workspace=Path("."))
    items = [{"title": "T", "agent": "missing-agent", "task": "work"}]
    subtasks = orch._normalize_subtasks(items, available=[], preferred=[])
    assert len(subtasks) == 1
    assert subtasks[0].agent == "axon"


@pytest.mark.asyncio
async def test_run_empty_goal() -> None:
    orch = Orchestrator(llm=MagicMock(), workspace=Path("."))
    result = await orch.run("")
    assert not result.ok
    assert result.error
