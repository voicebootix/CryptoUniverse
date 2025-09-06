"""
WebSocket-First Market Data System for CryptoUniverse
Real-time market data using WebSocket streams with REST API fallback.
Based on production crypto trading system patterns.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

import aiohttp
import websockets
import structlog
from app.core.config import get_settings
from app.core.redis import get_redis_client

settings = get_settings()
logger = structlog.get_logger(__name__)


class DataSource(Enum):
    WEBSOCKET = "websocket"
    REST_FALLBACK = "rest_fallback"
    CACHED = "cached"


class WebSocketMarketDataManager:
    """Production-grade WebSocket-first market data system with REST fallback."""
    
    def __init__(self):
        self.redis = None
        self.connections = {}
        self.subscription_callbacks = {}
        self.fallback_tasks = {}
        self.connection_health = {}
        
        # WebSocket configurations for major exchanges
        self.websocket_configs = {
            "binance": {
                "url": "wss://stream.binance.com:9443/ws/",
                "price_stream": "@ticker",
                "reconnect_delay": 5,
                "max_retries": 10,
                "ping_interval": 20,
                "symbols_per_connection": 200
            },
            "coinbase": {
                "url": "wss://ws-feed.pro.coinbase.com",
                "price_stream": "ticker",
                "reconnect_delay": 3,
                "max_retries": 5,
                "ping_interval": 30,
                "symbols_per_connection": 100
            },
            "kraken": {
                "url": "wss://ws.kraken.com",
                "price_stream": "ticker",
                "reconnect_delay": 7,
                "max_retries": 8,
                "ping_interval": 25,
                "symbols_per_connection": 50
            }
        }
        
        # REST API fallback configurations (from existing system)
        self.rest_apis = {
            "coingecko": {
                "base_url": "https://api.coingecko.com/api/v3",
                "rate_limit": 50,
                "price_endpoint": "/simple/price",
                "fallback_interval": 100  # 100ms aggressive polling
            },
            "coincap": {
                "base_url": "https://api.coincap.io/v2",
                "rate_limit": 100,
                "price_endpoint": "/assets",
                "fallback_interval": 50  # 50ms for backup
            }
        }
        
        # Performance tracking
        self.metrics = {
            "websocket_messages": 0,
            "rest_fallback_calls": 0,
            "cache_hits": 0,
            "total_updates": 0,
            "latency_ms": [],
            "data_source_stats": {source.value: 0 for source in DataSource}
        }
        
        # Fallback failure tracking for exponential backoff
        self.fallback_failures = {}
        
        # Cache TTL optimized for crypto volatility
        self.cache_ttl = {
            "price_hot": 1,      # 1 second for hot trading pairs
            "price_warm": 5,     # 5 seconds for popular pairs
            "price_cold": 15,    # 15 seconds for less active pairs
            "market_data": 60    # 1 minute for market summaries
        }
        
        # Symbol priority classification
        self.symbol_priorities = {
            "hot": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"],
            "warm": ["DOTUSDT", "MATICUSDT", "LINKUSDT", "UNIUSDT"],
            "cold": []  # Will be populated dynamically
        }
    
    async def initialize(self):
        """Initialize Redis client and prepare connections."""
        try:
            self.redis = await get_redis_client()
            if not self.redis:
                logger.warning("Redis unavailable - market data will work without caching")
            else:
                logger.info("Redis connected for market data caching")
                
            # Initialize connection health tracking
            for exchange in self.websocket_configs:
                self.connection_health[exchange] = {
                    "connected": False,
                    "last_message": 0,
                    "reconnect_count": 0,
                    "failure_count": 0
                }
                
        except Exception as e:
            logger.error("Failed to initialize market data manager", error=str(e))
            raise RuntimeError("Market data manager initialization failed") from e
    
    async def start_real_time_feeds(self, symbols: List[str]) -> bool:
        """Start real-time WebSocket feeds for given symbols with REST fallback."""
        logger.info("Starting real-time market data feeds", symbols=symbols[:5])
        
        success_count = 0
        
        # Start WebSocket connections for each exchange
        for exchange in self.websocket_configs:
            try:
                task = asyncio.create_task(
                    self._maintain_websocket_connection(exchange, symbols)
                )
                self.connections[exchange] = task
                success_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to start {exchange} WebSocket", error=str(e))
        
        # Start REST API fallback for all symbols
        for symbol in symbols:
            fallback_task = asyncio.create_task(
                self._rest_fallback_poller(symbol)
            )
            self.fallback_tasks[symbol] = fallback_task
        
        logger.info(f"Market data feeds started", 
                   websocket_connections=success_count,
                   fallback_pollers=len(symbols))
        
        return success_count > 0
    
    async def _maintain_websocket_connection(self, exchange: str, symbols: List[str]):
        """Maintain WebSocket connection with automatic reconnection."""
        config = self.websocket_configs[exchange]
        reconnect_count = 0
        
        while reconnect_count < config["max_retries"]:
            try:
                await self._connect_and_stream(exchange, symbols, config)
                
            except Exception as e:
                reconnect_count += 1
                self.connection_health[exchange]["failure_count"] += 1
                self.connection_health[exchange]["connected"] = False
                
                logger.warning(
                    f"WebSocket connection failed for {exchange}",
                    error=str(e),
                    reconnect_attempt=reconnect_count,
                    max_retries=config["max_retries"]
                )
                
                if reconnect_count < config["max_retries"]:
                    # Exponential backoff
                    delay = config["reconnect_delay"] * (2 ** min(reconnect_count, 5))
                    await asyncio.sleep(delay)
        
        logger.error(f"Max reconnection attempts reached for {exchange}")
    
    async def _connect_and_stream(self, exchange: str, symbols: List[str], config: Dict):
        """Connect to WebSocket and handle streaming data."""
        if exchange == "binance":
            await self._binance_stream(symbols, config)
        elif exchange == "coinbase":
            await self._coinbase_stream(symbols, config)
        elif exchange == "kraken":
            await self._kraken_stream(symbols, config)
    
    async def _binance_stream(self, symbols: List[str], config: Dict):
        """Handle Binance WebSocket stream."""
        # Create stream URL for multiple symbols
        streams = [f"{symbol.lower()}{config['price_stream']}" for symbol in symbols[:config['symbols_per_connection']]]
        stream_url = f"{config['url']}{'/'.join(streams)}"
        
        logger.info("Connecting to Binance WebSocket", symbols=len(symbols))
        
        async with websockets.connect(stream_url, ping_interval=config['ping_interval']) as websocket:
            self.connection_health["binance"]["connected"] = True
            self.connection_health["binance"]["reconnect_count"] += 1
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_binance_message(data)
                    self.connection_health["binance"]["last_message"] = time.time()
                    
                except Exception as e:
                    logger.warning("Failed to process Binance message", error=str(e))
    
    async def _coinbase_stream(self, symbols: List[str], config: Dict):
        """Handle Coinbase WebSocket stream."""
        subscribe_message = {
            "type": "subscribe",
            "product_ids": symbols[:config['symbols_per_connection']],
            "channels": [config['price_stream']]
        }
        
        logger.info("Connecting to Coinbase WebSocket", symbols=len(symbols))
        
        async with websockets.connect(config['url'], ping_interval=config['ping_interval']) as websocket:
            # Send subscription message
            await websocket.send(json.dumps(subscribe_message))
            
            self.connection_health["coinbase"]["connected"] = True
            self.connection_health["coinbase"]["reconnect_count"] += 1
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_coinbase_message(data)
                    self.connection_health["coinbase"]["last_message"] = time.time()
                    
                except Exception as e:
                    logger.warning("Failed to process Coinbase message", error=str(e))
    
    async def _kraken_stream(self, symbols: List[str], config: Dict):
        """Handle Kraken WebSocket stream."""
        subscribe_message = {
            "event": "subscribe",
            "pair": symbols[:config['symbols_per_connection']],
            "subscription": {"name": config['price_stream']}
        }
        
        logger.info("Connecting to Kraken WebSocket", symbols=len(symbols))
        
        async with websockets.connect(config['url'], ping_interval=config['ping_interval']) as websocket:
            # Send subscription message
            await websocket.send(json.dumps(subscribe_message))
            
            self.connection_health["kraken"]["connected"] = True
            self.connection_health["kraken"]["reconnect_count"] += 1
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_kraken_message(data)
                    self.connection_health["kraken"]["last_message"] = time.time()
                    
                except Exception as e:
                    logger.warning("Failed to process Kraken message", error=str(e))
    
    async def _process_binance_message(self, data: Dict):
        """Process Binance ticker message."""
        if "s" in data and "c" in data:  # Symbol and close price
            symbol = data["s"]
            price = float(data["c"])
            volume = float(data.get("v", 0))
            
            await self._update_price_data(symbol, price, volume, DataSource.WEBSOCKET, "binance")
    
    async def _process_coinbase_message(self, data: Dict):
        """Process Coinbase ticker message."""
        if data.get("type") == "ticker" and "product_id" in data:
            symbol = data["product_id"].replace("-", "")
            price = float(data.get("price", 0))
            volume = float(data.get("volume_24h", 0))
            
            await self._update_price_data(symbol, price, volume, DataSource.WEBSOCKET, "coinbase")
    
    async def _process_kraken_message(self, data: Dict):
        """Process Kraken ticker message."""
        # Kraken has a more complex message format
        if isinstance(data, list) and len(data) > 1:
            if isinstance(data[1], dict) and "c" in data[1]:
                # Ticker data format
                price = float(data[1]["c"][0]) if data[1]["c"] else 0
                volume = float(data[1].get("v", [0, 0])[1])
                symbol = data[3] if len(data) > 3 else "UNKNOWN"
                
                await self._update_price_data(symbol, price, volume, DataSource.WEBSOCKET, "kraken")
    
    async def _update_price_data(self, symbol: str, price: float, volume: float, 
                               source: DataSource, exchange: str):
        """Update price data with caching and metrics."""
        timestamp = time.time()
        
        price_data = {
            "symbol": symbol,
            "price": price,
            "volume_24h": volume,
            "timestamp": timestamp,
            "source": source.value,
            "exchange": exchange
        }
        
        # Update metrics
        self.metrics["total_updates"] += 1
        self.metrics["data_source_stats"][source.value] += 1
        
        # Cache with priority-based TTL
        if self.redis:
            try:
                cache_key = f"price:{symbol}"
                ttl = self._get_cache_ttl(symbol)
                
                await self.redis.setex(
                    cache_key,
                    ttl,
                    json.dumps(price_data)
                )
                
                # Also publish to Redis Streams for event-driven services
                await self.redis.xadd(
                    "market_updates",
                    price_data,
                    maxlen=100000,  # Keep last 100k updates
                    approximate=True
                )
                
            except Exception as e:
                logger.warning("Failed to cache price data", error=str(e))
        
        # Call registered callbacks
        await self._notify_subscribers(symbol, price_data)
        
        logger.debug(f"Price updated: {symbol} = ${price:.4f}", 
                    source=source.value, exchange=exchange)
    
    async def _rest_fallback_poller(self, symbol: str):
        """Aggressive REST API polling when WebSocket is unavailable."""
        while True:
            try:
                # Check if WebSocket is providing recent data
                if await self._is_websocket_healthy(symbol):
                    await asyncio.sleep(5)  # WebSocket is working, check again in 5s
                    continue
                
                # WebSocket is down, start aggressive polling
                logger.warning(f"WebSocket down for {symbol}, starting REST fallback")
                
                price_data = await self._fetch_rest_price(symbol)
                if price_data:
                    await self._update_price_data(
                        symbol, 
                        price_data["price"], 
                        price_data.get("volume", 0),
                        DataSource.REST_FALLBACK,
                        price_data.get("exchange", "rest_api")
                    )
                    
                    # Reset failure count on success
                    if symbol in self.fallback_failures:
                        self.fallback_failures[symbol] = max(0, self.fallback_failures[symbol] - 1)
                else:
                    # Track failure for exponential backoff
                    self.fallback_failures[symbol] = self.fallback_failures.get(symbol, 0) + 1
                
                # Get appropriate fallback interval based on symbol priority
                interval = self._get_fallback_interval(symbol)
                await asyncio.sleep(interval / 1000)  # Convert to seconds
                
            except Exception as e:
                # Track failure for exponential backoff
                self.fallback_failures[symbol] = self.fallback_failures.get(symbol, 0) + 1
                
                logger.error(f"REST fallback failed for {symbol}", error=str(e))
                
                # Use exponential backoff interval even for exceptions
                interval = self._get_fallback_interval(symbol)
                await asyncio.sleep(interval / 1000)
    
    async def _is_websocket_healthy(self, symbol: str) -> bool:
        """Check if WebSocket is providing recent data for symbol."""
        if not self.redis:
            return False
            
        try:
            cache_key = f"price:{symbol}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                # Consider healthy if last update was within 10 seconds from WebSocket
                if (data.get("source") == DataSource.WEBSOCKET.value and 
                    time.time() - data.get("timestamp", 0) < 10):
                    return True
            
            return False
            
        except Exception:
            return False
    
    async def _fetch_rest_price(self, symbol: str) -> Optional[Dict]:
        """Fetch price from REST API as fallback."""
        # Try CoinGecko first (most reliable free API)
        try:
            symbol_mapping = {
                "BTCUSDT": "bitcoin",
                "ETHUSDT": "ethereum", 
                "SOLUSDT": "solana",
                "ADAUSDT": "cardano"
            }
            
            gecko_id = symbol_mapping.get(symbol, symbol.lower().replace("usdt", ""))
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={gecko_id}&vs_currencies=usd&include_24hr_vol=true"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if gecko_id in data:
                            self.metrics["rest_fallback_calls"] += 1
                            return {
                                "price": data[gecko_id]["usd"],
                                "volume": data[gecko_id].get("usd_24h_vol", 0),
                                "exchange": "coingecko_rest"
                            }
            
        except Exception as e:
            logger.warning(f"REST fallback failed for {symbol}", error=str(e))
        
        return None
    
    def _get_cache_ttl(self, symbol: str) -> int:
        """Get cache TTL based on symbol priority."""
        if symbol in self.symbol_priorities["hot"]:
            return self.cache_ttl["price_hot"]
        elif symbol in self.symbol_priorities["warm"]:
            return self.cache_ttl["price_warm"]
        else:
            return self.cache_ttl["price_cold"]
    
    def _get_fallback_interval(self, symbol: str) -> int:
        """Get REST fallback interval with exponential backoff and jitter (in ms)."""
        import random
        
        # Conservative base intervals (1-5 seconds instead of 50-500ms)
        base_intervals = {
            "hot": 1000,    # 1 second for hot symbols
            "warm": 2000,   # 2 seconds for warm symbols  
            "cold": 5000    # 5 seconds for cold symbols
        }
        
        # Determine base interval
        if symbol in self.symbol_priorities["hot"]:
            base_interval = base_intervals["hot"]
        elif symbol in self.symbol_priorities["warm"]:
            base_interval = base_intervals["warm"]
        else:
            base_interval = base_intervals["cold"]
        
        # Apply exponential backoff based on recent failures
        failure_count = self.fallback_failures.get(symbol, 0)
        if failure_count > 0:
            # Double the interval for each failure, max 8x
            backoff_multiplier = min(2 ** failure_count, 8)
            base_interval = base_interval * backoff_multiplier
        
        # Add random jitter (±10%) to spread requests
        jitter = random.uniform(-0.1, 0.1)
        final_interval = int(base_interval * (1 + jitter))
        
        # Clamp between reasonable bounds (1s to 30s)
        return max(1000, min(final_interval, 30000))
    
    async def subscribe_to_symbol(self, symbol: str, callback: Callable):
        """Subscribe to real-time updates for a specific symbol."""
        if symbol not in self.subscription_callbacks:
            self.subscription_callbacks[symbol] = []
        
        self.subscription_callbacks[symbol].append(callback)
        logger.info(f"Subscribed to {symbol} updates")
    
    async def _notify_subscribers(self, symbol: str, price_data: Dict):
        """Notify all subscribers of price updates (supports both sync and async callbacks)."""
        if symbol in self.subscription_callbacks:
            for callback in self.subscription_callbacks[symbol]:
                try:
                    # Call the callback and check if it returns a coroutine
                    result = callback(price_data)
                    
                    # If it's a coroutine, await it; otherwise it's already done
                    if asyncio.iscoroutine(result):
                        await result
                        
                except Exception as e:
                    logger.warning(f"Subscriber callback failed for {symbol}", error=str(e))
    
    async def get_current_price(self, symbol: str) -> Optional[Dict]:
        """Get current price with automatic fallback chain."""
        # Try cache first
        if self.redis:
            try:
                cached_data = await self.redis.get(f"price:{symbol}")
                if cached_data:
                    self.metrics["cache_hits"] += 1
                    data = json.loads(cached_data)
                    
                    # Check if cache is fresh enough
                    age = time.time() - data.get("timestamp", 0)
                    ttl = self._get_cache_ttl(symbol)
                    
                    if age < ttl:
                        return data
                        
            except Exception as e:
                logger.warning("Cache lookup failed", error=str(e))
        
        # Cache miss or stale, try REST API
        rest_data = await self._fetch_rest_price(symbol)
        if rest_data:
            await self._update_price_data(
                symbol,
                rest_data["price"],
                rest_data.get("volume", 0),
                DataSource.REST_FALLBACK,
                rest_data.get("exchange", "rest_fallback")
            )
            return rest_data
        
        return None
    
    async def get_health_status(self) -> Dict:
        """Get comprehensive health status of market data system."""
        health = {
            "websocket_connections": {},
            "metrics": self.metrics.copy(),
            "redis_connected": self.redis is not None,
            "active_subscriptions": len(self.subscription_callbacks),
            "fallback_tasks_running": len(self.fallback_tasks)
        }
        
        # Add connection health details
        for exchange, health_data in self.connection_health.items():
            health["websocket_connections"][exchange] = {
                "connected": health_data["connected"],
                "last_message_age": time.time() - health_data["last_message"] if health_data["last_message"] else None,
                "reconnect_count": health_data["reconnect_count"],
                "failure_count": health_data["failure_count"]
            }
        
        return health
    
    async def shutdown(self):
        """Graceful shutdown of all connections and tasks."""
        logger.info("Shutting down market data manager")
        
        # Close WebSocket connections
        for exchange, task in self.connections.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close fallback tasks
        for symbol, task in self.fallback_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Market data manager shutdown complete")


# Global instance
websocket_market_data = WebSocketMarketDataManager()