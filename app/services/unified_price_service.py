"""
Unified Price Service - Single Source of Truth for USD Prices

Eliminates duplication between market analysis and exchange integration
by providing intelligent routing between different price data sources.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import structlog

from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.core.logging import LoggerMixin

settings = get_settings()
logger = structlog.get_logger(__name__)


class PriceSource(str, Enum):
    """Price data source options."""
    AUTO = "auto"                    # Smart selection based on symbol and use case
    MARKET_DATA = "market_data"      # CoinGecko, Alpha Vantage, Finnhub, CoinCap
    EXCHANGE = "exchange"            # Exchange ticker APIs (Binance, KuCoin, etc.)
    CACHED = "cached"                # Redis cache only


class UnifiedPriceService(LoggerMixin):
    """
    Unified price service with intelligent source routing.
    
    Features:
    - Smart source selection (market data vs exchange APIs)
    - Redis caching with appropriate TTL
    - Fallback mechanisms between sources
    - Batch price fetching for efficiency
    - Rate limit awareness
    - Error handling and logging
    """
    
    def __init__(self):
        self.redis = None
        self.market_data_feeds = None
        self.exchange_apis = None
        
        # Cache TTL settings
        self.cache_ttl = {
            "market_data": 60,    # 1 minute for market data (comprehensive)
            "exchange": 30,       # 30 seconds for exchange data (more current)
            "fallback": 300,      # 5 minutes for fallback data
            "stablecoin": 3600    # 1 hour for stablecoins (always ~$1)
        }
        
        # Stablecoin mapping
        self.stablecoins = {
            "USDT": 1.0,
            "USDC": 1.0,
            "BUSD": 1.0,
            "DAI": 1.0,
            "TUSD": 1.0
        }
        
        # Major coins that have better market data coverage
        self.major_coins = [
            "BTC", "ETH", "SOL", "ADA", "DOT", "MATIC", "LINK", "UNI", "AVAX", "ATOM"
        ]
    
    async def async_init(self):
        """Initialize Redis and import services."""
        try:
            self.redis = await get_redis_client()
            
            # Import market analysis service
            try:
                from app.services.market_data_feeds import market_data_feeds
                self.market_data_feeds = market_data_feeds
                await self.market_data_feeds.async_init()
                logger.info("Market data feeds initialized for unified price service")
            except ImportError as e:
                logger.warning("Market data feeds not available", error=str(e))
            
            # Import exchange price functions
            try:
                # Import the exchange price functions dynamically to avoid circular imports
                import importlib
                exchanges_module = importlib.import_module("app.api.v1.endpoints.exchanges")
                
                if hasattr(exchanges_module, 'get_binance_prices'):
                    self.exchange_apis = {
                        "binance": exchanges_module.get_binance_prices
                    }
                    logger.info("Exchange APIs initialized for unified price service")
                else:
                    logger.warning("Exchange price functions not found")
                    
            except Exception as e:
                logger.warning("Exchange APIs not available", error=str(e))
                
        except Exception as e:
            logger.error("Failed to initialize unified price service", error=str(e))
    
    async def get_usd_price(
        self, 
        symbol: str, 
        source: PriceSource = PriceSource.AUTO,
        max_age_seconds: int = 60,
        use_case: str = "general"
    ) -> Optional[float]:
        """
        Get USD price for a single symbol with intelligent source selection.
        
        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            source: Preferred price source
            max_age_seconds: Maximum age for cached data
            use_case: "market_analysis", "portfolio", "general"
            
        Returns:
            USD price as float, or None if not available
        """
        # Handle stablecoins immediately
        if symbol.upper() in self.stablecoins:
            return self.stablecoins[symbol.upper()]
        
        cache_key = f"unified_price:{symbol.upper()}"
        
        # Try cache first unless specifically requesting fresh exchange data
        if source != PriceSource.EXCHANGE or max_age_seconds > 0:
            cached_price = await self._get_cached_price(cache_key, max_age_seconds)
            if cached_price is not None:
                return cached_price
        
        # Smart source selection
        if source == PriceSource.AUTO:
            source = self._select_optimal_source(symbol, use_case)
        
        # Fetch from selected source with fallback
        price = await self._fetch_from_source(symbol, source)
        
        if price is not None:
            # Cache the result
            await self._cache_price(cache_key, price, source)
            return price
        
        # Final fallback - try any available source
        return await self._fetch_with_fallback(symbol)
    
    async def get_batch_prices(
        self, 
        symbols: List[str], 
        source: PriceSource = PriceSource.AUTO,
        use_case: str = "general"
    ) -> Dict[str, float]:
        """
        Get USD prices for multiple symbols efficiently.
        
        Args:
            symbols: List of crypto symbols
            source: Preferred price source
            use_case: "market_analysis", "portfolio", "general"
            
        Returns:
            Dictionary mapping symbols to USD prices
        """
        if not symbols:
            return {}
        
        # Handle stablecoins immediately
        results = {}
        remaining_symbols = []
        
        for symbol in symbols:
            if symbol.upper() in self.stablecoins:
                results[symbol] = self.stablecoins[symbol.upper()]
            else:
                remaining_symbols.append(symbol)
        
        if not remaining_symbols:
            return results
        
        # Smart source selection for batch
        if source == PriceSource.AUTO:
            # For portfolio use case, prefer exchange data for accuracy
            # For market analysis, prefer market data for comprehensiveness
            if use_case == "portfolio" and self.exchange_apis:
                source = PriceSource.EXCHANGE
            elif use_case == "market_analysis" and self.market_data_feeds:
                source = PriceSource.MARKET_DATA
            else:
                source = PriceSource.MARKET_DATA if self.market_data_feeds else PriceSource.EXCHANGE
        
        # Try batch fetching from preferred source
        batch_results = await self._fetch_batch_from_source(remaining_symbols, source)
        results.update(batch_results)
        
        # Fill in missing prices with fallback
        missing_symbols = [s for s in remaining_symbols if s not in results]
        if missing_symbols:
            fallback_results = await self._fetch_batch_fallback(missing_symbols, source)
            results.update(fallback_results)
        
        return results
    
    def _select_optimal_source(self, symbol: str, use_case: str) -> PriceSource:
        """Smart source selection based on symbol, use case, and availability."""
        # For portfolio valuation, prefer exchange data (more accurate for user holdings)
        if use_case == "portfolio" and self.exchange_apis:
            return PriceSource.EXCHANGE
        
        # For market analysis, prefer market data (more comprehensive)
        if use_case == "market_analysis" and self.market_data_feeds:
            return PriceSource.MARKET_DATA
        
        # For major coins, prefer market data (better coverage)
        if symbol.upper() in self.major_coins and self.market_data_feeds:
            return PriceSource.MARKET_DATA
        
        # Default fallback
        return PriceSource.MARKET_DATA if self.market_data_feeds else PriceSource.EXCHANGE
    
    async def _fetch_from_source(self, symbol: str, source: PriceSource) -> Optional[float]:
        """Fetch price from specified source."""
        try:
            if source == PriceSource.MARKET_DATA and self.market_data_feeds:
                data = await self.market_data_feeds.get_real_time_price(symbol)
                if data and data.get("success"):
                    price_data = data.get("data", {})
                    return float(price_data.get("price", 0)) if price_data.get("price") else None
                    
            elif source == PriceSource.EXCHANGE and self.exchange_apis:
                # Use Binance as primary exchange source
                if "binance" in self.exchange_apis:
                    prices = await self.exchange_apis["binance"]([symbol])
                    return prices.get(symbol)
                
        except Exception as e:
            self.logger.warning(f"Failed to fetch {symbol} from {source}", error=str(e))
        
        return None
    
    async def _fetch_batch_from_source(self, symbols: List[str], source: PriceSource) -> Dict[str, float]:
        """Fetch multiple prices from specified source."""
        try:
            if source == PriceSource.MARKET_DATA and self.market_data_feeds:
                data = await self.market_data_feeds.get_multiple_prices(symbols)
                if data and data.get("success"):
                    results = {}
                    data_dict = data.get("data", {})
                    for symbol, symbol_data in data_dict.items():
                        if symbol_data and symbol_data.get("price"):
                            results[symbol] = float(symbol_data["price"])
                    return results
                    
            elif source == PriceSource.EXCHANGE and self.exchange_apis:
                # Use Binance for batch fetching
                if "binance" in self.exchange_apis:
                    return await self.exchange_apis["binance"](symbols)
                
        except Exception as e:
            self.logger.warning(f"Failed to fetch batch prices from {source}", error=str(e))
        
        return {}
    
    async def _fetch_with_fallback(self, symbol: str) -> Optional[float]:
        """Try all available sources as fallback."""
        sources = []
        
        if self.market_data_feeds:
            sources.append(PriceSource.MARKET_DATA)
        if self.exchange_apis:
            sources.append(PriceSource.EXCHANGE)
        
        for source in sources:
            price = await self._fetch_from_source(symbol, source)
            if price is not None:
                self.logger.info(f"Fallback successful for {symbol} using {source}")
                return price
        
        self.logger.error(f"All price sources failed for {symbol}")
        return None
    
    async def _fetch_batch_fallback(self, symbols: List[str], primary_source: PriceSource) -> Dict[str, float]:
        """Fetch missing symbols using fallback sources."""
        results = {}
        
        # Try the other source as fallback
        fallback_source = (
            PriceSource.EXCHANGE if primary_source == PriceSource.MARKET_DATA 
            else PriceSource.MARKET_DATA
        )
        
        fallback_results = await self._fetch_batch_from_source(symbols, fallback_source)
        results.update(fallback_results)
        
        # For any still missing, try individual fallback
        still_missing = [s for s in symbols if s not in results]
        for symbol in still_missing:
            price = await self._fetch_with_fallback(symbol)
            if price is not None:
                results[symbol] = price
        
        return results
    
    async def _get_cached_price(self, cache_key: str, max_age_seconds: int) -> Optional[float]:
        """Get price from Redis cache if not too old."""
        try:
            cached_data = await self.redis.hgetall(cache_key)
            if cached_data:
                timestamp = float(cached_data.get("timestamp", 0))
                age = datetime.utcnow().timestamp() - timestamp
                
                if age <= max_age_seconds:
                    return float(cached_data.get("price"))
        except Exception as e:
            self.logger.warning("Cache read failed", error=str(e))
        
        return None
    
    async def _cache_price(self, cache_key: str, price: float, source: PriceSource):
        """Cache price in Redis with appropriate TTL."""
        try:
            ttl = self.cache_ttl.get(source.value, 60)
            
            await self.redis.hset(cache_key, {
                "price": str(price),
                "timestamp": str(datetime.utcnow().timestamp()),
                "source": source.value
            })
            await self.redis.expire(cache_key, ttl)
            
        except Exception as e:
            self.logger.warning("Cache write failed", error=str(e))
    
    async def get_price_with_metadata(self, symbol: str, source: PriceSource = PriceSource.AUTO) -> Dict[str, Any]:
        """Get price with additional metadata about source and freshness."""
        cache_key = f"unified_price:{symbol.upper()}"
        
        # Get cached metadata
        cached_data = await self.redis.hgetall(cache_key) if self.redis else {}
        
        price = await self.get_usd_price(symbol, source)
        
        return {
            "symbol": symbol.upper(),
            "price_usd": price,
            "source": cached_data.get("source", source.value),
            "timestamp": datetime.utcnow().isoformat(),
            "cached": bool(cached_data),
            "cache_age_seconds": (
                datetime.utcnow().timestamp() - float(cached_data.get("timestamp", 0))
                if cached_data.get("timestamp") else 0
            )
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all price sources."""
        health = {
            "service": "unified_price_service",
            "status": "HEALTHY",
            "sources": {},
            "test_results": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Test market data feeds
        if self.market_data_feeds:
            try:
                test_result = await self.market_data_feeds.get_real_time_price("BTC")
                health["sources"]["market_data"] = {
                    "available": True,
                    "status": "HEALTHY" if test_result.get("success") else "DEGRADED",
                    "last_test": datetime.utcnow().isoformat()
                }
                health["test_results"]["market_data"] = test_result.get("success", False)
            except Exception as e:
                health["sources"]["market_data"] = {
                    "available": False,
                    "status": "UNHEALTHY",
                    "error": str(e),
                    "last_test": datetime.utcnow().isoformat()
                }
                health["test_results"]["market_data"] = False
        else:
            health["sources"]["market_data"] = {
                "available": False,
                "status": "NOT_CONFIGURED",
                "last_test": datetime.utcnow().isoformat()
            }
        
        # Test exchange APIs
        if self.exchange_apis:
            try:
                test_prices = await self.exchange_apis["binance"](["BTC"])
                health["sources"]["exchange"] = {
                    "available": True,
                    "status": "HEALTHY" if test_prices.get("BTC") else "DEGRADED",
                    "last_test": datetime.utcnow().isoformat()
                }
                health["test_results"]["exchange"] = bool(test_prices.get("BTC"))
            except Exception as e:
                health["sources"]["exchange"] = {
                    "available": False,
                    "status": "UNHEALTHY",
                    "error": str(e),
                    "last_test": datetime.utcnow().isoformat()
                }
                health["test_results"]["exchange"] = False
        else:
            health["sources"]["exchange"] = {
                "available": False,
                "status": "NOT_CONFIGURED",
                "last_test": datetime.utcnow().isoformat()
            }
        
        # Determine overall health
        if not any(health["test_results"].values()):
            health["status"] = "UNHEALTHY"
        elif all(health["test_results"].values()):
            health["status"] = "HEALTHY"
        else:
            health["status"] = "DEGRADED"
        
        return health


# Global instance
unified_price_service = UnifiedPriceService()


# Convenience functions for backward compatibility
async def get_crypto_price(symbol: str, use_case: str = "general") -> Optional[float]:
    """Get USD price for a single cryptocurrency."""
    return await unified_price_service.get_usd_price(symbol, use_case=use_case)


async def get_crypto_prices(symbols: List[str], use_case: str = "general") -> Dict[str, float]:
    """Get USD prices for multiple cryptocurrencies."""
    return await unified_price_service.get_batch_prices(symbols, use_case=use_case)


async def get_market_overview_prices() -> Dict[str, float]:
    """Get prices for market overview (optimized for market analysis)."""
    top_symbols = ["BTC", "ETH", "SOL", "ADA", "DOT", "MATIC", "LINK", "UNI"]
    return await unified_price_service.get_batch_prices(
        top_symbols, 
        source=PriceSource.MARKET_DATA,
        use_case="market_analysis"
    )


async def get_portfolio_prices(symbols: List[str]) -> Dict[str, float]:
    """Get prices for portfolio valuation (optimized for accuracy)."""
    return await unified_price_service.get_batch_prices(
        symbols,
        source=PriceSource.AUTO,  # Will prefer exchange data for portfolio
        use_case="portfolio"
    )