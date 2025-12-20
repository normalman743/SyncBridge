import asyncio
import json
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, room: str, websocket: WebSocket):
        async with self.lock:
            if room not in self.rooms:
                self.rooms[room] = set()
            self.rooms[room].add(websocket)

    async def disconnect(self, room: str, websocket: WebSocket):
        async with self.lock:
            if room in self.rooms and websocket in self.rooms[room]:
                self.rooms[room].remove(websocket)
                if not self.rooms[room]:
                    del self.rooms[room]

    async def broadcast(self, room: str, message: dict):
        text = json.dumps(message, default=str)
        async with self.lock:
            recipients = list(self.rooms.get(room, set()))
        coros = [self._safe_send(ws, text) for ws in recipients]
        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

    async def _safe_send(self, websocket: WebSocket, text: str):
        try:
            await websocket.send_text(text)
        except Exception:
            # Ignore transient send errors; cleanup happens on disconnect.
            pass

    async def send_to(self, websocket: WebSocket, message: dict):
        await self._safe_send(websocket, json.dumps(message, default=str))


manager = ConnectionManager()
