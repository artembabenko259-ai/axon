"""Headless AXON execution for scripts and CI."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from config_store import get_model, save_model
from llm_client import LLMManager
from runtime_policy import load_runtime_policy
from skills.tools import ApprovalDecision, clear_session_approvals


async def _headless_approve(
    tool_name: str,
    detail: str,
    *,
    auto_approve: bool,
) -> ApprovalDecision:
    policy = load_runtime_policy()
    if policy.autonomy_enabled or auto_approve:
        return "once"
    print(
        f"AXON: approval required for {tool_name}: {detail}",
        file=sys.stderr,
    )
    return "deny"


async def run_headless_async(
    prompt: str,
    *,
    model: str | None = None,
    json_output: bool = False,
    auto_approve: bool = False,
) -> tuple[int, str]:
    text = prompt.strip()
    if not text:
        return 1, "AXON: empty prompt"

    clear_session_approvals()
    llm_manager = LLMManager(workspace=Path.cwd())

    if model:
        llm_manager.set_model(model)
    elif not get_model():
        save_model(llm_manager.model)

    async def approve(tool: str, detail: str) -> ApprovalDecision:
        return await _headless_approve(tool, detail, auto_approve=auto_approve)

    llm_manager.set_approval_callback(approve)
    result = await llm_manager.send_message_async(text)

    if json_output:
        payload = {
            "ok": result.ok,
            "content": result.content,
            "error": result.error,
            "model": result.model,
            "tool_steps": result.tool_steps,
        }
        return (0 if result.ok else 1), json.dumps(payload, ensure_ascii=False, indent=2)

    if result.ok:
        return 0, result.content or ""
    return 1, result.display_text


def run_headless(
    prompt: str,
    *,
    model: str | None = None,
    json_output: bool = False,
    auto_approve: bool = False,
) -> int:
    code, output = asyncio.run(
        run_headless_async(
            prompt,
            model=model,
            json_output=json_output,
            auto_approve=auto_approve,
        )
    )
    print(output)
    return code
