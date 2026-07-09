from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, chat_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active[chat_id].append(websocket)

    def disconnect(self, chat_id: int, websocket: WebSocket) -> None:
        if websocket in self.active[chat_id]:
            self.active[chat_id].remove(websocket)

    async def broadcast(self, chat_id: int, payload: dict) -> None:
        disconnected: list[WebSocket] = []
        for socket in self.active[chat_id]:
            try:
                await socket.send_json(payload)
            except RuntimeError:
                disconnected.append(socket)
        for socket in disconnected:
            self.disconnect(chat_id, socket)


manager = ConnectionManager()

