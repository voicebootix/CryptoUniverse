"""
Market Event Processor - Real-Time Intelligence

Processes real-time market events, detects opportunities, and triggers
autonomous trading strategies. Replaces batch processing with event-driven
intelligent market monitoring.

Connects to exchange WebSocket feeds for sub-second market intelligence.
"""

import asyncio
import json
import websockets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

import structlog
from app.core.config import get_settings
from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client
from app.services.autonomous_engine import MarketEvent, autonomous_engine

settings = get_settings()
logger = structlog.get_logger(__name__)


@dataclass
class PriceAlert:
    """Price alert configuration."""
    symbol: str
    condition: str  # "above", "below", "change_pct"
    threshold: float
    callback: Callable
    user_id: Optional[str] = None


class MarketEventProcessor(LoggerMixin):
    """
    Real-time market event processor for autonomous trading.
    
    Monitors multiple exchange feeds, detects significant events,
    and triggers strategy evaluation in real-time.
    """
    
    def __init__(self):
        self.websocket_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.price_history: Dict[str, List[Dict]] = {}
        self.volume_alerts: Dict[str, float] = {}
        self.price_alerts: List[PriceAlert] = []
        
        # Event detection thresholds
        self.event_thresholds = {
            "price_spike": 2.0,      # 2% price move
            "volume_spike": 3.0,     # 3x normal volume
            "large_order": 100000,   # $100k+ order
            "spread_anomaly": 0.5,   # 0.5% spread anomaly
            "arbitrage_opportunity": 0.2  # 0.2% arbitrage profit
        }
        
        self.running = False
        self.redis = None
    
    async def start_monitoring(self):
        """Start real-time market monitoring."""
        self.running = True
        self.redis = await get_redis_client()
        
        self.logger.info("🔍 Starting real-time market monitoring")
        
        # Start monitoring tasks
        tasks = [
            self._monitor_binance_stream(),
            self._monitor_kraken_stream(),
            self._monitor_kucoin_stream(),
            self._process_event_queue(),
            self._detect_arbitrage_opportunities(),
            self._monitor_whale_movements()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _monitor_binance_stream(self):
        """Monitor Binance WebSocket stream."""
        try:
            # Connect to Binance WebSocket
            uri = "wss://stream.binance.com:9443/ws/!ticker@arr"
            
            async with websockets.connect(uri) as websocket:
                self.websocket_connections["binance"] = websocket
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        
                        # Process each ticker update
                        for ticker in data:
                            await self._process_binance_ticker(ticker)
                            
                    except Exception as e:
                        self.logger.warning("Binance ticker processing error", error=str(e))
                        
        except Exception as e:
            self.logger.error("Binance stream connection failed", error=str(e))
    
    async def _process_binance_ticker(self, ticker: Dict[str, Any]):
        """Process individual Binance ticker update."""
        try:
            symbol = ticker.get("s", "")
            price = float(ticker.get("c", 0))
            volume = float(ticker.get("v", 0))
            price_change_pct = float(ticker.get("P", 0))
            
            # Filter for major pairs only
            major_pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT"]
            if symbol not in major_pairs:
                return
            
            # Detect significant events
            events = []
            
            # Price spike detection
            if abs(price_change_pct) > self.event_thresholds["price_spike"]:
                events.append(MarketEvent(
                    event_type="price_spike",
                    symbol=symbol.replace("USDT", ""),
                    price=price,
                    volume=volume,
                    timestamp=datetime.utcnow(),
                    significance=min(100, abs(price_change_pct) * 10),
                    data={
                        "price_change_pct": price_change_pct,
                        "exchange": "binance",
                        "pair": symbol
                    }
                ))
            
            # Volume spike detection
            avg_volume = await self._get_average_volume(symbol)
            if avg_volume > 0 and volume > avg_volume * self.event_thresholds["volume_spike"]:
                events.append(MarketEvent(
                    event_type="volume_spike",
                    symbol=symbol.replace("USDT", ""),
                    price=price,
                    volume=volume,
                    timestamp=datetime.utcnow(),
                    significance=min(100, (volume / avg_volume) * 20),
                    data={
                        "volume_ratio": volume / avg_volume,
                        "exchange": "binance",
                        "pair": symbol
                    }
                ))
            
            # Queue events for processing
            for event in events:
                await autonomous_engine.process_market_event(event)
            
            # Update price history
            await self._update_price_history(symbol, price, volume)
            
        except Exception as e:
            self.logger.warning("Binance ticker processing error", error=str(e))
    
    async def _monitor_kraken_stream(self):
        """Monitor Kraken WebSocket stream."""
        # Similar implementation for Kraken
        pass
    
    async def _monitor_kucoin_stream(self):
        """Monitor KuCoin WebSocket stream.""" 
        # Similar implementation for KuCoin
        pass
    
    async def _process_event_queue(self):
        """Process market events and trigger strategy evaluations."""
        while self.running:
            try:
                # Get market event
                event = await autonomous_engine.market_events_queue.get()
                
                # Log significant events
                if event.significance > 75:
                    self.logger.info(
                        f"🚨 SIGNIFICANT MARKET EVENT",
                        event_type=event.event_type,
                        symbol=event.symbol,
                        significance=event.significance,
                        price=event.price
                    )
                
                # Trigger strategy evaluation for all relevant users
                for user_id, config in autonomous_engine.active_sessions.items():
                    # Check if user is interested in this symbol
                    if (event.symbol in config.preferred_strategies or 
                        event.significance > 85):
                        
                        # Queue strategy evaluation
                        await autonomous_engine.strategy_pool.put({
                            "user_id": user_id,
                            "trigger_event": event,
                            "priority": "normal",
                            "timestamp": datetime.utcnow()
                        })
                
            except Exception as e:
                self.logger.error("Event queue processing error", error=str(e))
                await asyncio.sleep(1)
    
    async def _detect_arbitrage_opportunities(self):
        """Continuously scan for arbitrage opportunities."""
        while self.running:
            try:
                # Get prices from multiple exchanges
                symbols = ["BTC", "ETH", "SOL", "ADA"]
                
                for symbol in symbols:
                    # Get prices from different exchanges
                    binance_price = await self._get_binance_price(symbol)
                    kraken_price = await self._get_kraken_price(symbol)
                    kucoin_price = await self._get_kucoin_price(symbol)
                    
                    prices = {
                        "binance": binance_price,
                        "kraken": kraken_price, 
                        "kucoin": kucoin_price
                    }
                    
                    # Remove None values
                    prices = {k: v for k, v in prices.items() if v is not None}
                    
                    if len(prices) >= 2:
                        # Calculate arbitrage opportunity
                        max_price = max(prices.values())
                        min_price = min(prices.values())
                        profit_pct = ((max_price - min_price) / min_price) * 100
                        
                        if profit_pct > self.event_thresholds["arbitrage_opportunity"]:
                            # Create arbitrage event
                            arbitrage_event = MarketEvent(
                                event_type="arbitrage_opportunity",
                                symbol=symbol,
                                price=min_price,
                                volume=0,
                                timestamp=datetime.utcnow(),
                                significance=min(100, profit_pct * 50),
                                data={
                                    "profit_pct": profit_pct,
                                    "buy_exchange": min(prices, key=prices.get),
                                    "sell_exchange": max(prices, key=prices.get),
                                    "buy_price": min_price,
                                    "sell_price": max_price
                                }
                            )
                            
                            await autonomous_engine.process_market_event(arbitrage_event)
                
                # Check every 5 seconds for arbitrage
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error("Arbitrage detection error", error=str(e))
                await asyncio.sleep(10)
    
    async def _monitor_whale_movements(self):
        """Monitor large transactions and whale movements."""
        while self.running:
            try:
                # This would monitor:
                # - Large on-chain transactions
                # - Exchange inflows/outflows
                # - Whale wallet movements
                # - Institutional activity
                
                # For now, simulate whale detection
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error("Whale monitoring error", error=str(e))
                await asyncio.sleep(60)
    
    async def _get_average_volume(self, symbol: str) -> float:
        """Get average volume for symbol."""
        try:
            if symbol in self.price_history:
                volumes = [entry["volume"] for entry in self.price_history[symbol][-20:]]
                return sum(volumes) / len(volumes) if volumes else 0
            return 0
        except:
            return 0
    
    async def _update_price_history(self, symbol: str, price: float, volume: float):
        """Update price history for analysis."""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append({
            "price": price,
            "volume": volume,
            "timestamp": datetime.utcnow()
        })
        
        # Keep only last 100 entries
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
    
    async def _get_binance_price(self, symbol: str) -> Optional[float]:
        """Get current price from Binance."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT",
                    timeout=aiohttp.ClientTimeout(total=2)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data.get("price", 0))
            return None
        except:
            return None
    
    async def _get_kraken_price(self, symbol: str) -> Optional[float]:
        """Get current price from Kraken.""" 
        # Similar implementation
        return None
    
    async def _get_kucoin_price(self, symbol: str) -> Optional[float]:
        """Get current price from KuCoin."""
        # Similar implementation  
        return None


# Global market event processor
market_event_processor = MarketEventProcessor()


async def get_market_event_processor() -> MarketEventProcessor:
    """Dependency injection for FastAPI."""
    return market_event_processor