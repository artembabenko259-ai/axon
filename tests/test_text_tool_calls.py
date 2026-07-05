"""Tests for pseudo text tool-call parsing (Gemma-style)."""

from __future__ import annotations

import json

from skills.text_tool_calls import extract_text_tool_calls, strip_text_tool_calls


def test_extract_gemma_style_tool_chain():
    raw = (
        "<tool_call=call:update_task_status[status:='|*>in-progress<*|',task_id:2]"
        "=tool_call=|=tool_call=call:take_screenshot[purpose:='|*>Capture Shrek<*|']>"
        "<tool_call/>"
    )
    cleaned, calls = extract_text_tool_calls(raw)
    assert len(calls) == 2
    assert calls[0]["function"]["name"] == "update_task_status"
    assert calls[1]["function"]["name"] == "take_screenshot"
    args0 = json.loads(calls[0]["function"]["arguments"])
    args1 = json.loads(calls[1]["function"]["arguments"])
    assert args0["status"] == "in-progress"
    assert args0["task_id"] == 2
    assert args1["purpose"] == "Capture Shrek"
    assert "tool_call" not in cleaned.lower()


def test_strip_for_display():
    raw = "Done.<tool_call=call:take_screenshot[purpose:='x']>"
    assert strip_text_tool_calls(raw) == "Done."


def test_no_false_positive():
    text = "explain tool_call handling in Python"
    cleaned, calls = extract_text_tool_calls(text)
    assert calls == []
    assert cleaned == text
