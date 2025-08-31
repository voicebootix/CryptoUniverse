"""
Real Market Data Service - Enterprise Grade

Provides real-time market data aggregation from multiple exchanges
without requiring user API keys. Uses public market data endpoints
for price feeds, volume, and market statistics.

No mock data, no placeholders - production-ready market data.
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import structlog
from app.core.config import get_settings
from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client

settings = get_settings()
logger = structlog.get_logger(__name__)


@dataclass
class MarketDataPoint:
    """Market data point structure."""
    symbol: str
    price: Decimal
    change_24h: float
    change_24h_percent: float
    volume_24h: str
    high_24h: Decimal
    low_24h: Decimal
    last_updated: datetime
    exchange: str


class RealMarketDataService(LoggerMixin):
    """
    Enterprise-grade real market data service.
    
    Aggregates real-time market data from multiple exchanges
    using public APIs. Provides caching, failover, and
    comprehensive market analytics.
    """
    
    def __init__(self):
        self.redis = None
        self.cache_ttl = 30  # 30 seconds cache
        self.exchange_weights = {
            "binance": 0.4,
            "kraken": 0.3,
            "kucoin": 0.2,
            "coinbase": 0.1
        }
    
    async def get_market_overview(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get comprehensive market overview with real data.
        
        Args:
            symbols: Optional list of symbols to get data for
            
        Returns:
            Market overview with real prices and statistics
        """
        try:
            # Default symbols if none provided
            if not symbols:
                symbols = ["BTC", "ETH", "SOL", "ADA", "DOT", "MATIC", "LINK", "UNI", "AVAX", "ATOM"]
            
            # Get cached data first
            cached_data = await self._get_cached_market_data(symbols)
            if cached_data:
                return {
                    "success": True,
                    "market_data": cached_data,
                    "source": "cache",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Fetch fresh data from multiple exchanges
            market_data = await self._fetch_aggregated_market_data(symbols)
            
            # Cache the results
            await self._cache_market_data(market_data)
            
            return {
                "success": True,
                "market_data": market_data,
                "source": "live",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get market overview", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _fetch_aggregated_market_data(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Fetch and aggregate market data from multiple exchanges."""
        try:
            # Fetch from multiple exchanges in parallel
            tasks = [
                self._fetch_binance_data(symbols),
                self._fetch_kraken_data(symbols),
                self._fetch_kucoin_data(symbols),
                self._fetch_coinbase_data(symbols)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aggregate data by symbol
            aggregated_data = {}
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Exchange {i} data fetch failed: {result}")
                    continue
                
                for symbol, data in result.items():
                    if symbol not in aggregated_data:
                        aggregated_data[symbol] = []
                    aggregated_data[symbol].append(data)
            
            # Calculate weighted averages
            final_data = []
            for symbol in symbols:
                if symbol in aggregated_data and aggregated_data[symbol]:
                    aggregated_point = self._calculate_weighted_average(
                        symbol, aggregated_data[symbol]
                    )
                    final_data.append(aggregated_point)
            
            return final_data
            
        except Exception as e:
            self.logger.error("Failed to fetch aggregated market data", error=str(e))
            return []
    
    async def _fetch_binance_data(self, symbols: List[str]) -> Dict[str, MarketDataPoint]:
        """Fetch real market data from Binance."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get 24hr ticker statistics
                async with session.get(
                    "https://api.binance.com/api/v3/ticker/24hr",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return {}
                    
                    data = await response.json()
                    result = {}
                    
                    for ticker in data:
                        symbol_pair = ticker["symbol"]
                        # Extract base symbol (BTC from BTCUSDT)
                        for symbol in symbols:
                            if symbol_pair.startswith(symbol) and symbol_pair.endswith("USDT"):
                                result[symbol] = MarketDataPoint(
                                    symbol=symbol,
                                    price=Decimal(ticker["lastPrice"]),
                                    change_24h=float(ticker["priceChange"]),
                                    change_24h_percent=float(ticker["priceChangePercent"]),
                                    volume_24h=self._format_volume(float(ticker["quoteVolume"])),
                                    high_24h=Decimal(ticker["highPrice"]),
                                    low_24h=Decimal(ticker["lowPrice"]),
                                    last_updated=datetime.utcnow(),
                                    exchange="binance"
                                )
                                break
                    
                    return result
                    
        except Exception as e:
            self.logger.error("Failed to fetch Binance market data", error=str(e))
            return {}
    
    async def _fetch_kraken_data(self, symbols: List[str]) -> Dict[str, MarketDataPoint]:
        """Fetch real market data from Kraken."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get ticker information
                async with session.get(
                    "https://api.kraken.com/0/public/Ticker",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return {}
                    
                    data = await response.json()
                    result = {}
                    
                    if data.get("error"):
                        return {}
                    
                    ticker_data = data.get("result", {})
                    
                    # Map Kraken pairs to symbols
                    kraken_pairs = {
                        "BTC": "XXBTZUSD",
                        "ETH": "XETHZUSD", 
                        "SOL": "SOLUSD",
                        "ADA": "ADAUSD",
                        "DOT": "DOTUSD"
                    }
                    
                    for symbol in symbols:
                        kraken_pair = kraken_pairs.get(symbol)
                        if kraken_pair and kraken_pair in ticker_data:
                            ticker = ticker_data[kraken_pair]
                            current_price = float(ticker["c"][0])
                            open_price = float(ticker["o"])
                            change_24h = current_price - open_price
                            change_24h_percent = (change_24h / open_price) * 100 if open_price > 0 else 0
                            
                            result[symbol] = MarketDataPoint(
                                symbol=symbol,
                                price=Decimal(str(current_price)),
                                change_24h=change_24h,
                                change_24h_percent=change_24h_percent,
                                volume_24h=self._format_volume(float(ticker["v"][1])),
                                high_24h=Decimal(ticker["h"][1]),
                                low_24h=Decimal(ticker["l"][1]),
                                last_updated=datetime.utcnow(),
                                exchange="kraken"
                            )
                    
                    return result
                    
        except Exception as e:
            self.logger.error("Failed to fetch Kraken market data", error=str(e))
            return {}
    
    async def _fetch_kucoin_data(self, symbols: List[str]) -> Dict[str, MarketDataPoint]:
        """Fetch real market data from KuCoin."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get 24hr stats
                async with session.get(
                    "https://api.kucoin.com/api/v1/market/allTickers",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return {}
                    
                    data = await response.json()
                    result = {}
                    
                    if data.get("code") != "200000":
                        return {}
                    
                    tickers = data.get("data", {}).get("ticker", [])
                    
                    for ticker in tickers:
                        symbol_pair = ticker.get("symbol", "")
                        # Extract base symbol (BTC from BTC-USDT)
                        for symbol in symbols:
                            if symbol_pair == f"{symbol}-USDT":
                                current_price = float(ticker.get("last", 0))
                                change_24h = float(ticker.get("changePrice", 0))
                                change_24h_percent = float(ticker.get("changeRate", 0)) * 100
                                
                                result[symbol] = MarketDataPoint(
                                    symbol=symbol,
                                    price=Decimal(str(current_price)),
                                    change_24h=change_24h,
                                    change_24h_percent=change_24h_percent,
                                    volume_24h=self._format_volume(float(ticker.get("volValue", 0))),
                                    high_24h=Decimal(ticker.get("high", current_price)),
                                    low_24h=Decimal(ticker.get("low", current_price)),
                                    last_updated=datetime.utcnow(),
                                    exchange="kucoin"
                                )
                                break
                    
                    return result
                    
        except Exception as e:
            self.logger.error("Failed to fetch KuCoin market data", error=str(e))
            return {}
    
    async def _fetch_coinbase_data(self, symbols: List[str]) -> Dict[str, MarketDataPoint]:
        """Fetch real market data from Coinbase."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get products and stats
                async with session.get(
                    "https://api.exchange.coinbase.com/products",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return {}
                    
                    products = await response.json()
                    result = {}
                    
                    # Get 24hr stats for relevant products
                    for symbol in symbols:
                        product_id = f"{symbol}-USD"
                        
                        # Check if product exists
                        product_exists = any(p["id"] == product_id for p in products)
                        if not product_exists:
                            continue
                        
                        # Get 24hr stats
                        async with session.get(
                            f"https://api.exchange.coinbase.com/products/{product_id}/stats",
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as stats_response:
                            if stats_response.status == 200:
                                stats = await stats_response.json()
                                
                                current_price = float(stats.get("last", 0))
                                open_price = float(stats.get("open", current_price))
                                change_24h = current_price - open_price
                                change_24h_percent = (change_24h / open_price) * 100 if open_price > 0 else 0
                                
                                result[symbol] = MarketDataPoint(
                                    symbol=symbol,
                                    price=Decimal(str(current_price)),
                                    change_24h=change_24h,
                                    change_24h_percent=change_24h_percent,
                                    volume_24h=self._format_volume(float(stats.get("volume", 0))),
                                    high_24h=Decimal(stats.get("high", current_price)),
                                    low_24h=Decimal(stats.get("low", current_price)),
                                    last_updated=datetime.utcnow(),
                                    exchange="coinbase"
                                )
                    
                    return result
                    
        except Exception as e:
            self.logger.error("Failed to fetch Coinbase market data", error=str(e))
            return {}
    
    def _calculate_weighted_average(
        self, 
        symbol: str, 
        data_points: List[MarketDataPoint]
    ) -> Dict[str, Any]:
        """Calculate weighted average of market data from multiple exchanges."""
        if not data_points:
            return {}
        
        total_weight = 0
        weighted_price = 0
        weighted_change = 0
        weighted_volume = 0
        
        # Use exchange weights for averaging
        for point in data_points:
            weight = self.exchange_weights.get(point.exchange, 0.1)
            total_weight += weight
            weighted_price += float(point.price) * weight
            weighted_change += point.change_24h_percent * weight
            
            # Parse volume for weighted calculation
            volume_float = self._parse_volume_string(point.volume_24h)
            weighted_volume += volume_float * weight
        
        if total_weight == 0:
            return {}
        
        # Normalize by total weight
        avg_price = weighted_price / total_weight
        avg_change = weighted_change / total_weight
        avg_volume = weighted_volume / total_weight
        
        # Get high/low from all exchanges
        all_highs = [float(point.high_24h) for point in data_points]
        all_lows = [float(point.low_24h) for point in data_points]
        
        return {
            "symbol": symbol,
            "price": Decimal(str(round(avg_price, 8))),
            "change": round(avg_change, 2),
            "volume": self._format_volume(avg_volume),
            "high_24h": Decimal(str(max(all_highs))),
            "low_24h": Decimal(str(min(all_lows))),
            "exchanges_count": len(data_points),
            "data_quality": "high" if len(data_points) >= 3 else "medium" if len(data_points) >= 2 else "low"
        }
    
    def _format_volume(self, volume: float) -> str:
        """Format volume in human-readable format."""
        if volume >= 1_000_000_000:
            return f"{volume / 1_000_000_000:.1f}B"
        elif volume >= 1_000_000:
            return f"{volume / 1_000_000:.1f}M"
        elif volume >= 1_000:
            return f"{volume / 1_000:.1f}K"
        else:
            return f"{volume:.0f}"
    
    def _parse_volume_string(self, volume_str: str) -> float:
        """Parse volume string back to float for calculations."""
        if volume_str.endswith("B"):
            return float(volume_str[:-1]) * 1_000_000_000
        elif volume_str.endswith("M"):
            return float(volume_str[:-1]) * 1_000_000
        elif volume_str.endswith("K"):
            return float(volume_str[:-1]) * 1_000
        else:
            try:
                return float(volume_str)
            except:
                return 0.0
    
    async def _get_cached_market_data(self, symbols: List[str]) -> Optional[List[Dict[str, Any]]]:
        """Get cached market data if available and fresh."""
        try:
            if not self.redis:
                self.redis = await get_redis_client()
            
            cache_key = f"market_data:{':'.join(sorted(symbols))}"
            cached = await self.redis.get(cache_key)
            
            if cached:
                import json
                return json.loads(cached)
            
            return None
            
        except Exception as e:
            self.logger.warning("Failed to get cached market data", error=str(e))
            return None
    
    async def _cache_market_data(self, market_data: List[Dict[str, Any]]) -> None:
        """Cache market data for performance."""
        try:
            if not self.redis:
                self.redis = await get_redis_client()
            
            symbols = [item["symbol"] for item in market_data]
            cache_key = f"market_data:{':'.join(sorted(symbols))}"
            
            # Convert Decimal to float for JSON serialization
            serializable_data = []
            for item in market_data:
                serializable_item = {}
                for key, value in item.items():
                    if isinstance(value, Decimal):
                        serializable_item[key] = float(value)
                    else:
                        serializable_item[key] = value
                serializable_data.append(serializable_item)
            
            import json
            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(serializable_data)
            )
            
        except Exception as e:
            self.logger.warning("Failed to cache market data", error=str(e))
    
    async def get_real_time_price(self, symbol: str, exchange: Optional[str] = None) -> Dict[str, Any]:
        """
        Get real-time price for a specific symbol.
        
        Args:
            symbol: Symbol to get price for
            exchange: Specific exchange or None for best price
            
        Returns:
            Real-time price data
        """
        try:
            if exchange:
                # Get from specific exchange
                if exchange.lower() == "binance":
                    data = await self._fetch_binance_data([symbol])
                elif exchange.lower() == "kraken":
                    data = await self._fetch_kraken_data([symbol])
                elif exchange.lower() == "kucoin":
                    data = await self._fetch_kucoin_data([symbol])
                else:
                    return {"success": False, "error": f"Exchange {exchange} not supported"}
                
                if symbol in data:
                    point = data[symbol]
                    return {
                        "success": True,
                        "symbol": symbol,
                        "price": float(point.price),
                        "exchange": exchange,
                        "timestamp": point.last_updated.isoformat()
                    }
            else:
                # Get best price from multiple exchanges
                market_data = await self._fetch_aggregated_market_data([symbol])
                if market_data:
                    return {
                        "success": True,
                        "symbol": symbol,
                        "price": float(market_data[0]["price"]),
                        "exchanges_count": market_data[0]["exchanges_count"],
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            return {"success": False, "error": f"No price data found for {symbol}"}
            
        except Exception as e:
            self.logger.error("Failed to get real-time price", error=str(e), symbol=symbol)
            return {"success": False, "error": str(e)}
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive symbol information from multiple exchanges."""
        try:
            # Get symbol info from all exchanges
            tasks = [
                self._get_binance_symbol_info(symbol),
                self._get_kraken_symbol_info(symbol),
                self._get_kucoin_symbol_info(symbol)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            symbol_info = {
                "symbol": symbol,
                "supported_exchanges": [],
                "trading_pairs": [],
                "min_order_sizes": {},
                "fee_structures": {},
                "available": False
            }
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    continue
                
                if result.get("supported"):
                    exchange_name = ["binance", "kraken", "kucoin"][i]
                    symbol_info["supported_exchanges"].append(exchange_name)
                    symbol_info["trading_pairs"].extend(result.get("pairs", []))
                    symbol_info["min_order_sizes"][exchange_name] = result.get("min_order_size")
                    symbol_info["fee_structures"][exchange_name] = result.get("fees")
                    symbol_info["available"] = True
            
            return {
                "success": True,
                "symbol_info": symbol_info,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get symbol info", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _get_binance_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol info from Binance."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.binance.com/api/v3/exchangeInfo",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return {"supported": False}
                    
                    data = await response.json()
                    symbols_data = data.get("symbols", [])
                    
                    # Find symbol pairs
                    pairs = []
                    min_order_size = None
                    fees = {"maker": 0.001, "taker": 0.001}  # Default Binance fees
                    
                    for sym_data in symbols_data:
                        if sym_data["baseAsset"] == symbol and sym_data["status"] == "TRADING":
                            pairs.append(sym_data["symbol"])
                            
                            # Get min order size
                            for filter_item in sym_data.get("filters", []):
                                if filter_item["filterType"] == "LOT_SIZE":
                                    min_order_size = float(filter_item["minQty"])
                                    break
                    
                    return {
                        "supported": len(pairs) > 0,
                        "pairs": pairs,
                        "min_order_size": min_order_size,
                        "fees": fees
                    }
                    
        except Exception as e:
            self.logger.error("Failed to get Binance symbol info", error=str(e))
            return {"supported": False}
    
    async def _get_kraken_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol info from Kraken."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.kraken.com/0/public/AssetPairs",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return {"supported": False}
                    
                    data = await response.json()
                    
                    if data.get("error"):
                        return {"supported": False}
                    
                    pairs_data = data.get("result", {})
                    pairs = []
                    min_order_size = None
                    fees = {"maker": 0.0016, "taker": 0.0026}  # Default Kraken fees
                    
                    # Map symbol to Kraken format
                    kraken_symbol = symbol.replace("BTC", "XBT")
                    
                    for pair_name, pair_data in pairs_data.items():
                        if pair_data.get("base") == kraken_symbol:
                            pairs.append(pair_name)
                            if not min_order_size:
                                min_order_size = float(pair_data.get("ordermin", 0))
                    
                    return {
                        "supported": len(pairs) > 0,
                        "pairs": pairs,
                        "min_order_size": min_order_size,
                        "fees": fees
                    }
                    
        except Exception as e:
            self.logger.error("Failed to get Kraken symbol info", error=str(e))
            return {"supported": False}
    
    async def _get_kucoin_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol info from KuCoin."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.kucoin.com/api/v1/symbols",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return {"supported": False}
                    
                    data = await response.json()
                    
                    if data.get("code") != "200000":
                        return {"supported": False}
                    
                    symbols_data = data.get("data", [])
                    pairs = []
                    min_order_size = None
                    fees = {"maker": 0.001, "taker": 0.001}  # Default KuCoin fees
                    
                    for sym_data in symbols_data:
                        if sym_data.get("baseCurrency") == symbol and sym_data.get("enableTrading"):
                            pairs.append(sym_data["symbol"])
                            if not min_order_size:
                                min_order_size = float(sym_data.get("baseMinSize", 0))
                    
                    return {
                        "supported": len(pairs) > 0,
                        "pairs": pairs,
                        "min_order_size": min_order_size,
                        "fees": fees
                    }
                    
        except Exception as e:
            self.logger.error("Failed to get KuCoin symbol info", error=str(e))
            return {"supported": False}


# Global service instance
real_market_data_service = RealMarketDataService()


# FastAPI dependency
async def get_real_market_data_service() -> RealMarketDataService:
    """Dependency injection for FastAPI."""
    return real_market_data_service