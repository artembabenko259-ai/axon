from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Awaitable, Callable
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol

WS_HOST = "127.0.0.1"
WS_PORT = 8765
_ADDR_IN_USE = frozenset({48, 98, 10048})

ProcessChatHandler = Callable[[str, str], Awaitable[None]]
SetModelHandler = Callable[[str], Awaitable[None]]
RefreshUIHandler = Callable[[], None]

connected_clients: set[WebSocketServerProtocol] = set()


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

    async def ws_handler(self, websocket: WebSocketServerProtocol) -> None:
        connected_clients.add(websocket)
        try:
            from llm_client import TOTAL_COST, TOTAL_TOKENS

            await websocket.send(
                json.dumps(
                    {
                        "type": "connected",
                        "content": "AXON bridge connected",
                    }
                )
            )
            await self.broadcast_stats(TOTAL_TOKENS, TOTAL_COST)
            if self._current_model:
                await self.broadcast_model(self._current_model)

            async for raw in websocket:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type")

                if msg_type == "chat":
                    text = (data.get("text") or data.get("content") or "").strip()
                    if text and self._process_chat is not None:
                        asyncio.create_task(self._process_chat(text, "web"))

                elif msg_type == "set_model":
                    model = (data.get("model") or "").strip()
                    if model and self._set_model is not None:
                        asyncio.create_task(self._set_model(model))

        finally:
            connected_clients.discard(websocket)

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

    async def broadcast_stats(self, tokens: int, cost: float) -> None:
        await self.broadcast(
            {
                "type": "stats",
                "tokens": tokens,
                "cost": cost,
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
