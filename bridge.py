from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Awaitable, Callable
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol

from llm_client import SESSION_STARTED_AT, TOTAL_COST, TOTAL_TOKENS
from approval_bridge import resolve_approval
from runtime_policy import (
    load_runtime_policy,
    policy_for_client,
    save_runtime_policy,
    verify_bridge_token,
    RuntimePolicy,
)

WS_HOST = "127.0.0.1"
WS_PORT = 8765
_ADDR_IN_USE = frozenset({48, 98, 10048})

ProcessChatHandler = Callable[[str, str], Awaitable[None]]
SetModelHandler = Callable[[str], Awaitable[None]]
RefreshUIHandler = Callable[[], None]

connected_clients: set[WebSocketServerProtocol] = set()
authenticated_clients: set[WebSocketServerProtocol] = set()


class AxonBridge:
    """WebSocket hub — ws_handler + broadcast helpers."""

    def __init__(self) -> None:
        self._process_chat: ProcessChatHandler | None = None
        self._set_model: SetModelHandler | None = None
        self._refresh_ui: RefreshUIHandler | None = None
        self._current_model: str = ""
        self._server: Any = None

    def configure(
        self,
        *,
        process_chat: ProcessChatHandler,
        set_model: SetModelHandler,
        refresh_ui: RefreshUIHandler,
        current_model: str,
    ) -> None:
        self._process_chat = process_chat
        self._set_model = set_model
        self._refresh_ui = refresh_ui
        self._current_model = current_model

    async def start(self) -> Any | None:
        try:
            self._server = await websockets.serve(
                self.ws_handler,
                WS_HOST,
                WS_PORT,
                reuse_address=True,
            )
            return self._server
        except OSError as exc:
            if exc.errno in _ADDR_IN_USE:
                print(
                    f"AXON: Port {WS_PORT} is already in use — "
                    "another AXON instance is probably still running.\n"
                    f"Close it first, or run:  taskkill /PID <pid> /F\n"
                    f"Find PID with:  netstat -ano | findstr :{WS_PORT}\n"
                    "CLI will start without the web dashboard bridge.",
                    file=sys.stderr,
                )
                self._server = None
                return None
            raise

    async def stop(self) -> None:
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def _send_session_snapshot(self, websocket: WebSocketServerProtocol) -> None:
        policy = load_runtime_policy()
        await websocket.send(
            json.dumps(
                {
                    "type": "connected",
                    "content": "AXON bridge connected",
                    "session_started_at": SESSION_STARTED_AT,
                    "tokens": TOTAL_TOKENS,
                    "cost": TOTAL_COST,
                    "policy": policy_for_client(),
                    "web_control_enabled": policy.web_control_enabled,
                }
            )
        )
        await self.broadcast_stats(TOTAL_TOKENS, TOTAL_COST)
        if self._current_model:
            await self.broadcast_model(self._current_model)

    async def ws_handler(self, websocket: WebSocketServerProtocol) -> None:
        connected_clients.add(websocket)
        policy = load_runtime_policy()
        is_authenticated = not policy.bridge_auth_enabled

        try:
            await websocket.send(
                json.dumps(
                    {
                        "type": "auth_required",
                        "bridge_auth_enabled": policy.bridge_auth_enabled,
                        "pin": policy.bridge_pin if policy.bridge_auth_enabled else "",
                    }
                )
            )

            if is_authenticated:
                authenticated_clients.add(websocket)
                await self._send_session_snapshot(websocket)

            async for raw in websocket:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type")

                if msg_type == "auth":
                    token = str(data.get("token", ""))
                    if verify_bridge_token(token):
                        is_authenticated = True
                        authenticated_clients.add(websocket)
                        await self._send_session_snapshot(websocket)
                    else:
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "auth_failed",
                                    "content": "Invalid bridge token",
                                }
                            )
                        )
                        await websocket.close()
                    continue

                if not is_authenticated:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "auth_required",
                                "content": "Send {type: auth, token: ...}",
                            }
                        )
                    )
                    continue

                if msg_type == "get_policy":
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "policy",
                                "policy": policy_for_client(),
                            }
                        )
                    )
                    continue

                if msg_type == "set_policy":
                    updates = data.get("policy") or data
                    current = load_runtime_policy()
                    merged = RuntimePolicy(
                        autonomy_enabled=bool(
                            updates.get("autonomy_enabled", current.autonomy_enabled)
                        ),
                        web_control_enabled=bool(
                            updates.get(
                                "web_control_enabled", current.web_control_enabled
                            )
                        ),
                        terminal_control_enabled=bool(
                            updates.get(
                                "terminal_control_enabled",
                                current.terminal_control_enabled,
                            )
                        ),
                        require_desktop_confirmation=bool(
                            updates.get(
                                "require_desktop_confirmation",
                                current.require_desktop_confirmation,
                            )
                        ),
                        allow_parallel_agents=bool(
                            updates.get(
                                "allow_parallel_agents", current.allow_parallel_agents
                            )
                        ),
                        bridge_auth_enabled=bool(
                            updates.get(
                                "bridge_auth_enabled", current.bridge_auth_enabled
                            )
                        ),
                        bridge_token=str(
                            updates.get("bridge_token", current.bridge_token)
                        ),
                        bridge_pin=str(updates.get("bridge_pin", current.bridge_pin)),
                        tool_policy=current.tool_policy,
                        notifications_enabled=bool(
                            updates.get(
                                "notifications_enabled",
                                current.notifications_enabled,
                            )
                        ),
                        sound_on_approval=bool(
                            updates.get(
                                "sound_on_approval", current.sound_on_approval
                            )
                        ),
                        sound_on_complete=bool(
                            updates.get(
                                "sound_on_complete", current.sound_on_complete
                            )
                        ),
                        notification_volume=float(
                            updates.get(
                                "notification_volume",
                                current.notification_volume,
                            )
                        ),
                    )
                    save_runtime_policy(merged)
                    await self.broadcast(
                        {
                            "type": "policy",
                            "policy": policy_for_client(),
                        }
                    )
                    continue

                if msg_type == "approval_response":
                    approval_id = str(data.get("id", ""))
                    decision = str(data.get("decision", "deny"))
                    pin = str(data.get("pin", ""))
                    policy = load_runtime_policy()
                    if policy.require_desktop_confirmation:
                        if pin != policy.bridge_pin:
                            await websocket.send(
                                json.dumps(
                                    {
                                        "type": "error",
                                        "content": "Invalid PIN for desktop-confirmed approval",
                                    }
                                )
                            )
                            continue
                    resolve_approval(approval_id, decision)
                    continue

                if msg_type == "chat":
                    if not load_runtime_policy().web_control_enabled:
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "error",
                                    "content": "Web control is disabled in runtime policy",
                                }
                            )
                        )
                        continue
                    text = (data.get("text") or data.get("content") or "").strip()
                    if text and self._process_chat is not None:
                        asyncio.create_task(self._process_chat(text, "web"))

                elif msg_type == "set_model":
                    model = (data.get("model") or "").strip()
                    if model and self._set_model is not None:
                        asyncio.create_task(self._set_model(model))

        finally:
            connected_clients.discard(websocket)
            authenticated_clients.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        if not connected_clients:
            return

        message = json.dumps(payload)
        stale: list[WebSocketServerProtocol] = []

        for client in list(connected_clients):
            try:
                await client.send(message)
            except Exception:
                stale.append(client)

        for client in stale:
            connected_clients.discard(client)
            authenticated_clients.discard(client)

    async def broadcast_stats(self, tokens: int, cost: float) -> None:
        await self.broadcast(
            {
                "type": "stats",
                "tokens": tokens,
                "cost": cost,
                "session_started_at": SESSION_STARTED_AT,
            }
        )
        if self._refresh_ui is not None:
            self._refresh_ui()

    async def broadcast_model(self, model: str) -> None:
        self._current_model = model
        await self.broadcast({"type": "model", "model": model})

    async def broadcast_chat(
        self,
        *,
        role: str,
        text: str,
        source: str = "terminal",
        message_id: str | None = None,
    ) -> None:
        await self.broadcast(
            {
                "type": "chat",
                "role": "assistant" if role in {"axon", "assistant"} else role,
                "text": text,
                "content": text,
                "source": source,
                "id": message_id,
            }
        )

    async def broadcast_approval_request(self, tool_name: str, detail: str) -> None:
        await self.broadcast(
            {
                "type": "approval_request",
                "tool": tool_name,
                "detail": detail,
            }
        )

    async def broadcast_stream_start(
        self,
        message_id: str,
        *,
        source: str = "terminal",
    ) -> None:
        await self.broadcast(
            {
                "type": "stream_start",
                "id": message_id,
                "source": source,
            }
        )

    async def broadcast_stream_delta(
        self,
        message_id: str,
        delta: str,
    ) -> None:
        if not delta:
            return
        await self.broadcast(
            {
                "type": "stream_delta",
                "id": message_id,
                "delta": delta,
            }
        )

    async def broadcast_stream_end(
        self,
        message_id: str,
        text: str,
        *,
        source: str = "terminal",
    ) -> None:
        await self.broadcast(
            {
                "type": "stream_end",
                "id": message_id,
                "text": text,
                "source": source,
            }
        )

    async def broadcast_plan_update(self, tasks: list[dict[str, object]], goal: str = "") -> None:
        await self.broadcast(
            {
                "type": "plan_update",
                "goal": goal,
                "tasks": tasks,
            }
        )

    async def broadcast_tool_event(
        self,
        tool_name: str,
        status: str,
        detail: str = "",
    ) -> None:
        await self.broadcast(
            {
                "type": "tool_event",
                "tool": tool_name,
                "status": status,
                "detail": detail,
            }
        )
