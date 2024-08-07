from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Optional
import asyncio
import random

app = FastAPI()

class ConnectionManager: 
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket):
        client_id = str(random.randint(100, 999))
        await websocket.accept()
        self.active_connections[client_id] = websocket
        await self.active_connections[client_id].send_text(f"Connected! Your client ID is {client_id}")
        return client_id 
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
         del self.active_connections[client_id]
    
    async def broadcast(self, message: str):
        for client_id, connection in list(self.active_connections.items()):
            try:
                await connection.send_text(message)
            except RuntimeError:
                self.disconnect(client_id)

    async def send_message_to_client(self, client_id: str, message: str): 
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except RuntimeError:
                self.disconnect(client_id)
                raise HTTPException(status_code=404, detail=f"Client ID {client_id} not connected")
        else:
            raise HTTPException(status_code=404, detail=f"Client ID {client_id} not connected")

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = await manager.connect(websocket)
    try: 
        while True: 
            message = await websocket.receive_text()
            if message.startswith("private:"): 
                _, private_message = message.split(": ", 1)
                await asyncio.sleep(1) 
                await manager.send_message_to_client(client_id, f"Private message from {client_id}: {private_message}")
            else: 
                await asyncio.sleep(1) 
                await manager.broadcast(f"Public message from {client_id}: {message}")
    except WebSocketDisconnect: 
        manager.disconnect(websocket)
        await manager.broadcast("A client disconnected.")


@app.post("/send-message")
async def send_message(client_id: Optional[str] = None, message: str = ""):
    if client_id: 
        await manager.send_message_to_client(client_id, f"Server private message to {client_id}: {message}")
    else:
        await manager.broadcast(f"Server broadcast message: {message}")
    return {"message": "Message sent"}