"""
Enterprise Real Market Data Service
Production-grade market data integration with CCXT

This service provides:
- Real-time price feeds from multiple exchanges
- Historical OHLCV data with caching
- Order book depth for realistic simulations
- Multi-exchange aggregation
- Automatic failover and retry logic
"""

import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
import json
import hashlib
import time
from decimal import Decimal

import structlog
from app.core.redis import redis_manager
from app.core.logging import LoggerMixin

logger = structlog.get_logger(__name__)


class RealMarketDataService(LoggerMixin):
    """
    Enterprise-grade market data service with real exchange connectivity.
    """

    def __init__(self):
        """Initialize with multiple exchange connections for redundancy."""
        self.exchanges = {}
        self.cache_ttl = {
            'ticker': 10,      # 10 seconds for real-time prices
            'ohlcv': 300,      # 5 minutes for candles
            'orderbook': 5,    # 5 seconds for order books
            'historical': 3600 # 1 hour for historical data
        }
        self._initialize_exchanges()

    def _initialize_exchanges(self):
        """Initialize CCXT exchange connections."""
        try:
            # Initialize multiple exchanges for redundancy
            self.exchanges['binance'] = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True
                }
            })

            self.exchanges['kucoin'] = ccxt.kucoin({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True
                }
            })

            self.exchanges['kraken'] = ccxt.kraken({
                'enableRateLimit': True,
                'options': {
                    'adjustForTimeDifference': True  # Fix nonce errors from time sync issues
                }
            })

            # Coinbase for US market
            self.exchanges['coinbase'] = ccxt.coinbase({
                'enableRateLimit': True,
                'options': {
                    'adjustForTimeDifference': True
                }
            })

            self.logger.info("✅ Initialized real market data connections",
                           exchanges=list(self.exchanges.keys()))

        except Exception as e:
            self.logger.error("Failed to initialize exchanges", error=str(e))
            # Fallback to at least one exchange
            self.exchanges['binance'] = ccxt.binance({'enableRateLimit': True})

    async def get_real_price(
        self,
        symbol: str,
        exchange: str = 'auto'
    ) -> Dict[str, Any]:
        """
        Get real-time price from actual exchanges.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            exchange: Specific exchange or 'auto' for best available

        Returns:
            Real price data with metadata
        """
        cache_key = f"price:{exchange}:{symbol}"

        # Check cache first
        cached = await self._get_cached_data(cache_key)
        if cached:
            return cached

        # Normalize symbol for CCXT format
        ccxt_symbol = self._normalize_symbol(symbol)

        # Auto-select exchange or use specific one
        if exchange == 'auto':
            exchange_list = ['binance', 'coinbase', 'kucoin', 'kraken']
        else:
            exchange_list = [exchange]

        for exch_name in exchange_list:
            if exch_name not in self.exchanges:
                continue

            try:
                exchange_obj = self.exchanges[exch_name]

                if exch_name == 'kraken':
                    def _build_monotonic_nonce(initial_seed: int) -> Callable[[], int]:
                        last_value = max(int(initial_seed), int(time.time() * 1000))

                        def _next_nonce() -> int:
                            nonlocal last_value
                            current = int(time.time() * 1000)
                            if current <= last_value:
                                last_value += 1
                            else:
                                last_value = current
                            return last_value

                        return _next_nonce

                    try:
                        seed = await self._get_kraken_nonce()
                        exchange_obj.nonce = _build_monotonic_nonce(int(seed))
                    except asyncio.CancelledError:
                        raise
                    except Exception as nonce_error:
                        fallback_seed = int(time.time() * 1000)
                        exchange_obj.nonce = _build_monotonic_nonce(fallback_seed)
                        self.logger.warning(
                            "Kraken nonce generation fallback in use",
                            error=str(nonce_error)
                        )

                # Fetch real ticker data with enterprise-grade error handling
                ticker = await exchange_obj.fetch_ticker(ccxt_symbol)
                
                # Validate ticker data before processing
                if not self._validate_market_data(ticker, "ticker"):
                    self.logger.warning(
                        f"Invalid ticker data received from {exch_name}",
                        symbol=symbol,
                        ticker_preview=str(ticker)[:200]
                    )
                    continue

                # Safely extract ticker values with fallbacks
                last_price = ticker.get('last') or ticker.get('close') or 0
                last_price = float(last_price) if last_price else 0

                bid_val = ticker.get('bid') or last_price or 0
                bid_price = float(bid_val) if bid_val else 0

                ask_val = ticker.get('ask') or last_price or 0
                ask_price = float(ask_val) if ask_val else 0

                # Always convert to quote volume for consistency
                quote_volume = ticker.get('quoteVolume')
                base_volume = ticker.get('baseVolume')

                if quote_volume:
                    volume_24h = float(quote_volume)
                elif base_volume and last_price:
                    # Convert base volume to quote volume
                    volume_24h = float(base_volume) * last_price
                else:
                    volume_24h = 0

                change_val = ticker.get('percentage') or ticker.get('change') or 0
                change_24h = float(change_val) if change_val else 0

                high_val = ticker.get('high') or last_price or 0
                high_24h = float(high_val) if high_val else 0

                low_val = ticker.get('low') or last_price or 0
                low_24h = float(low_val) if low_val else 0

                price_data = {
                    'symbol': symbol,
                    'price': last_price,
                    'bid': bid_price,
                    'ask': ask_price,
                    'volume_24h': volume_24h,
                    'change_24h': change_24h,
                    'high_24h': high_24h,
                    'low_24h': low_24h,
                    'exchange': exch_name,
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': 'real_market_data'
                }

                # Cache the result
                await self._cache_data(cache_key, price_data, self.cache_ttl['ticker'])

                self.logger.info(f"✅ Fetched real price for {symbol}: ${price_data['price']:.2f}")
                return price_data

            except Exception as e:
                self.logger.warning(f"Failed to fetch from {exch_name}: {str(e)}")
                continue

        # If all exchanges fail, return error
        self.logger.error(f"❌ Could not fetch real price for {symbol}")
        return {
            'symbol': symbol,
            'price': 0,
            'error': 'All exchanges failed',
            'source': 'real_market_data'
        }

    async def get_historical_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100,
        exchange: str = 'binance'
    ) -> List[Dict[str, Any]]:
        """
        Fetch real historical OHLCV data from exchanges.

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch
            exchange: Exchange to use

        Returns:
            List of OHLCV candles
        """
        cache_key = f"ohlcv:{exchange}:{symbol}:{timeframe}:{limit}"

        # Check cache
        cached = await self._get_cached_data(cache_key)
        if cached:
            return cached

        try:
            if exchange not in self.exchanges:
                exchange = 'binance'  # Default fallback

            exchange_obj = self.exchanges[exchange]
            ccxt_symbol = self._normalize_symbol(symbol)

            # Fetch real OHLCV data with enterprise-grade error handling
            ohlcv_raw = await exchange_obj.fetch_ohlcv(
                ccxt_symbol,
                timeframe,
                limit=limit
            )
            
            # Validate OHLCV data before processing
            if not self._validate_market_data(ohlcv_raw, "ohlcv"):
                self.logger.warning(
                    f"Invalid OHLCV data received from {exchange}",
                    symbol=symbol,
                    timeframe=timeframe,
                    data_preview=str(ohlcv_raw)[:200]
                )
                # Fallback to price-based single candle
                price_data = await self.get_real_price(symbol, exchange)
                if price_data.get('price', 0) > 0:
                    current_price = price_data['price']
                    return [{
                        'timestamp': datetime.utcnow().isoformat(),
                        'open': current_price,
                        'high': current_price * 1.01,
                        'low': current_price * 0.99,
                        'close': current_price,
                        'volume': 1000.0
                    }]
                else:
                    raise Exception("Failed to get fallback price data")

            # Enterprise-grade OHLCV parsing with robust error handling
            ohlcv_data = []
            for i, candle in enumerate(ohlcv_raw):
                try:
                    if isinstance(candle, (list, tuple)) and len(candle) >= 6:
                        # Standard OHLCV format: [timestamp, open, high, low, close, volume, ...]
                        ohlcv_data.append({
                            'timestamp': datetime.fromtimestamp(candle[0]/1000).isoformat(),
                            'open': float(candle[1]),
                            'high': float(candle[2]),
                            'low': float(candle[3]),
                            'close': float(candle[4]),
                            'volume': float(candle[5])
                        })
                    elif isinstance(candle, dict):
                        # Dictionary format: {'timestamp': x, 'open': y, ...}
                        timestamp = candle.get('timestamp', 0)
                        if isinstance(timestamp, (int, float)):
                            timestamp = datetime.fromtimestamp(timestamp/1000).isoformat()
                        elif isinstance(timestamp, str):
                            timestamp = timestamp
                        else:
                            timestamp = datetime.utcnow().isoformat()
                        
                        ohlcv_data.append({
                            'timestamp': timestamp,
                            'open': float(candle.get('open', 0)),
                            'high': float(candle.get('high', 0)),
                            'low': float(candle.get('low', 0)),
                            'close': float(candle.get('close', 0)),
                            'volume': float(candle.get('volume', 0))
                        })
                    else:
                        self.logger.warning(
                            f"Unexpected OHLCV candle format",
                            candle_index=i,
                            candle_type=type(candle).__name__,
                            candle_preview=str(candle)[:100]
                        )
                        continue
                except (ValueError, TypeError, IndexError, KeyError) as e:
                    self.logger.warning(
                        f"Failed to parse OHLCV candle",
                        candle_index=i,
                        error=str(e),
                        candle_preview=str(candle)[:100]
                    )
                    continue

            # Cache the result
            await self._cache_data(cache_key, ohlcv_data, self.cache_ttl['ohlcv'])

            self.logger.info(f"✅ Fetched {len(ohlcv_data)} real candles for {symbol}")
            return ohlcv_data

        except Exception as e:
            self.logger.error(f"Failed to fetch OHLCV data", error=str(e))

            # Return at least current price as single candle
            price_data = await self.get_real_price(symbol, exchange)
            if price_data.get('price', 0) > 0:
                current_price = price_data['price']
                return [{
                    'timestamp': datetime.utcnow().isoformat(),
                    'open': current_price,
                    'high': current_price * 1.01,
                    'low': current_price * 0.99,
                    'close': current_price,
                    'volume': price_data.get('volume_24h', 1000000)
                }]

            return []

    async def get_order_book(
        self,
        symbol: str,
        exchange: str = 'binance',
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get real order book depth for accurate simulation.

        Args:
            symbol: Trading pair
            exchange: Exchange to use
            limit: Depth of order book

        Returns:
            Order book with bids and asks
        """
        cache_key = f"orderbook:{exchange}:{symbol}"

        # Check cache
        cached = await self._get_cached_data(cache_key)
        if cached:
            return cached

        try:
            if exchange not in self.exchanges:
                exchange = 'binance'

            exchange_obj = self.exchanges[exchange]
            ccxt_symbol = self._normalize_symbol(symbol)

            # Fetch real order book with enterprise-grade error handling
            orderbook = await exchange_obj.fetch_order_book(ccxt_symbol, limit)
            
            # Validate order book data before processing
            if not self._validate_market_data(orderbook, "orderbook"):
                self.logger.warning(
                    f"Invalid order book data received from {exchange}",
                    symbol=symbol,
                    data_preview=str(orderbook)[:200]
                )
                # Fallback to synthetic order book
                price_data = await self.get_real_price(symbol, exchange)
                if price_data.get('price', 0) > 0:
                    return self._generate_synthetic_orderbook(
                        price_data['price'], symbol, exchange, limit
                    )
                else:
                    raise Exception("Failed to get fallback price data")

            # Enterprise-grade order book parsing with robust error handling
            def _parse_order_book_levels(levels: List, level_type: str) -> List[List[float]]:
                """Safely parse order book levels with comprehensive error handling."""
                parsed_levels = []
                for i, level in enumerate(levels[:limit]):
                    try:
                        if isinstance(level, (list, tuple)) and len(level) >= 2:
                            # Standard format: [price, amount, ...]
                            price = float(level[0])
                            amount = float(level[1])
                            parsed_levels.append([price, amount])
                        elif isinstance(level, dict):
                            # Dictionary format: {'price': x, 'amount': y, ...}
                            price = float(level.get('price', 0))
                            amount = float(level.get('amount', 0))
                            if price > 0 and amount > 0:
                                parsed_levels.append([price, amount])
                        else:
                            self.logger.warning(
                                f"Unexpected order book level format for {level_type}",
                                level_index=i,
                                level_type=type(level).__name__,
                                level_preview=str(level)[:100]
                            )
                    except (ValueError, TypeError, IndexError) as e:
                        self.logger.warning(
                            f"Failed to parse order book level for {level_type}",
                            level_index=i,
                            error=str(e),
                            level_preview=str(level)[:100]
                        )
                        continue
                
                return parsed_levels

            result = {
                'symbol': symbol,
                'bids': _parse_order_book_levels(orderbook.get('bids', []), 'bids'),
                'asks': _parse_order_book_levels(orderbook.get('asks', []), 'asks'),
                'timestamp': orderbook.get('timestamp', datetime.utcnow().timestamp() * 1000),
                'exchange': exchange,
                'source': 'real_order_book'
            }

            # Cache the result
            await self._cache_data(cache_key, result, self.cache_ttl['orderbook'])

            return result

        except Exception as e:
            self.logger.error(f"Failed to fetch order book", error=str(e))

            # Fallback to price-based synthetic order book
            price_data = await self.get_real_price(symbol, exchange)
            if price_data.get('price', 0) > 0:
                return self._generate_synthetic_orderbook(price_data['price'], symbol, exchange, limit)

            # Return consistent structure even on complete failure
            return {
                'symbol': symbol,
                'bids': [],
                'asks': [],
                'timestamp': datetime.utcnow().timestamp() * 1000,
                'exchange': exchange,
                'source': 'fallback_empty',
                'error': str(e)
            }

    async def get_aggregated_price(
        self,
        symbol: str,
        exchanges: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get volume-weighted average price across multiple exchanges.

        Args:
            symbol: Trading pair
            exchanges: List of exchanges to aggregate

        Returns:
            Aggregated price data
        """
        if not exchanges:
            exchanges = ['binance', 'coinbase', 'kucoin']

        prices = []
        volumes = []

        # Fetch from multiple exchanges in parallel
        tasks = [self.get_real_price(symbol, exch) for exch in exchanges]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, dict) and result.get('price', 0) > 0:
                prices.append(result['price'])
                # Use consistent quote volume from get_real_price (converted if needed)
                volumes.append(result.get('volume_24h', 1))

        if not prices:
            return {'error': 'No valid prices found'}

        # Calculate volume-weighted average price using consistent quote volumes
        total_volume = sum(volumes)
        vwap = sum(p * v for p, v in zip(prices, volumes)) / total_volume if total_volume > 0 else np.mean(prices)

        return {
            'symbol': symbol,
            'vwap': float(vwap),
            'min_price': min(prices),
            'max_price': max(prices),
            'spread_pct': ((max(prices) - min(prices)) / min(prices) * 100) if min(prices) > 0 else 0,
            'exchanges_count': len(prices),
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'aggregated_real_data'
        }

    async def get_market_depth_analysis(
        self,
        symbol: str,
        exchange: str = 'binance'
    ) -> Dict[str, Any]:
        """
        Analyze market depth for better execution simulation.

        Returns:
            Market depth metrics including liquidity and spread
        """
        orderbook = await self.get_order_book(symbol, exchange, limit=50)

        if not orderbook.get('bids') or not orderbook.get('asks'):
            return {'error': 'No orderbook data'}

        bids = orderbook['bids']
        asks = orderbook['asks']

        # Calculate metrics
        best_bid = bids[0][0] if bids else 0
        best_ask = asks[0][0] if asks else 0
        spread = best_ask - best_bid
        spread_pct = (spread / best_bid * 100) if best_bid > 0 else 0

        # Calculate liquidity at different levels
        bid_liquidity_1pct = sum(amount for price, amount in bids if price >= best_bid * 0.99)
        ask_liquidity_1pct = sum(amount for price, amount in asks if price <= best_ask * 1.01)

        # Market pressure indicator
        bid_volume = sum(amount for _, amount in bids[:10])
        ask_volume = sum(amount for _, amount in asks[:10])
        pressure = (bid_volume - ask_volume) / (bid_volume + ask_volume) if (bid_volume + ask_volume) > 0 else 0

        return {
            'symbol': symbol,
            'best_bid': best_bid,
            'best_ask': best_ask,
            'spread': spread,
            'spread_pct': spread_pct,
            'bid_liquidity_1pct': bid_liquidity_1pct,
            'ask_liquidity_1pct': ask_liquidity_1pct,
            'market_pressure': pressure,  # Positive = buying pressure
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'real_market_depth'
        }

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol to CCXT's expected ``BASE/QUOTE`` format with enterprise-grade error handling."""

        if not symbol:
            return "BTC/USDT"

        try:
            cleaned_symbol = symbol.upper().strip()

            if "/" in cleaned_symbol:
                # Enterprise-grade symbol splitting with comprehensive error handling
                parts = cleaned_symbol.split("/")
                if len(parts) == 2:
                    base, quote = parts
                    base = base.replace("-", "").replace("_", "").strip()
                    quote = quote.replace("-", "").replace("_", "").strip() or "USDT"
                    return f"{base}/{quote}"
                else:
                    # Handle multiple slashes by taking first and last parts
                    self.logger.warning(
                        f"Symbol contains multiple slashes, using first and last parts",
                        original_symbol=symbol,
                        parts=parts
                    )
                    base = parts[0].replace("-", "").replace("_", "").strip()
                    quote = parts[-1].replace("-", "").replace("_", "").strip() or "USDT"
                    return f"{base}/{quote}"

            collapsed = cleaned_symbol.replace("-", "").replace("_", "")

            known_quotes = ["USDT", "USD", "USDC", "BTC", "ETH", "EUR"]
            for quote in known_quotes:
                if collapsed.endswith(quote) and len(collapsed) > len(quote):
                    base = collapsed[: -len(quote)]
                    return f"{base}/{quote}"

            return f"{collapsed}/USDT"
            
        except Exception as e:
            self.logger.error(
                f"Failed to normalize symbol, using fallback",
                original_symbol=symbol,
                error=str(e)
            )
            return "BTC/USDT"

    def _validate_market_data(self, data: Any, data_type: str) -> bool:
        """Enterprise-grade data validation for market data."""
        try:
            if data_type == "ticker":
                return (
                    isinstance(data, dict) and
                    any(key in data for key in ['last', 'close', 'bid', 'ask']) and
                    any(isinstance(data.get(key), (int, float)) for key in ['last', 'close', 'bid', 'ask'])
                )
            elif data_type == "ohlcv":
                return (
                    isinstance(data, list) and
                    len(data) > 0 and
                    all(isinstance(candle, (list, tuple, dict)) for candle in data)
                )
            elif data_type == "orderbook":
                return (
                    isinstance(data, dict) and
                    'bids' in data and 'asks' in data and
                    isinstance(data['bids'], list) and isinstance(data['asks'], list)
                )
            return False
        except Exception as e:
            self.logger.error(f"Data validation failed for {data_type}", error=str(e))
            return False

    def _generate_synthetic_orderbook(
        self,
        mid_price: float,
        symbol: str,
        exchange: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Generate realistic order book when real data unavailable.

        Creates a synthetic order book with realistic spread and depth,
        matching the exact structure of the primary path.

        Args:
            mid_price: Middle price for synthetic book
            symbol: Trading pair symbol
            exchange: Exchange name
            limit: Number of levels to generate
        """
        bids = []
        asks = []

        # Generate bids (buy orders) up to requested limit
        for i in range(limit):
            price_level = mid_price * (1 - 0.0001 * (i + 1))  # 0.01% steps
            volume = np.random.exponential(1000) * (limit - i) / limit  # Decreasing volume
            bids.append([float(price_level), float(volume)])

        # Generate asks (sell orders) up to requested limit
        for i in range(limit):
            price_level = mid_price * (1 + 0.0001 * (i + 1))  # 0.01% steps
            volume = np.random.exponential(1000) * (limit - i) / limit  # Decreasing volume
            asks.append([float(price_level), float(volume)])

        # Return exact same structure as primary path
        return {
            'symbol': symbol,
            'bids': bids,
            'asks': asks,
            'timestamp': datetime.utcnow().timestamp() * 1000,
            'exchange': exchange,
            'source': 'synthetic_orderbook'
        }

    async def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get data from Redis cache."""
        try:
            redis = await redis_manager.get_client()
            if not redis:
                return None

            data = await redis.get(f"market_data:{key}")
            if data:
                return json.loads(data)
        except Exception as e:
            self.logger.debug(f"Cache miss for {key}: {str(e)}")

        return None

    async def _cache_data(self, key: str, data: Any, ttl: int):
        """Store data in Redis cache."""
        try:
            redis = await redis_manager.get_client()
            if redis:
                await redis.setex(
                    f"market_data:{key}",
                    ttl,
                    json.dumps(data, default=str)
                )
        except Exception as e:
            self.logger.debug(f"Failed to cache {key}: {str(e)}")

    async def _get_kraken_nonce(self) -> int:
        """Generate a Kraken API nonce with Redis coordination and time-based fallback."""

        try:
            redis = await redis_manager.get_client()
            if redis:
                nonce_value = await redis.incr("kraken_nonce")
                if nonce_value:
                    return int(nonce_value)
        except Exception as redis_error:
            self.logger.warning(
                "Redis unavailable for Kraken nonce",
                error=str(redis_error)
            )

        return int(time.time() * 1000)

    async def close(self):
        """Clean up exchange connections."""
        for exchange in self.exchanges.values():
            try:
                await exchange.close()
            except:
                pass


# Global service instance
real_market_data_service = RealMarketDataService()


async def get_real_market_data_service() -> RealMarketDataService:
    """Dependency injection for FastAPI."""
    return real_market_data_service
