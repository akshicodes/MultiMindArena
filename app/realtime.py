import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState


class SessionConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._connections[session_id].add(websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket):
        async with self._lock:
            connections = self._connections.get(session_id)
            if not connections:
                return

            connections.discard(websocket)
            if not connections:
                self._connections.pop(session_id, None)

    async def broadcast(self, session_id: str, payload: dict[str, Any]):
        async with self._lock:
            connections = list(self._connections.get(session_id, set()))

        if not connections:
            return

        message = json.dumps(payload, default=str)
        stale_connections: list[WebSocket] = []

        for websocket in connections:
            if websocket.application_state == WebSocketState.DISCONNECTED:
                stale_connections.append(websocket)
                continue

            try:
                await websocket.send_text(message)
            except Exception:
                stale_connections.append(websocket)

        if stale_connections:
            async with self._lock:
                active_connections = self._connections.get(session_id)
                if not active_connections:
                    return

                for websocket in stale_connections:
                    active_connections.discard(websocket)

                if not active_connections:
                    self._connections.pop(session_id, None)


session_connection_manager = SessionConnectionManager()