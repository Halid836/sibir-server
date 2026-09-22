from typing import Dict, List
from fastapi import WebSocket

class WSManager:
    def __init__(self):
        # user_id -> list of websockets
        self.active: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: int, ws: WebSocket):
        conns = self.active.get(user_id)
        if conns and ws in conns:
            conns.remove(ws)
            if not conns:
                self.active.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict):
        for ws in list(self.active.get(user_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id, ws)

manager = WSManager()
