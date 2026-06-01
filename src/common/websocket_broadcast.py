import asyncio
import json
from typing import List, Optional
from fastapi import WebSocket

from src.common.logging import setup_logging

logger = setup_logging("websocket")


class WebSocketManager:
    def __init__(self):
        self._connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("WebSocket client connected", extra={"total": len(self._connections)})

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)
        logger.info("WebSocket client disconnected", extra={"total": len(self._connections)})

    async def broadcast(self, event: dict):
        dead: List[WebSocket] = []
        async with self._lock:
            for ws in self._connections:
                try:
                    await ws.send_json(event)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections.remove(ws)
        if dead:
            logger.info("Cleaned up dead WebSocket connections", extra={"count": len(dead)})

    @property
    def active_count(self) -> int:
        return len(self._connections)


ws_manager = WebSocketManager()
