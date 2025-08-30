import asyncio
import json
from typing import List, Dict, Any, Optional
from fastapi import WebSocket
import structlog

logger = structlog.get_logger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.market_subscribers: Dict[str, List[WebSocket]] = {}  # Symbol -> WebSocket connections
        self.is_market_streaming = False
        self._market_stream_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket, user_id: str):
        try:
            await websocket.accept()
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
            logger.info(f"WebSocket connected for user {user_id}")
        except Exception as e:
            # Connection might already be accepted or closed
            logger.warning(f"WebSocket connection error: {e}")
            # Still add to connections if not already there
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            if websocket not in self.active_connections[user_id]:
                self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
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
        if user_id in self.active_connections:
            broken_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.exception(f"Failed to send message to user {user_id}", error=str(e))
                    broken_connections.append(connection)
            
            # Clean up broken connections safely
            if broken_connections:
                self.active_connections[user_id] = [
                    conn for conn in self.active_connections[user_id] 
                    if conn not in broken_connections
                ]
                
                # Remove user if no connections remain
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

    async def broadcast_market_update(self, symbol: str, price_data: Dict[str, Any]):
        """Broadcast market data update to subscribed connections."""
        if symbol in self.market_subscribers:
            message = {
                "type": "market_update",
                "symbol": symbol,
                "data": price_data,
                "timestamp": price_data.get("timestamp")
            }
            
            broken_connections = []
            # Iterate over a copy to avoid mutation during iteration
            for connection in list(self.market_subscribers[symbol]):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.exception(f"Failed to send market update for {symbol}", error=str(e))
                    broken_connections.append(connection)
                    
                    # Attempt to close broken connection
                    try:
                        await connection.close()
                    except Exception as close_error:
                        logger.warning(f"Failed to close broken connection", error=str(close_error))
            
            # Clean up broken connections safely
            if broken_connections:
                self.market_subscribers[symbol] = [
                    conn for conn in self.market_subscribers[symbol] 
                    if conn not in broken_connections
                ]
                
                # Remove symbol if no connections remain
                if not self.market_subscribers[symbol]:
                    del self.market_subscribers[symbol]

    async def _start_market_streaming(self):
        """Start background task for streaming market data."""
        logger.info("Starting market data streaming")
        
        try:
            while self.is_market_streaming and self.market_subscribers:
                # Get all subscribed symbols
                subscribed_symbols = [symbol for symbol, connections in self.market_subscribers.items() if connections]
                
                if not subscribed_symbols:
                    await asyncio.sleep(5)
                    continue
                
                # Fetch latest prices for subscribed symbols
                try:
                    from app.services.market_data_feeds import market_data_feeds
                    
                    # Initialize if needed
                    if not hasattr(market_data_feeds, 'redis') or market_data_feeds.redis is None:
                        await market_data_feeds.async_init()
                    
                    for symbol in subscribed_symbols:
                        price_data = await market_data_feeds.get_real_time_price(symbol)
                        if price_data.get("success"):
                            await self.broadcast_market_update(symbol, price_data.get("data", {}))
                
                except Exception as e:
                    logger.error("Market streaming error", error=str(e))
                
                # Wait 30 seconds before next update (respecting rate limits)
                await asyncio.sleep(30)
                
        except Exception as e:
            logger.error("Market streaming failed", error=str(e))
        finally:
            self.is_market_streaming = False
            self._market_stream_task = None
            logger.info("Market data streaming stopped")

manager = ConnectionManager()
