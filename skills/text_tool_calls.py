"""Parse tool calls that some models emit as plain text instead of native tool_calls."""

from __future__ import annotations

import json
import re
from typing import Any

# Gemma / legacy: tool_call=call:name[key:='|*>value<*|',task_id:2]=tool_call
_TEXT_TOOL_CALL_RE = re.compile(
    r"<?tool_call=call:(?P<name>[a-zA-Z_][\w]*)"
    r"\[(?P<args>[^\]]*)\]"
    r"(?:=tool_call)?>?",
    re.IGNORECASE,
)
_TOOL_CALL_TAG_RE = re.compile(r"</?tool_call\s*/?>", re.IGNORECASE)
_TOOL_CALL_JUNK_RE = re.compile(r"(?:=+\|=?)+|(?:\|=?)+", re.IGNORECASE)

_ARG_QUOTED_RE = re.compile(
    r"(?P<key>\w+)\s*:?=?\s*'\s*(?P<val>.*?)\s*'",
    re.DOTALL,
)
_ARG_NUMERIC_RE = re.compile(r"(?P<key>\w+)\s*:\s*(?P<val>\d+)\b")


def _clean_arg_value(raw: str) -> str:
    return raw.replace("|*>", "").replace("<*|", "").strip()


def _parse_bracket_args(args_str: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    cleaned = args_str.replace("|*>", "").replace("<*|", "")
    for match in _ARG_QUOTED_RE.finditer(cleaned):
        key = match.group("key")
        if key not in result:
            result[key] = _clean_arg_value(match.group("val"))
    for match in _ARG_NUMERIC_RE.finditer(cleaned):
        key = match.group("key")
        if key not in result:
            result[key] = int(match.group("val"))
    return result


def extract_text_tool_calls(content: str) -> tuple[str, list[dict[str, Any]]]:
    """Return (cleaned_text, OpenAI-style tool_calls) from pseudo markup."""
    if not content or "tool_call" not in content.lower():
        return content, []

    calls: list[dict[str, Any]] = []
    for index, match in enumerate(_TEXT_TOOL_CALL_RE.finditer(content)):
        name = match.group("name")
        args = _parse_bracket_args(match.group("args"))
        calls.append(
            {
                "id": f"text_call_{index}",
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(args, ensure_ascii=False),
                },
            }
        )

    if not calls:
        return content, []

    cleaned = _TEXT_TOOL_CALL_RE.sub("", content)
    cleaned = _TOOL_CALL_TAG_RE.sub("", cleaned)
    cleaned = _TOOL_CALL_JUNK_RE.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if cleaned and not re.search(r"[\w\u0400-\u04ff]", cleaned):
        cleaned = ""
    return cleaned, calls


def strip_text_tool_calls(content: str) -> str:
    """Remove pseudo tool-call markup for live chat display."""
    cleaned, _ = extract_text_tool_calls(content)
    return cleaned
