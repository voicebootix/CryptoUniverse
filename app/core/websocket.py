"""
WebSocket Manager for Real-Time Updates
"""
import asyncio
import json
import structlog
from typing import Dict, Any
from datetime import datetime
from fastapi import WebSocket

logger = structlog.get_logger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[user_id] = websocket
            logger.info("WebSocket connected", user_id=user_id)

    async def disconnect(self, user_id: str):
        """Disconnect and cleanup a WebSocket connection."""
        async with self._lock:
            if user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].close()
                except Exception as e:
                    logger.warning("Error closing WebSocket", user_id=user_id, error=str(e))
                finally:
                    del self.active_connections[user_id]
                    logger.info("WebSocket disconnected", user_id=user_id)

    async def broadcast_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send a message to a specific user."""
        async with self._lock:
            if user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].send_json(message)
                except Exception as e:
                    logger.error("Failed to broadcast message", user_id=user_id, error=str(e))
                    # Connection might be stale, clean it up
                    await self.disconnect(user_id)

    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast a message to all connected users."""
        async with self._lock:
            disconnected_users = []
            for user_id, connection in self.active_connections.items():
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error("Failed to broadcast to user", user_id=user_id, error=str(e))
                    disconnected_users.append(user_id)
            
            # Cleanup any failed connections
            for user_id in disconnected_users:
                await self.disconnect(user_id)

    async def broadcast_portfolio_snapshot(
        self,
        user_id: str,
        snapshot_date: datetime,
        total_value_usd: float,
        daily_pnl_usd: float,
        daily_pnl_percent: float,
        positions_data: Dict[str, Any] = None
    ):
        """Broadcast portfolio snapshot update to a specific user."""
        message = {
            "type": "portfolio_snapshot",
            "data": {
                "timestamp": snapshot_date.isoformat(),
                "total_value_usd": total_value_usd,
                "daily_pnl": daily_pnl_usd,
                "daily_pnl_percent": daily_pnl_percent
            }
        }

        # Add positions data if provided
        if positions_data:
            message["data"]["positions"] = positions_data

        await self.broadcast_to_user(user_id, message)

    async def broadcast_portfolio_update(
        self,
        user_id: str,
        total_value_usd: float,
        daily_pnl_usd: float,
        daily_pnl_percent: float,
        performance_history: list = None
    ):
        """Broadcast comprehensive portfolio update to a specific user."""
        message = {
            "type": "portfolio_update",
            "data": {
                "timestamp": datetime.utcnow().isoformat(),
                "total_value_usd": total_value_usd,
                "daily_pnl": daily_pnl_usd,
                "daily_pnl_percent": daily_pnl_percent
            }
        }

        if performance_history:
            message["data"]["performance_history"] = performance_history

        await self.broadcast_to_user(user_id, message)

manager = WebSocketManager()