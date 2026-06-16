from __future__ import annotations

import unittest

from context_optimizer import (
    compose_system_prompt,
    prepare_messages_for_api,
    should_auto_compact,
    trim_stale_tool_messages,
)


class ContextOptimizerTests(unittest.TestCase):
    def test_compose_system_prompt_splits_static_and_dynamic(self) -> None:
        text = compose_system_prompt("STATIC", "dynamic block")
        self.assertIn("STATIC", text)
        self.assertIn("dynamic block", text)
        self.assertIn("---AXON_DYNAMIC---", text)

    def test_trim_stale_tool_messages_shortens_old_tool_output(self) -> None:
        big = "x" * 13000
        messages: list[dict[str, str]] = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ]
        for index in range(8):
            messages.append(
                {
                    "role": "tool",
                    "content": big if index < 6 else "fresh",
                    "tool_call_id": str(index),
                }
            )
        trimmed = trim_stale_tool_messages(messages)
        self.assertIn("[AXON trimmed older tool output", trimmed[2]["content"])
        self.assertEqual(trimmed[-1]["content"], "fresh")

    def test_prepare_messages_adds_cache_control_for_claude(self) -> None:
        system = compose_system_prompt("Stable AXON rules", "Session notes")
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "again"},
        ]
        prepared = prepare_messages_for_api(
            messages,
            model="anthropic/claude-3.5-sonnet",
            prompt_cache_enabled=True,
        )
        system_content = prepared[0]["content"]
        self.assertIsInstance(system_content, list)
        assert isinstance(system_content, list)
        self.assertEqual(system_content[0]["cache_control"], {"type": "ephemeral"})

    def test_should_auto_compact_on_large_history(self) -> None:
        messages = [{"role": "user", "content": "x" * 40000} for _ in range(10)]
        messages.insert(0, {"role": "system", "content": "sys"})
        self.assertTrue(should_auto_compact(messages))


if __name__ == "__main__":
    unittest.main()
