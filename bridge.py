from __future__ import annotations

import asyncio
import json
import os
import threading
from typing import Any, Callable

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    websockets = None  # type: ignore[assignment]
    WebSocketServerProtocol = object  # type: ignore[misc, assignment]

MessageHandler = Callable[[dict[str, Any]], None]

DEFAULT_HOST = os.environ.get("AXON_WS_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("AXON_WS_PORT", "8765"))


class WSBridge:
    """WebSocket hub connecting the AXON CLI/backend with the web dashboard."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._clients: set[WebSocketServerProtocol] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._on_message: MessageHandler | None = None
        self._server = None

    def set_message_handler(self, handler: MessageHandler) -> None:
        self._on_message = handler

    def start(self) -> None:
        if websockets is None:
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())
        self._loop.run_forever()

    async def _serve(self) -> None:
        self._server = await websockets.serve(
            self._handler,
            self.host,
            self.port,
        )

    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        self._clients.add(websocket)
        try:
            await websocket.send(
                json.dumps(
                    {
                        "type": "connected",
                        "source": "terminal",
                        "content": "AXON bridge connected",
                    }
                )
            )
            async for raw in websocket:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if data.get("source") == "web" and self._on_message:
                    self._on_message(data)
        finally:
            self._clients.discard(websocket)

    def broadcast(self, payload: dict[str, Any]) -> None:
        if not self._loop or not self._clients:
            return
        asyncio.run_coroutine_threadsafe(
            self._broadcast_async(payload),
            self._loop,
        )

    async def _broadcast_async(self, payload: dict[str, Any]) -> None:
        message = json.dumps(payload)
        stale: list[WebSocketServerProtocol] = []
        for client in self._clients:
            try:
                await client.send(message)
            except Exception:
                stale.append(client)
        for client in stale:
            self._clients.discard(client)


_bridge: WSBridge | None = None


def get_bridge() -> WSBridge:
    """Return the singleton WebSocket bridge, starting it if needed."""
    global _bridge
    if _bridge is None:
        _bridge = WSBridge()
        _bridge.start()
    return _bridge
