from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.recorder import recorder_service
import json

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    async def send_event_to_client(event):
        await websocket.send_json(event)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "start":
                url = message.get("url")
                await recorder_service.start_recording(url, send_event_to_client)
                await websocket.send_json({"status": "started", "url": url})
                
            elif message.get("type") == "stop":
                await recorder_service.stop_recording()
                await websocket.send_json({"status": "stopped"})
                
    except WebSocketDisconnect:
        await recorder_service.stop_recording()
