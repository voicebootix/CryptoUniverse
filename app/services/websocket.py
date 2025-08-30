import json
from typing import List, Dict, Optional
from fastapi import WebSocket
import structlog

logger = structlog.get_logger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.chat_sessions: Dict[str, str] = {}  # session_id -> user_id mapping

    async def connect(self, websocket: WebSocket, user_id: str):
        try:
            await websocket.accept()
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
            logger.info("WebSocket connected", user_id=user_id)
        except Exception as e:
            # Connection might already be accepted or closed
            logger.warning("WebSocket connection error", error=str(e), user_id=user_id)
            # Still add to connections if not already there
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            if websocket not in self.active_connections[user_id]:
                self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                logger.info("WebSocket disconnected", user_id=user_id)
            except ValueError:
                # WebSocket not in list
                pass

    async def send_personal_message(self, message: str, user_id: str):
        """Send a message to a specific user."""
        if user_id in self.active_connections:
            disconnected_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.warning("Failed to send WebSocket message", error=str(e), user_id=user_id)
                    disconnected_connections.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected_connections:
                try:
                    self.active_connections[user_id].remove(conn)
                except ValueError:
                    pass
            
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def broadcast(self, message: dict, user_id: str):
        """Broadcast a JSON message to all connections for a user."""
        if user_id in self.active_connections:
            disconnected_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning("Failed to broadcast WebSocket message", error=str(e), user_id=user_id)
                    disconnected_connections.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected_connections:
                try:
                    self.active_connections[user_id].remove(conn)
                except ValueError:
                    pass
            
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.broadcast(message, user_id)

    def get_connected_users(self) -> List[str]:
        """Get list of currently connected user IDs."""
        return list(self.active_connections.keys())

    def get_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user."""
        return len(self.active_connections.get(user_id, []))

    def register_chat_session(self, session_id: str, user_id: str):
        """Register a chat session with user mapping."""
        self.chat_sessions[session_id] = user_id

    def get_user_for_session(self, session_id: str) -> Optional[str]:
        """Get user ID for a chat session."""
        return self.chat_sessions.get(session_id)


manager = ConnectionManager()
