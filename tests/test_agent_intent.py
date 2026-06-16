"""Tests for natural-language plan / multitask routing."""

from ui.agent_intent import detect_intent


def test_slash_plan():
    assert detect_intent("/plan refactor auth") == "plan"


def test_slash_multitask():
    assert detect_intent("/multitask fix bugs and add tests") == "multitask"


def test_natural_plan_uk():
    assert detect_intent("составь план для рефакторинга") == "plan"


def test_natural_multitask_ru():
    assert detect_intent("сделай параллельно ревью и тесты") == "multitask"


def test_execute_when_plan_active():
    assert detect_intent("выполни план", has_active_plan=True) == "execute"


def test_plain_chat():
    assert detect_intent("как дела?") == "chat"


def test_parallel_wins_when_both():
    assert detect_intent("составь план и запусти параллельно агентов") == "multitask"
