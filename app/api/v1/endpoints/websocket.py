"""
WebSocket endpoints for real-time updates
"""
from fastapi import APIRouter, WebSocket, Depends
from app.core.websocket import manager
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user: User = Depends(get_current_user)):
    """WebSocket endpoint for real-time portfolio updates."""
    user_id = str(user.id)
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_json()
            
            # Handle subscription requests
            if data.get("type") == "subscribe":
                # Handle subscription logic here
                pass
            
    except Exception as e:
        # Handle disconnection
        await manager.disconnect(user_id)
