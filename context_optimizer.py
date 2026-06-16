"""Token-saving helpers: prompt cache markers, tool-history trim, size estimates."""

from __future__ import annotations

import copy
import json
from typing import Any

DYNAMIC_SYSTEM_DELIMITER = "\n\n---AXON_DYNAMIC---\n\n"

MAX_TOOL_RESULT_CHARS = 12_000
TOOL_RESULT_SUMMARY_CHARS = 480
KEEP_FULL_TOOL_RESULTS = 6
AUTO_COMPACT_MESSAGE_COUNT = 36
AUTO_COMPACT_CHAR_ESTIMATE = 90_000


def estimate_messages_chars(messages: list[dict[str, Any]]) -> int:
    total = 0
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            total += len(json.dumps(content, ensure_ascii=False))
        tool_calls = msg.get("tool_calls")
        if tool_calls:
            total += len(json.dumps(tool_calls, ensure_ascii=False))
    return total


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    return max(estimate_messages_chars(messages) // 4, 1)


def should_auto_compact(messages: list[dict[str, Any]]) -> bool:
    if len(messages) <= 8:
        return False
    if len(messages) >= AUTO_COMPACT_MESSAGE_COUNT:
        return True
    return estimate_messages_chars(messages) >= AUTO_COMPACT_CHAR_ESTIMATE


def _cache_control_block() -> dict[str, str]:
    return {"type": "ephemeral"}


def _supports_prompt_cache(model: str) -> bool:
    lowered = model.lower()
    if any(
        token in lowered
        for token in (
            "claude",
            "anthropic",
            "gemini",
            "google/",
            "openai/gpt-4",
            "openai/gpt-5",
            "openai/o1",
            "openai/o3",
            "openai/o4",
        )
    ):
        return True
    return False


def _text_content_block(text: str, *, cache: bool = False) -> dict[str, Any]:
    block: dict[str, Any] = {"type": "text", "text": text}
    if cache:
        block["cache_control"] = _cache_control_block()
    return block


def _with_cache_on_text_message(msg: dict[str, Any]) -> dict[str, Any]:
    out = dict(msg)
    content = out.get("content")
    if isinstance(content, str) and content.strip():
        out["content"] = [_text_content_block(content, cache=True)]
    elif isinstance(content, list):
        copied = copy.deepcopy(content)
        for block in reversed(copied):
            if isinstance(block, dict) and block.get("type") == "text":
                block["cache_control"] = _cache_control_block()
                break
        out["content"] = copied
    return out


def _split_system_for_cache(content: str) -> list[dict[str, Any]]:
    if DYNAMIC_SYSTEM_DELIMITER in content:
        static, dynamic = content.split(DYNAMIC_SYSTEM_DELIMITER, 1)
        blocks = [_text_content_block(static, cache=True)]
        if dynamic.strip():
            blocks.append(_text_content_block(dynamic.strip()))
        return blocks
    return [_text_content_block(content, cache=True)]


def _summarize_tool_content(content: str) -> str:
    text = content.strip()
    if len(text) <= TOOL_RESULT_SUMMARY_CHARS:
        return text
    head = text[:TOOL_RESULT_SUMMARY_CHARS].rstrip()
    omitted = len(text) - TOOL_RESULT_SUMMARY_CHARS
    return (
        f"{head}\n\n"
        f"[AXON trimmed older tool output — {omitted} chars omitted to save tokens]"
    )


def trim_stale_tool_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a copy with older tool results shortened (keeps recent tool turns full)."""
    tool_indexes = [
        index for index, msg in enumerate(messages) if msg.get("role") == "tool"
    ]
    if len(tool_indexes) <= KEEP_FULL_TOOL_RESULTS:
        return messages

    trim_before = set(tool_indexes[: -KEEP_FULL_TOOL_RESULTS])
    if not trim_before:
        return messages

    trimmed: list[dict[str, Any]] = []
    for index, msg in enumerate(messages):
        if index not in trim_before:
            trimmed.append(msg)
            continue
        content = msg.get("content")
        if not isinstance(content, str) or len(content) <= MAX_TOOL_RESULT_CHARS:
            trimmed.append(msg)
            continue
        copy_msg = dict(msg)
        copy_msg["content"] = _summarize_tool_content(content)
        trimmed.append(copy_msg)
    return trimmed


def prepare_messages_for_api(
    messages: list[dict[str, Any]],
    *,
    model: str,
    prompt_cache_enabled: bool = True,
    trim_tool_history: bool = True,
) -> list[dict[str, Any]]:
    """Build API payload: optional cache markers + trim stale tool output."""
    payload = copy.deepcopy(messages)
    if trim_tool_history:
        payload = trim_stale_tool_messages(payload)

    if not prompt_cache_enabled or not _supports_prompt_cache(model):
        return payload

    prepared: list[dict[str, Any]] = []
    for index, msg in enumerate(payload):
        role = msg.get("role")
        if index == 0 and role == "system":
            content = msg.get("content")
            if isinstance(content, str):
                system_msg = dict(msg)
                system_msg["content"] = _split_system_for_cache(content)
                prepared.append(system_msg)
                continue
        prepared.append(msg)

    # Prefix-cache stable conversation up to the latest user turn.
    last_user = max(
        (i for i, msg in enumerate(prepared) if msg.get("role") == "user"),
        default=-1,
    )
    if last_user > 0:
        cache_index = last_user - 1
        prepared[cache_index] = _with_cache_on_text_message(prepared[cache_index])

    return prepared


def compose_system_prompt(static: str, dynamic: str) -> str:
    """Join stable (cacheable) and dynamic system instructions."""
    static_text = static.strip()
    dynamic_text = dynamic.strip()
    if dynamic_text:
        return f"{static_text}{DYNAMIC_SYSTEM_DELIMITER}{dynamic_text}"
    return static_text
