from __future__ import annotations

import asyncio
import uuid
from typing import Literal

ApprovalDecision = Literal["once", "session", "deny"]

_pending: dict[str, asyncio.Future[ApprovalDecision]] = {}


def create_approval_waiter() -> tuple[str, asyncio.Future[ApprovalDecision]]:
    approval_id = uuid.uuid4().hex[:12]
    loop = asyncio.get_running_loop()
    future: asyncio.Future[ApprovalDecision] = loop.create_future()
    _pending[approval_id] = future
    return approval_id, future


def resolve_approval(approval_id: str, decision: str) -> bool:
    future = _pending.pop(approval_id, None)
    if future is None or future.done():
        return False
    normalized: ApprovalDecision
    if decision == "session":
        normalized = "session"
    elif decision in {"deny", "reject", "3"}:
        normalized = "deny"
    else:
        normalized = "once"
    future.set_result(normalized)
    return True


def cancel_approval(approval_id: str) -> None:
    future = _pending.pop(approval_id, None)
    if future and not future.done():
        future.set_result("deny")
