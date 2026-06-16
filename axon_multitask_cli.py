"""Headless `axon multitask` — orchestrator without REPL."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from llm_client import LLMManager, TOTAL_COST, TOTAL_TOKENS
from orchestrator import Orchestrator, OrchestratorResult, SubTask
from runtime_policy import load_runtime_policy
from skills.tools import ApprovalDecision, clear_session_approvals
from ui.headless import _headless_approve


async def run_multitask_headless_async(
    goal: str,
    *,
    agents: list[str] | None = None,
    json_output: bool = False,
    auto_approve: bool = False,
) -> tuple[int, str]:
    text = goal.strip()
    if not text:
        return 1, "AXON: empty goal"

    clear_session_approvals()
    policy = load_runtime_policy()
    llm = LLMManager(workspace=Path.cwd())

    async def approve(tool: str, detail: str) -> ApprovalDecision:
        return await _headless_approve(tool, detail, auto_approve=auto_approve)

    llm.set_approval_callback(approve)

    orch = Orchestrator(
        llm=llm,
        workspace=Path.cwd(),
        allow_parallel=policy.allow_parallel_agents,
    )

    def _on_progress(message: str) -> None:
        if not json_output:
            print(message, file=sys.stderr)

    result = await orch.run(
        text,
        preferred_agents=agents or [],
        on_progress=_on_progress,
    )

    if json_output:
        payload = _result_to_json(result)
        payload["cost"] = TOTAL_COST
        payload["tokens"] = TOTAL_TOKENS
        return (0 if result.ok else 1), json.dumps(payload, ensure_ascii=False, indent=2)

    if result.error and not result.synthesis:
        return 1, result.error

    body = result.synthesis or ""
    footer = f"\n\n---\nCost: ${TOTAL_COST:.4f} | Tokens: {TOTAL_TOKENS}"
    return 0, body + footer


def _result_to_json(result: OrchestratorResult) -> dict:
    return {
        "ok": result.ok,
        "goal": result.goal,
        "error": result.error,
        "synthesis": result.synthesis,
        "subtasks": [
            {
                "id": t.id,
                "title": t.title,
                "agent": t.agent,
                "status": t.status,
                "result": t.result,
                "error": t.error,
            }
            for t in result.subtasks
        ],
    }


def run_multitask_headless(
    goal: str,
    *,
    agents: list[str] | None = None,
    json_output: bool = False,
    auto_approve: bool = False,
) -> int:
    code, output = asyncio.run(
        run_multitask_headless_async(
            goal,
            agents=agents,
            json_output=json_output,
            auto_approve=auto_approve,
        )
    )
    print(output)
    return code
