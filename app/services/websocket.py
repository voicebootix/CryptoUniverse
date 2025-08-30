import asyncio
import json
from typing import List, Dict, Any
from fastapi import WebSocket
import structlog

logger = structlog.get_logger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.market_subscribers: Dict[str, List[WebSocket]] = {}  # Symbol -> WebSocket connections
        self.is_market_streaming = False

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
        
        # Start market streaming if not already running
        if not self.is_market_streaming:
            asyncio.create_task(self._start_market_streaming())

    async def broadcast(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            broken_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    broken_connections.append(connection)
            
            # Clean up broken connections
            for broken_conn in broken_connections:
                self.active_connections[user_id].remove(broken_conn)

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
            for connection in self.market_subscribers[symbol]:
                try:
                    await connection.send_json(message)
                except:
                    broken_connections.append(connection)
            
            # Clean up broken connections
            for broken_conn in broken_connections:
                self.market_subscribers[symbol].remove(broken_conn)

    async def _start_market_streaming(self):
        """Start background task for streaming market data."""
        if self.is_market_streaming:
            return
        
        self.is_market_streaming = True
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
            logger.info("Market data streaming stopped")

manager = ConnectionManager()
