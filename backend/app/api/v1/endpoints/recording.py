from typing import Any

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.api import deps
from app.models.user import User
from app.services.recorder import recorder_service
import json

router = APIRouter()


@router.get("/context")
async def get_recording_context(
    *,
    max_dom_chars: int = Query(50000, ge=1000, le=200000),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """获取当前录制浏览器的真实页面上下文。"""
    del current_user
    return await recorder_service.get_page_context(dom_limit=max_dom_chars)

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
                try:
                    url = message.get("url")
                    await recorder_service.start_recording(url, send_event_to_client)
                    await websocket.send_json({"status": "started", "url": url})
                except Exception as e:
                    await websocket.send_json({"status": "error", "message": str(e)})
                
            elif message.get("type") == "stop":
                await recorder_service.stop_recording()
                await websocket.send_json({"status": "stopped"})
                
    except WebSocketDisconnect:
        await recorder_service.stop_recording()
