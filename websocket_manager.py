# app/websocket_manager.py
import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket

"""
ConnectionManager 管理每个 form 的连接（room），并提供广播/单发功能。
rooms: Dict[str, Set[WebSocket]]
"""

class ConnectionManager:
    def __init__(self):
        # key: room_id (str, e.g. "form:1"), value: set of websockets
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, room: str, websocket: WebSocket):
        """
        Add websocket to a room.
        """
        async with self.lock:
            if room not in self.rooms:
                self.rooms[room] = set()
            self.rooms[room].add(websocket)

    async def disconnect(self, room: str, websocket: WebSocket):
        async with self.lock:
            if room in self.rooms and websocket in self.rooms[room]:
                self.rooms[room].remove(websocket)
                if not self.rooms[room]:
                    # optionally delete empty room
                    del self.rooms[room]

    async def broadcast(self, room: str, message: dict):
        """
        Broadcast a JSON-serializable dict to all websocket clients in room.
        """
        text = json.dumps(message, default=str)
        # We copy recipients to avoid mutation-on-iterate issues.
        async with self.lock:
            recipients = list(self.rooms.get(room, set()))
        coros = []
        for ws in recipients:
            coros.append(self._safe_send(ws, text))
        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

    async def _safe_send(self, websocket: WebSocket, text: str):
        """
        Send text to websocket, ignore connection errors.
        """
        try:
            await websocket.send_text(text)
        except Exception:
            # If sending fails, we deliberately ignore; client will reconnect.
            # Disconnection cleanup should happen when websocket disconnects.
            pass

    async def send_to(self, websocket: WebSocket, message: dict):
        await self._safe_send(websocket, json.dumps(message, default=str))


# singleton manager for app
manager = ConnectionManager()
