from fastapi import WebSocket
import structlog

logger = structlog.get_logger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """ENTERPRISE: Add WebSocket to connection pool (websocket should already be accepted)."""
        try:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            
            if websocket not in self.active_connections[user_id]:
                self.active_connections[user_id].append(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove from market subscribers
        for symbol, connections in self.market_subscribers.items():
            if websocket in connections:
                connections.remove(websocket)
        
        logger.info(f"WebSocket disconnected for user {user_id}")

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

manager = ConnectionManager()
