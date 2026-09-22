from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..auth import decode_token
from ..ws_manager import manager

router = APIRouter()

@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket, token: str):
    user_id = decode_token(token)
    if user_id is None:
        await ws.close(code=1008)
        return

    await manager.connect(user_id, ws)
    try:
        while True:
            # держим соединение, слушаем ping/тишину
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, ws)
    except Exception:
        manager.disconnect(user_id, ws)