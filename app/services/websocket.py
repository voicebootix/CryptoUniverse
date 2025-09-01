from fastapi import WebSocket
from typing import Dict, List
import asyncio
import structlog

logger = structlog.get_logger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.market_subscribers: Dict[str, List[WebSocket]] = {}
        self.is_market_streaming = False
        self._market_stream_task = None

    async def connect(self, websocket: WebSocket, user_id: str):
        """ENTERPRISE: Add WebSocket to connection pool (websocket should already be accepted)."""
        try:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            
            if websocket not in self.active_connections[user_id]:
                self.active_connections[user_id].append(websocket)
                
            logger.info(f"WebSocket connected for user {user_id}")
        except Exception as e:
            logger.error(f"Error connecting WebSocket for user {user_id}", error=str(e))

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect WebSocket and clean up subscriptions."""
        try:
            # Remove from active connections
            if user_id in self.active_connections and websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
                
            # Clean up empty user entries
            if user_id in self.active_connections and not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            # Remove from market subscribers
            for symbol, connections in self.market_subscribers.items():
                if websocket in connections:
                    connections.remove(websocket)
            
            logger.info(f"WebSocket disconnected for user {user_id}")
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket for user {user_id}", error=str(e))

    async def subscribe_to_market_data(self, websocket: WebSocket, symbols: List[str]):
        """Subscribe WebSocket to market data updates for specific symbols."""
        for symbol in symbols:
            if symbol not in self.market_subscribers:
                self.market_subscribers[symbol] = []
            if websocket not in self.market_subscribers[symbol]:
                self.market_subscribers[symbol].append(websocket)
        
        # Start market streaming if not already running (prevent race condition)
        if not self.is_market_streaming:
            self.is_market_streaming = True
            self._market_stream_task = asyncio.create_task(self._start_market_streaming())

    async def unsubscribe_from_market_data(self, websocket: WebSocket, symbols: List[str]):
        """Unsubscribe WebSocket from market data updates for specific symbols."""
        for symbol in symbols:
            if symbol in self.market_subscribers and websocket in self.market_subscribers[symbol]:
                self.market_subscribers[symbol].remove(websocket)
                
                # Clean up empty symbol entries
                if not self.market_subscribers[symbol]:
                    del self.market_subscribers[symbol]
        
        # Stop market streaming if no subscribers remain
        if not self.market_subscribers and self.is_market_streaming and self._market_stream_task:
            try:
                self._market_stream_task.cancel()
                try:
                    await self._market_stream_task
                except asyncio.CancelledError:
                    pass
            except Exception as e:
                logger.error("Error cancelling market stream task", error=str(e))
            finally:
                self.is_market_streaming = False
                self._market_stream_task = None

    async def broadcast(self, message: dict, user_id: str):
        """Broadcast a JSON message to all connections for a user."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}", error=str(e))

    async def broadcast_to_all(self, message: dict):
        """Broadcast a JSON message to all active connections."""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}", error=str(e))

    async def _start_market_streaming(self):
        """Start streaming market data to subscribers (placeholder)."""
        # This would contain the actual market data streaming logic
        # For now, it's a placeholder to prevent the syntax error
        pass

manager = ConnectionManager()