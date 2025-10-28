"""
Market Data Feeds - Real Free APIs

Provides real-time market data using free APIs like CoinGecko, CoinCap,
and other free sources for the AI money manager platform.
"""

import asyncio
import copy
import json
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple

import aiohttp
import numpy as np
import structlog
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.core.supabase import supabase_client
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerError
from app.services.market_data_profiles import (
    DEFI_PROTOCOL_MAPPINGS,
    get_asset_profile,
    get_yield_products,
)

settings = get_settings()
logger = structlog.get_logger(__name__)


# Custom exceptions for market data operations
class MarketDataError(Exception):
    """Base exception for market data operations."""
    pass


class MarketDataRateLimitError(MarketDataError):
    """Raised when API rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(message)


class MarketDataBatchFetchError(MarketDataError):
    """Raised when batch price fetching fails after all retries."""
    def __init__(self, message: str, attempts: int = 0):
        self.attempts = attempts
        super().__init__(message)


class MarketDataFeeds:
    """Real market data feeds using free APIs."""
    
    def __init__(self):
        self.redis = None
        self._local_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._cache_lock = asyncio.Lock()
        self._local_cache_max = int(getattr(settings, "LOCAL_CACHE_MAX_KEYS", 5000))
        self._bg_tasks = set()
        
        # Load API keys from environment
        self.api_keys = {
            "alpha_vantage": settings.ALPHA_VANTAGE_API_KEY if hasattr(settings, 'ALPHA_VANTAGE_API_KEY') else None,
            "coingecko": settings.COINGECKO_API_KEY if hasattr(settings, 'COINGECKO_API_KEY') else None,
            "finnhub": settings.FINNHUB_API_KEY if hasattr(settings, 'FINNHUB_API_KEY') else None,
            "cryptocompare": getattr(settings, "CRYPTOCOMPARE_API_KEY", None),
        }
        
        # Enhanced API endpoints with API key support
        self.apis = {
            "coingecko": {
                "base_url": "https://api.coingecko.com/api/v3",
                "rate_limit": 50,  # 50 calls per minute for free tier
                "endpoints": {
                    "price": "/simple/price",
                    "coins": "/coins/{id}",
                    "markets": "/coins/markets",
                    "trending": "/search/trending",
                    "global": "/global"
                },
                "requires_key": False,
                "api_key_param": "x_cg_demo_api_key"
            },
            "alpha_vantage": {
                "base_url": "https://www.alphavantage.co/query",
                "rate_limit": 5,  # 5 calls per minute for free tier
                "endpoints": {
                    "quote": "?function=GLOBAL_QUOTE",
                    "intraday": "?function=TIME_SERIES_INTRADAY",
                    "crypto": "?function=DIGITAL_CURRENCY_DAILY"
                },
                "requires_key": True,
                "api_key_param": "apikey"
            },
            "finnhub": {
                "base_url": "https://finnhub.io/api/v1",
                "rate_limit": 60,  # 60 calls per minute for free tier
                "endpoints": {
                    "quote": "/quote",
                    "crypto": "/crypto/symbol",
                    "candle": "/crypto/candle"
                },
                "requires_key": True,
                "api_key_param": "token"
            },
            "cryptocompare": {
                "base_url": "https://min-api.cryptocompare.com/data",
                "rate_limit": 100,  # generous community limit
                "endpoints": {
                    "price": "/pricemultifull",
                    "histoday": "/v2/histoday",
                    "histohour": "/v2/histohour"
                },
                "requires_key": False,
                "api_key_param": "api_key"
            },
            "coincap": {
                "base_url": "https://api.coincap.io/v2",
                "rate_limit": 100,  # 100 calls per minute
                "endpoints": {
                    "assets": "/assets",
                    "asset": "/assets/{id}",
                    "rates": "/rates",
                    "markets": "/markets"
                },
                "requires_key": False
            },
            "coinpaprika": {
                "base_url": "https://api.coinpaprika.com/v1",
                "rate_limit": 20000,  # 20k calls per month
                "endpoints": {
                    "tickers": "/tickers",
                    "ticker": "/tickers/{id}",
                    "global": "/global"
                },
                "requires_key": False
            }
        }
        
        # Rate limiting tracking
        self.rate_limiters = {}
        for api_name, config in self.apis.items():
            self.rate_limiters[api_name] = {
                "requests": 0,
                "window_start": time.time(),
                "max_requests": config["rate_limit"]
            }
        
        # ENTERPRISE CACHING AND FALLBACK CONFIGURATION
        # Redis retains entries long enough for degraded-mode operation while
        # the "freshness" window keeps live responses tight for end users.
        self.cache_ttl = {
            "price": 300,       # 5 minutes – allows stale-but-safe fallbacks
            "detailed": 600,    # 10 minutes for enriched market snapshots
            "market": 600,      # 10 minutes for market data aggregates
            "markets": 900,     # 15 minutes for broader market tables
            "trending": 900,    # 15 minutes for trending data
            "global": 900,      # 15 minutes for global stats
        }
        self.cache_freshness_seconds = {
            "price": 60,        # mark price data as stale after 1 minute
            "detailed": 300,
            "market": 300,
            "markets": 600,
            "trending": 600,
            "global": 600,
        }

        # ENTERPRISE API fallback hierarchy with circuit breaker status
        self.api_fallbacks = {
            "price": ["coingecko", "cryptocompare", "coincap", "coinpaprika"],
            "market": ["coingecko", "alpha_vantage", "finnhub"],
            "trending": ["coingecko", "coinpaprika"],
            "global": ["coingecko", "coinpaprika"]
        }
        
        # ENTERPRISE CIRCUIT BREAKER STATE using existing CircuitBreaker implementation
        self.circuit_breakers = {}
        for api_name in self.apis.keys():
            # Configure circuit breaker based on API characteristics
            if api_name == "alpha_vantage":
                config = CircuitBreakerConfig(
                    failure_threshold=3,  # Strict rate limits
                    timeout_seconds=300,  # 5 minutes
                    max_timeout_seconds=1800  # 30 minutes max
                )
            elif api_name == "coingecko":
                config = CircuitBreakerConfig(
                    failure_threshold=7,  # More lenient
                    timeout_seconds=120,  # 2 minutes
                    max_timeout_seconds=900  # 15 minutes max
                )
            else:
                config = CircuitBreakerConfig()  # Default configuration
            
            self.circuit_breakers[api_name] = CircuitBreaker(
                name=f"market_data_{api_name}",
                config=config
            )
        
        # Enable circuit breakers based on configuration
        self.circuit_breakers_enabled = settings.CIRCUIT_BREAKER_ENABLED
        
        # Symbol mappings for different APIs
        self.symbol_mappings = {
            "coingecko": {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "SOL": "solana",
                "ADA": "cardano",
                "DOT": "polkadot",
                "MATIC": "matic-network",
                "LINK": "chainlink",
                "UNI": "uniswap",
                "AVAX": "avalanche-2",
                "ATOM": "cosmos"
            },
            "cryptocompare": {
                "BTC": "BTC",
                "ETH": "ETH",
                "SOL": "SOL",
                "ADA": "ADA",
                "DOT": "DOT",
                "MATIC": "MATIC",
                "LINK": "LINK",
                "UNI": "UNI",
                "AVAX": "AVAX",
                "ATOM": "ATOM",
                "AAVE": "AAVE",
                "MKR": "MKR",
                "SNX": "SNX",
                "CRV": "CRV",
                "USDC": "USDC",
                "USDT": "USDT",
                "DAI": "DAI",
            },
            "coincap": {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "SOL": "solana",
                "ADA": "cardano",
                "DOT": "polkadot",
                "MATIC": "polygon",
                "LINK": "chainlink",
                "UNI": "uniswap",
                "AVAX": "avalanche",
                "ATOM": "cosmos"
            },
            "coinpaprika": {
                "BTC": "btc-bitcoin",
                "ETH": "eth-ethereum",
                "SOL": "sol-solana",
                "ADA": "ada-cardano",
                "DOT": "dot-polkadot",
                "MATIC": "matic-polygon",
                "LINK": "link-chainlink",
                "UNI": "uni-uniswap",
                "AVAX": "avax-avalanche",
                "ATOM": "atom-cosmos"
            }
        }
        
        # Map DeFi governance tokens to protocol level analytics endpoints
        self.defi_protocol_mappings = DEFI_PROTOCOL_MAPPINGS

        # ENTERPRISE TIMEOUT + FALLBACK CONFIGURATION
        self.api_call_timeout = float(getattr(settings, "MARKET_DATA_API_TIMEOUT", 6.0))
        self.total_price_timeout = float(getattr(settings, "MARKET_DATA_TOTAL_TIMEOUT", 8.0))
        self.supabase_sync_timeout = float(getattr(settings, "MARKET_DATA_SUPABASE_TIMEOUT", 1.5))
    
    async def async_init(self):
        try:
            self.redis = await get_redis_client()
        except Exception as e:
            logger.warning("Redis not available for MarketDataFeeds", error=str(e))
            self.redis = None

    def _monotonic(self) -> float:
        return time.monotonic()

    async def _cache_local(self, cache_key: str, ttl_seconds: int, payload: Dict[str, Any]) -> None:
        expires_at = self._monotonic() + ttl_seconds
        async with self._cache_lock:
            # Evict oldest if at capacity
            if self._local_cache_max and len(self._local_cache) >= self._local_cache_max:
                oldest_key = min(self._local_cache, key=lambda k: self._local_cache[k][0])
                self._local_cache.pop(oldest_key, None)
            self._local_cache[cache_key] = (expires_at, copy.deepcopy(payload))

    def _parse_cached_at(self, cached_at: Optional[str]) -> Optional[datetime]:
        if not cached_at:
            return None

        try:
            value = cached_at
            if isinstance(value, str) and value.endswith("Z"):
                value = value[:-1] + "+00:00"
            dt = datetime.fromisoformat(value)
            return dt if getattr(dt, "tzinfo", None) else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    def _prepare_cache_payload(self, payload: Dict[str, Any], ttl_key: str) -> Dict[str, Any]:
        prepared: Dict[str, Any]
        if isinstance(payload, dict):
            prepared = copy.deepcopy(payload)
        else:
            prepared = {"success": True, "data": copy.deepcopy(payload)}

        metadata = prepared.setdefault("metadata", {})
        now_iso = datetime.now(timezone.utc).isoformat()
        metadata.setdefault("cached_at", now_iso)
        metadata.setdefault("served_from", "live")
        metadata.setdefault("cache_origin", metadata.get("source", "unknown"))
        metadata["cache_ttl"] = self.cache_ttl.get(ttl_key, 30)

        return prepared

    def _apply_cache_metadata(self, payload: Dict[str, Any], ttl_key: str) -> Dict[str, Any]:
        metadata = payload.setdefault("metadata", {})
        metadata.setdefault("cache_origin", metadata.get("source", "unknown"))

        cached_at = self._parse_cached_at(metadata.get("cached_at"))
        if cached_at is None:
            cached_at = datetime.now(timezone.utc)
            metadata["cached_at"] = cached_at.isoformat()
        elif getattr(cached_at, "tzinfo", None) is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)

        freshness_window = self.cache_freshness_seconds.get(ttl_key)
        is_stale = False
        if freshness_window is not None:
            now_utc = datetime.now(timezone.utc)
            is_stale = (now_utc - cached_at).total_seconds() > freshness_window

        metadata["stale"] = is_stale
        metadata["served_from"] = "cache"
        metadata["cache_ttl"] = self.cache_ttl.get(ttl_key, 30)

        return payload

    def _decode_cached_payload(self, raw: Any) -> Optional[Dict[str, Any]]:
        payload: Any = raw

        if isinstance(payload, bytes):
            try:
                payload = payload.decode()
            except Exception:
                payload = payload.decode(errors="ignore") if hasattr(payload, "decode") else payload

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                # Cache entries must be valid JSON (written via json.dumps)
                # This fallback should never execute in normal operation
                logger.debug(
                    "Failed to decode cached payload as JSON",
                    payload_preview=payload[:100] if len(payload) > 100 else payload,
                )
                return None

        return payload if isinstance(payload, dict) else None

    async def _get_cached_response(self, cache_key: str, ttl_key: str = "price") -> Optional[Dict[str, Any]]:
        now = self._monotonic()

        async with self._cache_lock:
            entry = self._local_cache.get(cache_key)
            if entry:
                expires_at, payload = entry
                if expires_at > now:
                    payload_copy = copy.deepcopy(payload)
                    return self._apply_cache_metadata(payload_copy, ttl_key)
                self._local_cache.pop(cache_key, None)

        if not self.redis:
            return None

        try:
            raw = await self.redis.get(cache_key)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug(
                "Redis read failed for market data cache",
                key=cache_key,
                error=str(exc),
            )
            return None

        if not raw:
            return None

        decoded = self._decode_cached_payload(raw)
        if decoded is None:
            return None

        ttl_seconds = self.cache_ttl.get(ttl_key, 30)
        await self._cache_local(cache_key, ttl_seconds, decoded)
        payload_copy = copy.deepcopy(decoded)
        return self._apply_cache_metadata(payload_copy, ttl_key)

    async def _store_cached_response(
        self,
        cache_key: str,
        ttl_key: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        prepared_payload = self._prepare_cache_payload(payload, ttl_key)
        ttl_seconds = self.cache_ttl.get(ttl_key, 30)
        await self._cache_local(cache_key, ttl_seconds, prepared_payload)

        if self.redis:
            try:
                await self.redis.setex(cache_key, ttl_seconds, json.dumps(prepared_payload))
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.debug(
                    "Redis write failed for market data cache",
                    key=cache_key,
                    error=str(exc),
                )

        return copy.deepcopy(prepared_payload)

    def _schedule_supabase_sync(self, symbol: str, payload: Dict[str, Any]) -> None:
        sync_fn = getattr(supabase_client, "sync_market_data", None)
        if not callable(sync_fn):
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # pragma: no cover - loop not running
            return

        payload_copy = copy.deepcopy(payload)

        async def _sync() -> None:
            try:
                await asyncio.wait_for(
                    sync_fn(symbol, payload_copy),
                    timeout=self.supabase_sync_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Supabase sync timed out",
                    symbol=symbol,
                    timeout=self.supabase_sync_timeout,
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "Supabase sync failed",
                    symbol=symbol,
                    error=str(exc),
                )

        task = loop.create_task(_sync())
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)
    
    async def _check_rate_limit(self, api_name: str) -> bool:
        """ENTERPRISE: Check rate limits with circuit breaker protection."""
        current_time = time.time()
        
        # ENTERPRISE CIRCUIT BREAKER CHECK
        circuit_breaker = self.circuit_breakers.get(api_name)
        if circuit_breaker:
            try:
                should_try = await circuit_breaker._should_try()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "Circuit breaker check failed",
                    api=api_name,
                    error=str(exc),
                )
                should_try = True

            if not should_try:
                logger.debug(f"Circuit breaker OPEN for {api_name}")
                return False

        # Check traditional rate limits
        limiter = self.rate_limiters.get(api_name)
        if limiter is None:
            api_config = self.apis.get(api_name, {})
            limiter = {
                "requests": 0,
                "window_start": current_time,
                "max_requests": api_config.get("rate_limit", 60),
            }
            self.rate_limiters[api_name] = limiter

        # Reset window if needed (1 minute windows)
        if current_time - limiter.get("window_start", 0) >= 60:
            limiter["requests"] = 0
            limiter["window_start"] = current_time
        
        # Check if under limit
        if limiter["requests"] < limiter["max_requests"]:
            limiter["requests"] += 1
            return True
        
        return False
    
    async def _handle_api_failure(self, api_name: str, error: str):
        """ENTERPRISE: Handle API failure using existing CircuitBreaker implementation."""
        if not self.circuit_breakers_enabled:
            return
            
        circuit_breaker = self.circuit_breakers.get(api_name)
        if circuit_breaker:
            # Record failure in circuit breaker
            await circuit_breaker._record_failure()
            logger.warning(f"Circuit breaker failure recorded for {api_name}", error=error)
    
    async def _handle_api_success(self, api_name: str):
        """ENTERPRISE: Handle API success using existing CircuitBreaker implementation."""
        if not self.circuit_breakers_enabled:
            return
            
        circuit_breaker = self.circuit_breakers.get(api_name)
        if circuit_breaker:
            # Record success in circuit breaker
            await circuit_breaker._record_success()
            logger.debug(f"Circuit breaker success recorded for {api_name}")

    def _get_api_params(self, api_name: str, base_params: Dict = None) -> Dict[str, Any]:
        """Get API parameters including API key if required."""
        params = base_params or {}

        api_config = self.apis.get(api_name, {})
        if api_config.get("requires_key") and self.api_keys.get(api_name):
            key_param = api_config.get("api_key_param", "apikey")
            params[key_param] = self.api_keys[api_name]

        return params

    async def _load_cached_price_entry(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Load a cached price payload for graceful degradation."""
        cached_response = await self._get_cached_response(f"price:{symbol}", "price")
        if not cached_response:
            return None

        if isinstance(cached_response, dict) and "data" in cached_response:
            data = cached_response.get("data")
            return data if isinstance(data, dict) else None

        return cached_response if isinstance(cached_response, dict) else None

    async def _fallback_price_response(
        self,
        symbol: str,
        errors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Return a cached price payload when live calls fail."""

        cache_key = f"price:{symbol}"
        cached_response = await self._get_cached_response(cache_key, "price")
        if cached_response:
            response_payload = copy.deepcopy(cached_response)
            if not isinstance(response_payload, dict):
                response_payload = {"success": True, "data": {}}

            if "success" not in response_payload:
                response_payload = {
                    "success": True,
                    "data": response_payload,
                }

            metadata = response_payload.setdefault("metadata", {})
            metadata["served_from"] = "cache"
            metadata["stale"] = metadata.get("stale", True)
            metadata["cache_degraded"] = True

            if errors:
                metadata["errors"] = list(errors)

            return response_payload

        error_message = "; ".join(errors or []) if errors else "Live market data unavailable"
        return {
            "success": False,
            "error": error_message or "Live market data unavailable",
            "data": {},
        }
    
    async def get_real_time_price(self, symbol: str) -> Dict[str, Any]:
        """Get real-time price data for a symbol."""
        try:
            cache_key = f"price:{symbol}"
            cached_data = await self._get_cached_response(cache_key, "price")
            if cached_data:
                # Check if cached data is stale before returning it
                metadata = cached_data.get("metadata", {}) if isinstance(cached_data, dict) else {}
                is_stale = metadata.get("stale", False)

                # Only return cached data if it's fresh
                if not is_stale:
                    return cached_data
                # If stale, fall through to attempt fresh API call

            # Try APIs in order of preference with rate limiting
            apis_to_try = [
                ("coingecko", self._fetch_coingecko_price),
                ("cryptocompare", self._fetch_cryptocompare_price),
                ("alpha_vantage", self._fetch_alpha_vantage_price),
                ("finnhub", self._fetch_finnhub_price),
                ("coincap", self._fetch_coincap_price)
            ]

            price_data = {"success": False, "error": "No APIs available"}
            aggregated_errors: List[str] = []
            start_time = time.monotonic()

            for api_name, fetch_method in apis_to_try:
                elapsed = time.monotonic() - start_time
                if elapsed >= self.total_price_timeout:
                    aggregated_errors.append(f"Global timeout reached after {elapsed:.2f}s")
                    break

                try:
                    # ENTERPRISE: Check circuit breaker before API call
                    if not await self._check_rate_limit(api_name):
                        aggregated_errors.append(f"{api_name}: rate limited")
                        continue

                    price_data = await asyncio.wait_for(
                        fetch_method(symbol),
                        timeout=self.api_call_timeout,
                    )
                    if price_data.get("success"):
                        # ENTERPRISE: Record successful API call
                        await self._handle_api_success(api_name)
                        break
                    else:
                        # ENTERPRISE: Handle API failure
                        aggregated_errors.append(f"{api_name}: {price_data.get('error', 'unknown error')}")
                        await self._handle_api_failure(api_name, price_data.get("error", "Unknown error"))
                except asyncio.TimeoutError:
                    logger.warning("Market data API timed out", api=api_name, symbol=symbol)
                    await self._handle_api_failure(api_name, "timeout")
                    aggregated_errors.append(f"{api_name}: timeout")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to fetch from {api_name}", error=str(e))
                    # ENTERPRISE: Handle API exception
                    await self._handle_api_failure(api_name, str(e))
                    aggregated_errors.append(f"{api_name}: {str(e)}")
                    continue

            if price_data.get("success"):
                cached_payload = await self._store_cached_response(cache_key, "price", price_data)

                response_payload = copy.deepcopy(cached_payload)

                self._schedule_supabase_sync(symbol, response_payload.get("data", {}))

                if aggregated_errors:
                    metadata = response_payload.setdefault("metadata", {})
                    metadata["warnings"] = list(aggregated_errors)
                return response_payload

            if aggregated_errors:
                return await self._fallback_price_response(symbol, aggregated_errors)
            return price_data

        except Exception as e:
            logger.error(f"Failed to get price for {symbol}", error=str(e))
            return await self._fallback_price_response(symbol, [str(e)])
    
    async def get_price_with_enterprise_fallback(self, symbol: str, data_type: str = "price") -> Dict[str, Any]:
        """ENTERPRISE-GRADE price fetching with comprehensive fallback strategies."""
        ttl_key = data_type if data_type in self.cache_ttl else "price"
        cache_key = f"{data_type}:{symbol}"

        try:
            cached_data = await self._get_cached_response(cache_key, ttl_key)
            if cached_data:
                return cached_data
            
            # Get fallback hierarchy for this data type
            api_hierarchy = self.api_fallbacks.get(data_type, ["coingecko", "coincap"])
            
            aggregated_errors: List[str] = []
            start_time = time.monotonic()

            for api_name in api_hierarchy:
                elapsed = time.monotonic() - start_time
                if elapsed >= self.total_price_timeout:
                    aggregated_errors.append(
                        f"Global timeout reached after {elapsed:.2f}s"
                    )
                    break

                try:
                    # Check rate limits
                    if not await self._check_rate_limit(api_name):
                        logger.warning(
                            "Rate limit exceeded, trying next API",
                            api=api_name,
                            symbol=symbol,
                        )
                        aggregated_errors.append(f"{api_name}: rate limited")
                        continue

                    # Attempt to fetch data with per-call timeout
                    if api_name == "coingecko":
                        result = await asyncio.wait_for(
                            self._fetch_coingecko_price(symbol),
                            timeout=self.api_call_timeout,
                        )
                    elif api_name == "coincap":
                        result = await asyncio.wait_for(
                            self._fetch_coincap_price(symbol),
                            timeout=self.api_call_timeout,
                        )
                    elif api_name == "coinpaprika":
                        result = await asyncio.wait_for(
                            self._fetch_coinpaprika_price(symbol),
                            timeout=self.api_call_timeout,
                        )
                    else:
                        continue

                    if result.get("success"):
                        await self._handle_api_success(api_name)

                        cached_payload = await self._store_cached_response(cache_key, ttl_key, result)

                        response_payload = copy.deepcopy(cached_payload)
                        if aggregated_errors:
                            metadata = response_payload.setdefault("metadata", {})
                            metadata["warnings"] = list(aggregated_errors)
                        return response_payload

                    aggregated_errors.append(
                        f"{api_name}: {result.get('error', 'unknown error')}"
                    )
                    await self._handle_api_failure(
                        api_name, result.get("error", "Unknown error")
                    )

                except asyncio.TimeoutError:
                    logger.warning(
                        "Market data API timed out",
                        api=api_name,
                        symbol=symbol,
                    )
                    aggregated_errors.append(f"{api_name}: timeout")
                    await self._handle_api_failure(api_name, "timeout")
                    continue
                except Exception as e:
                    logger.warning(
                        "API call failed",
                        api=api_name,
                        symbol=symbol,
                        error=str(e),
                    )
                    aggregated_errors.append(f"{api_name}: {str(e)}")
                    await self._handle_api_failure(api_name, str(e))
                    continue

            if aggregated_errors:
                return await self._fallback_price_response(symbol, aggregated_errors)

            # All APIs failed without specific errors recorded
            return await self._fallback_price_response(symbol)

        except Exception as e:
            logger.error(f"Enterprise fallback failed for {symbol}: {str(e)}")
            return await self._fallback_price_response(symbol, [str(e)])

    async def get_detailed_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get detailed market data including volume, market cap, etc."""
        try:
            cache_key = f"detailed:{symbol}"
            cached_data = await self._get_cached_response(cache_key, "detailed")
            if cached_data:
                return cached_data
            
            # Get detailed data from CoinGecko
            detailed_data = await self._fetch_coingecko_detailed(symbol)
            
            if detailed_data.get("success"):
                cached_payload = await self._store_cached_response(cache_key, "detailed", detailed_data)
                return cached_payload

            return detailed_data
            
        except Exception as e:
            logger.error(f"Failed to get detailed data for {symbol}", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Any]:
        """Get prices for multiple symbols efficiently."""
        try:
            # Use CoinGecko batch API
            symbol_ids = []
            symbol_map = {}
            
            for symbol in symbols:
                if symbol in self.symbol_mappings["coingecko"]:
                    coin_id = self.symbol_mappings["coingecko"][symbol]
                    symbol_ids.append(coin_id)
                    symbol_map[coin_id] = symbol
            
            if not symbol_ids:
                return {"success": False, "error": "No valid symbols"}
            
            url = f"{self.apis['coingecko']['base_url']}/simple/price"
            params = {
                "ids": ",".join(symbol_ids),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
                "include_market_cap": "true"
            }
            
            timeout = aiohttp.ClientTimeout(total=6)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()

                            # Transform data
                            result = {"success": True, "data": {}}

                            for coin_id, coin_data in data.items():
                                symbol = symbol_map.get(coin_id, coin_id.upper())
                                result["data"][symbol] = {
                                    "symbol": symbol,
                                    "price": coin_data.get("usd", 0),
                                    "change_24h": coin_data.get("usd_24h_change", 0),
                                    "volume_24h": coin_data.get("usd_24h_vol", 0),
                                    "market_cap": coin_data.get("usd_market_cap", 0),
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "source": "coingecko"
                                }

                                await self._store_cached_response(
                                    f"price:{symbol}",
                                    "price",
                                    {
                                        "success": True,
                                        "data": result["data"][symbol],
                                    },
                                )

                            return result
                        return {"success": False, "error": f"API error: {response.status}"}
                except asyncio.TimeoutError:
                    logger.warning("CoinGecko multiple price request timed out", symbols=symbols)
                    return await self._fallback_cached_prices(symbols)

        except Exception as e:
            logger.error("Failed to get multiple prices", error=str(e))
            return await self._fallback_cached_prices(symbols, error=str(e))

    async def _fallback_cached_prices(
        self,
        symbols: List[str],
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        cached: Dict[str, Any] = {}

        async def load_from_cache(symbol: str) -> Optional[Dict[str, Any]]:
            return await self._load_cached_price_entry(symbol)

        for symbol in symbols:
            cached_data = await load_from_cache(symbol)
            if cached_data:
                cached[symbol] = cached_data

        if cached:
            metadata = {
                "served_from": "cache",
                "cache_degraded": True,
                "stale": True,
            }
            if error:
                metadata["errors"] = [error]
            return {"success": True, "data": cached, "metadata": metadata}

        return {
            "success": False,
            "error": error or "Price service unavailable",
        }

    def _deserialize_price_cache(self, raw: Any) -> Optional[Dict[str, Any]]:
        """Normalise cached price payloads into dictionaries."""

        container = self._decode_cached_payload(raw)
        if not isinstance(container, dict):
            return None

        data: Any = container.get("data") if "data" in container else container

        if isinstance(data, dict):
            return data

        decoded = self._decode_cached_payload(data)
        return decoded if isinstance(decoded, dict) else None

    async def get_trending_coins(self, limit: int = 10) -> Dict[str, Any]:
        """Get trending coins from CoinGecko."""
        try:
            url = f"{self.apis['coingecko']['base_url']}/search/trending"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        trending = []
                        for coin in data.get("coins", [])[:limit]:
                            coin_data = coin.get("item", {})
                            trending.append({
                                "symbol": coin_data.get("symbol", "").upper(),
                                "name": coin_data.get("name", ""),
                                "rank": coin_data.get("market_cap_rank", 0),
                                "price_btc": coin_data.get("price_btc", 0)
                            })
                        
                        return {
                            "success": True,
                            "data": trending,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    else:
                        return {"success": False, "error": f"API error: {response.status}"}
                        
        except Exception as e:
            logger.error("Failed to get trending coins", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _fetch_coingecko_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch price from CoinGecko API with API key support."""
        try:
            if not await self._check_rate_limit("coingecko"):
                return {"success": False, "error": "Rate limit exceeded for CoinGecko"}
            
            if symbol not in self.symbol_mappings["coingecko"]:
                return {"success": False, "error": f"Symbol {symbol} not supported"}
            
            coin_id = self.symbol_mappings["coingecko"][symbol]
            url = f"{self.apis['coingecko']['base_url']}/simple/price"
            
            base_params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
                "include_market_cap": "true"
            }
            
            params = self._get_api_params("coingecko", base_params)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        coin_data = data.get(coin_id, {})
                        
                        if coin_data:
                            return {
                                "success": True,
                                "data": {
                                    "symbol": symbol,
                                    "price": coin_data.get("usd", 0),
                                    "change_24h": coin_data.get("usd_24h_change", 0),
                                    "volume_24h": coin_data.get("usd_24h_vol", 0),
                                    "market_cap": coin_data.get("usd_market_cap", 0),
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "source": "coingecko"
                                }
                            }
                    elif response.status == 429:
                        # ENTERPRISE: Handle rate limiting specifically
                        retry_after = response.headers.get("Retry-After", "60")
                        error_msg = f"API error: 429 - Rate limited (retry after {retry_after}s)"
                        logger.debug(f"CoinGecko rate limited", symbol=symbol, retry_after=retry_after)
                        
                        cached_price = await self._load_cached_price_entry(symbol)
                        if cached_price:
                            cached_payload = copy.deepcopy(cached_price)
                            cached_payload["from_cache"] = True
                            return {
                                "success": True,
                                "data": cached_payload,
                                "metadata": {
                                    "source": "cache",
                                    "rate_limited": True,
                                },
                            }

                        return {"success": False, "error": error_msg}
                    
                    return {"success": False, "error": f"API error: {response.status}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_market_snapshot(self, symbol: str, include_onchain: bool = False) -> Dict[str, Any]:
        """Aggregate price, volume, volatility and on-chain analytics for a symbol."""

        symbol = (symbol or "").upper()
        if not symbol:
            return {"success": False, "error": "symbol_required"}

        price_task = asyncio.create_task(self.get_real_time_price(symbol))
        cc_task = asyncio.create_task(self._fetch_cryptocompare_price(symbol))
        vol_task = asyncio.create_task(self._calculate_realized_volatility(symbol))

        price_result, cc_result, volatility_result = await asyncio.gather(
            price_task, cc_task, vol_task, return_exceptions=True
        )

        snapshot: Dict[str, Any] = {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "sources": {},
        }

        # Primary price feed (CoinGecko / fallback hierarchy)
        if isinstance(price_result, dict) and price_result.get("success"):
            data = price_result.get("data", {})
            snapshot.update({k: v for k, v in data.items() if k not in {"symbol", "source"}})
            snapshot["sources"]["primary"] = data.get("source")

        # CryptoCompare enrichment for volume/volatility context
        if isinstance(cc_result, dict) and cc_result.get("success"):
            cc_data = cc_result.get("data", {})
            snapshot.setdefault("price", cc_data.get("price"))
            snapshot.setdefault("change_24h", cc_data.get("change_24h"))
            snapshot["volume_24h"] = max(
                float(snapshot.get("volume_24h", 0) or 0),
                float(cc_data.get("volume_24h", 0) or 0),
            )
            snapshot["high_24h"] = max(snapshot.get("high_24h", 0) or 0, cc_data.get("high_24h", 0) or 0)
            snapshot["low_24h"] = min(
                snapshot.get("low_24h", float("inf")) or float("inf"),
                cc_data.get("low_24h", float("inf")) or float("inf"),
            )
            snapshot["range_volatility"] = cc_data.get("range_volatility")
            snapshot["sources"]["cryptocompare"] = cc_data.get("source", "cryptocompare")

        if snapshot.get("low_24h") == float("inf"):
            snapshot["low_24h"] = None

        if isinstance(volatility_result, Exception):
            volatility_value = None
        else:
            volatility_value = volatility_result

        if volatility_value is not None:
            snapshot["realized_volatility_30d"] = volatility_value

        # Attach static expectations
        profile = get_asset_profile(symbol)
        snapshot["asset_profile"] = {
            "category": profile.category,
            "tier": profile.tier,
            "baseline_expected_return": profile.baseline_return,
            "staking_yield": profile.staking_yield,
            "total_expected_return": profile.total_expected_return,
            "notes": profile.notes,
        }

        # Optional on-chain analytics for DeFi tokens
        if include_onchain and symbol in self.defi_protocol_mappings:
            defi_result = await self.get_defi_token_insights(symbol)
            if defi_result.get("success"):
                snapshot["onchain_metrics"] = defi_result.get("data", {})

        success = "price" in snapshot and snapshot.get("price") not in (None, 0)

        return {
            "success": success,
            "data": snapshot,
            "timestamp": snapshot["timestamp"],
        }

    async def get_defi_token_insights(self, symbol: str) -> Dict[str, Any]:
        """Fetch on-chain analytics for DeFi protocols using DefiLlama."""

        protocol_slug = self.defi_protocol_mappings.get((symbol or "").upper())
        if not protocol_slug:
            return {"success": False, "error": "protocol_not_supported"}

        url = f"https://api.llama.fi/protocol/{protocol_slug}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return {"success": False, "error": f"API error: {response.status}"}

                    payload = await response.json()

                    def _safe_float(value: Any) -> float:
                        try:
                            if isinstance(value, str):
                                value = value.replace(",", "").strip()
                            return float(value)
                        except (TypeError, ValueError):
                            return 0.0

                    raw_tvl = payload.get("tvl", 0)
                    tvl = 0.0

                    if isinstance(raw_tvl, list):
                        last_entry: Optional[Dict[str, Any]] = None
                        for item in reversed(raw_tvl):
                            if isinstance(item, dict):
                                last_entry = item
                                break

                        if last_entry:
                            for key in (
                                "totalLiquidityUSD",
                                "tvl",
                                "liquidityUSD",
                                "totalLiquidity",
                            ):
                                if key in last_entry and last_entry[key] not in (None, ""):
                                    tvl = _safe_float(last_entry[key])
                                    break
                    else:
                        tvl = _safe_float(raw_tvl)

                    change_1d = float(payload.get("change_1d", 0) or 0)
                    change_7d = float(payload.get("change_7d", 0) or 0)
                    change_1m = float(payload.get("change_1m", 0) or 0)

                    return {
                        "success": True,
                        "data": {
                            "protocol": protocol_slug,
                            "category": payload.get("category"),
                            "chains": payload.get("chains", []),
                            "tvl_usd": tvl,
                            "change_1d_pct": change_1d,
                            "change_7d_pct": change_7d,
                            "change_1m_pct": change_1m,
                            "audits": payload.get("audit").split(",") if payload.get("audit") else [],
                            "url": payload.get("url"),
                            "risk_commentary": payload.get("riskFactors", {}).get("overall", "")
                            if isinstance(payload.get("riskFactors"), dict)
                            else "",
                            "source": "defillama",
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    }
        except Exception as exc:
            logger.debug("DefiLlama insight fetch failed", symbol=symbol, error=str(exc))
            return {"success": False, "error": str(exc)}

    async def get_yield_opportunities(self, symbols: List[str]) -> Dict[str, Any]:
        """Return staking, lending and yield farming opportunities for the provided symbols."""

        results: Dict[str, Any] = {}
        defi_tasks: Dict[str, asyncio.Task] = {}

        for raw_symbol in symbols:
            symbol = (raw_symbol or "").upper()
            if not symbol:
                continue

            profile = get_asset_profile(symbol)
            products = get_yield_products(symbol)

            if profile.staking_yield > 0 or products:
                results[symbol] = {
                    "symbol": symbol,
                    "category": profile.category,
                    "tier": profile.tier,
                    "baseline_expected_return": profile.baseline_return,
                    "staking_yield": profile.staking_yield,
                    "total_expected_return": profile.total_expected_return,
                    "products": products,
                    "risk_notes": profile.notes,
                }

            if symbol in self.defi_protocol_mappings and symbol not in defi_tasks:
                defi_tasks[symbol] = asyncio.create_task(self.get_defi_token_insights(symbol))

        for symbol, task in defi_tasks.items():
            try:
                defi_result = await task
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.debug("Defi insight task failed", symbol=symbol, error=str(exc))
                continue

            if defi_result.get("success"):
                profile = get_asset_profile(symbol)
                entry = results.setdefault(
                    symbol,
                    {
                        "symbol": symbol,
                        "category": profile.category,
                        "tier": profile.tier,
                        "baseline_expected_return": profile.baseline_return,
                        "staking_yield": profile.staking_yield,
                        "total_expected_return": profile.total_expected_return,
                        "products": [],
                        "risk_notes": profile.notes,
                    },
                )
                entry["protocol_metrics"] = defi_result.get("data", {})

        timestamp = datetime.utcnow().isoformat()

        return {
            "success": bool(results),
            "data": results,
            "timestamp": timestamp,
        }

    async def _fetch_cryptocompare_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch market snapshot from CryptoCompare including 24h ranges."""
        try:
            if symbol not in self.symbol_mappings.get("cryptocompare", {}):
                return {"success": False, "error": f"Symbol {symbol} not supported"}

            if not await self._check_rate_limit("cryptocompare"):
                return {"success": False, "error": "Rate limit exceeded for CryptoCompare"}

            mapped_symbol = self.symbol_mappings["cryptocompare"][symbol]
            url = f"{self.apis['cryptocompare']['base_url']}{self.apis['cryptocompare']['endpoints']['price']}"
            params = self._get_api_params("cryptocompare", {
                "fsyms": mapped_symbol,
                "tsyms": "USD"
            })

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status != 200:
                        return {"success": False, "error": f"API error: {response.status}"}

                    payload = await response.json()
                    raw_section = payload.get("RAW", {})
                    usd_data = raw_section.get(mapped_symbol, {}).get("USD", {})

                    if not usd_data:
                        return {"success": False, "error": "No data returned"}

                    price = float(usd_data.get("PRICE", 0) or 0)
                    high = float(usd_data.get("HIGH24HOUR", 0) or 0)
                    low = float(usd_data.get("LOW24HOUR", 0) or 0)
                    volume = float(usd_data.get("TOTALVOLUME24H", 0) or usd_data.get("TOTALVOLUME24HTO", 0) or 0)
                    change_pct = float(usd_data.get("CHANGEPCT24H", 0) or 0)

                    # Simple intraday volatility proxy using 24h high/low range
                    if price > 0 and high > 0 and low > 0:
                        range_vol = abs(high - low) / price
                    else:
                        range_vol = 0.0

                    return {
                        "success": True,
                        "data": {
                            "symbol": symbol,
                            "price": price,
                            "change_24h": change_pct,
                            "volume_24h": volume,
                            "high_24h": high,
                            "low_24h": low,
                            "range_volatility": range_vol,
                            "market": usd_data.get("MARKET", "crypto"),
                            "timestamp": datetime.utcnow().isoformat(),
                            "source": "cryptocompare",
                        },
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _fetch_cryptocompare_history(
        self,
        symbol: str,
        *,
        limit: int = 60,
        interval: str = "histoday",
    ) -> List[Dict[str, Any]]:
        """Fetch historical candles from CryptoCompare for volatility analysis."""

        if symbol not in self.symbol_mappings.get("cryptocompare", {}):
            return []

        endpoint_key = "histoday" if interval == "histoday" else "histohour"
        endpoint = self.apis["cryptocompare"]["endpoints"].get(endpoint_key)
        if not endpoint:
            return []

        if not await self._check_rate_limit("cryptocompare"):
            return []

        mapped_symbol = self.symbol_mappings["cryptocompare"][symbol]
        params = self._get_api_params(
            "cryptocompare",
            {
                "fsym": mapped_symbol,
                "tsym": "USD",
                "limit": limit,
            },
        )

        url = f"{self.apis['cryptocompare']['base_url']}{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status != 200:
                        return []

                    payload = await response.json()
                    data = payload.get("Data", {})
                    candles = data.get("Data", []) if isinstance(data, dict) else payload.get("Data", [])
                    return candles or []
        except Exception:
            return []

    async def _calculate_realized_volatility(self, symbol: str, window: int = 30) -> Optional[float]:
        """Calculate annualised realized volatility using CryptoCompare history."""

        candles = await self._fetch_cryptocompare_history(symbol, limit=window)
        if not candles:
            return None

        closes = [float(entry.get("close", 0) or 0) for entry in candles if entry.get("close")]
        if len(closes) < 2:
            return None

        closes_array = np.asarray(closes, dtype=float)
        log_returns = np.diff(np.log(closes_array))
        if log_returns.size == 0:
            return None

        volatility = float(np.std(log_returns) * np.sqrt(365))
        if np.isnan(volatility) or np.isinf(volatility):
            return None

        return volatility

    async def _fetch_coincap_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch price from CoinCap API as fallback."""
        try:
            if symbol not in self.symbol_mappings["coincap"]:
                return {"success": False, "error": f"Symbol {symbol} not supported"}

            asset_id = self.symbol_mappings["coincap"][symbol]
            url = f"{self.apis['coincap']['base_url']}/assets/{asset_id}"

            timeout = aiohttp.ClientTimeout(total=10)
            max_retries = 3
            base_delay = 0.5
            last_error: Optional[Exception] = None

            for attempt in range(max_retries):
                try:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(url) as response:
                            if response.status == 429:
                                retry_after = int(response.headers.get("Retry-After", "1"))
                                raise MarketDataRateLimitError(
                                    message="CoinCap rate limit hit", retry_after=retry_after
                                )
                            if response.status >= 500:
                                raise MarketDataError(
                                    f"CoinCap server error: {response.status}"
                                )
                            if response.status != 200:
                                raise MarketDataError(
                                    f"CoinCap request failed: {response.status}"
                                )

                            response_data = await response.json()
                            data = response_data.get("data", {})
                            if not data:
                                raise MarketDataError("CoinCap returned empty payload")

                            result = {
                                "success": True,
                                "data": {
                                    "symbol": symbol,
                                    "price": float(data.get("priceUsd", 0) or 0),
                                    "change_24h": float(data.get("changePercent24Hr", 0) or 0),
                                    "volume_24h": float(data.get("volumeUsd24Hr", 0) or 0),
                                    "market_cap": float(data.get("marketCapUsd", 0) or 0),
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "source": "coincap",
                                },
                            }

                            await self._handle_api_success("coincap")
                            return result

                except MarketDataRateLimitError as rate_error:
                    last_error = rate_error
                    await self._handle_api_failure("coincap", str(rate_error))
                    delay = rate_error.retry_after or base_delay * (2 ** attempt)
                except (aiohttp.ClientError, asyncio.TimeoutError) as net_error:
                    last_error = net_error
                    await self._handle_api_failure("coincap", str(net_error))
                    delay = base_delay * (2 ** attempt)
                except MarketDataError as api_error:
                    last_error = api_error
                    await self._handle_api_failure("coincap", str(api_error))
                    delay = base_delay * (2 ** attempt)
                except Exception as unexpected_error:
                    last_error = unexpected_error
                    await self._handle_api_failure("coincap", str(unexpected_error))
                    delay = base_delay * (2 ** attempt)

                await asyncio.sleep(delay + random.uniform(0, 0.3))

            cached_fallback = await self._load_cached_price_entry(symbol)
            if cached_fallback:
                return {
                    "success": True,
                    "data": cached_fallback,
                    "metadata": {
                        "source": "cache",
                        "error": str(last_error) if last_error else None,
                    },
                }

            error_message = str(last_error) if last_error else "CoinCap request failed"
            return {"success": False, "error": error_message}

        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _fetch_coingecko_detailed(self, symbol: str) -> Dict[str, Any]:
        """Fetch detailed data from CoinGecko."""
        try:
            if symbol not in self.symbol_mappings["coingecko"]:
                return {"success": False, "error": f"Symbol {symbol} not supported"}

            coin_id = self.symbol_mappings["coingecko"][symbol]
            url = f"{self.apis['coingecko']['base_url']}/coins/{coin_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
            }

            max_retries = 3
            base_delay = 1.0

            timeout = aiohttp.ClientTimeout(total=30)
            last_error: Optional[Exception] = None

            for attempt in range(max_retries):
                try:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(url, params=params) as response:
                            if response.status == 429:
                                retry_after = int(response.headers.get("Retry-After", "1"))
                                raise MarketDataRateLimitError(
                                    message="CoinGecko rate limited",
                                    retry_after=retry_after,
                                )
                            if response.status >= 500:
                                raise MarketDataError(
                                    f"CoinGecko server error: {response.status}"
                                )
                            if response.status != 200:
                                raise MarketDataError(
                                    f"CoinGecko request failed: {response.status}"
                                )

                            data = await response.json()
                            market_data = data.get("market_data", {})

                            detailed_payload = {
                                "success": True,
                                "data": {
                                    "symbol": symbol,
                                    "name": data.get("name", ""),
                                    "price": market_data.get("current_price", {}).get("usd", 0),
                                    "market_cap": market_data.get("market_cap", {}).get("usd", 0),
                                    "volume_24h": market_data.get("total_volume", {}).get("usd", 0),
                                    "change_24h": market_data.get("price_change_percentage_24h", 0),
                                    "change_7d": market_data.get("price_change_percentage_7d", 0),
                                    "change_30d": market_data.get("price_change_percentage_30d", 0),
                                    "high_24h": market_data.get("high_24h", {}).get("usd", 0),
                                    "low_24h": market_data.get("low_24h", {}).get("usd", 0),
                                    "ath": market_data.get("ath", {}).get("usd", 0),
                                    "atl": market_data.get("atl", {}).get("usd", 0),
                                    "circulating_supply": market_data.get("circulating_supply", 0),
                                    "total_supply": market_data.get("total_supply", 0),
                                    "max_supply": market_data.get("max_supply", 0),
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "source": "coingecko",
                                },
                            }

                            await self._handle_api_success("coingecko")
                            return detailed_payload

                except MarketDataRateLimitError as rate_error:
                    last_error = rate_error
                    await self._handle_api_failure("coingecko", str(rate_error))
                    delay = rate_error.retry_after or base_delay * (2 ** attempt)
                except (aiohttp.ClientError, asyncio.TimeoutError) as net_error:
                    last_error = net_error
                    await self._handle_api_failure("coingecko", str(net_error))
                    delay = base_delay * (2 ** attempt)
                except MarketDataError as api_error:
                    last_error = api_error
                    await self._handle_api_failure("coingecko", str(api_error))
                    delay = base_delay * (2 ** attempt)
                except Exception as unexpected_error:
                    last_error = unexpected_error
                    await self._handle_api_failure("coingecko", str(unexpected_error))
                    delay = base_delay * (2 ** attempt)

                await asyncio.sleep(delay + random.uniform(0, 0.5))

            cached_fallback = await self._get_cached_response(f"detailed:{symbol}", "detailed")

            if isinstance(cached_fallback, dict):
                metadata = cached_fallback.get("metadata", {})
                metadata.update(
                    {
                        "source": "cache",
                        "error": str(last_error) if last_error else None,
                    }
                )
                cached_fallback["metadata"] = metadata
                return cached_fallback

            error_message = (
                str(last_error) if last_error else "CoinGecko detailed request failed"
            )
            return {"success": False, "error": error_message}

        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _fetch_batch_with_retries(self, batch: List[str], max_retries: int = 3) -> Dict[str, float]:
        """Fetch prices for a batch of symbols with retry logic."""
        for attempt in range(max_retries):
            try:
                # Use existing get_multiple_prices method for batch fetching
                result = await self.get_multiple_prices(batch)

                if result.get("success"):
                    # Extract price values from the result
                    prices = {}
                    for symbol, data in result.get("data", {}).items():
                        prices[symbol] = float(data.get("price", 0))
                    return prices
                else:
                    error = result.get("error", "Unknown error")
                    if "429" in str(error) or "Rate limit" in str(error):
                        # Rate limit hit - raise to trigger backoff
                        raise MarketDataRateLimitError(f"Rate limit exceeded: {error}")

                # Other error - retry with exponential backoff
                if attempt < max_retries - 1:
                    delay = 2 ** attempt
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final attempt failed
                    raise MarketDataBatchFetchError(
                        f"Batch fetch failed after {max_retries} attempts: {error}",
                        attempts=max_retries
                    )
            except MarketDataRateLimitError:
                # Re-raise rate limit errors immediately without retry
                raise
            except MarketDataBatchFetchError:
                # Re-raise batch fetch errors immediately
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = 2 ** attempt
                    logger.warning(f"Batch fetch attempt {attempt + 1} failed, retrying in {delay}s", error=str(e))
                    await asyncio.sleep(delay)
                else:
                    # Final attempt - raise as batch fetch error
                    raise MarketDataBatchFetchError(
                        f"Batch fetch failed after {max_retries} attempts: {str(e)}",
                        attempts=max_retries
                    )

    async def _get_stale_price(self, symbol: str) -> Optional[float]:
        """Get cached/stale price from Redis as fallback."""
        try:
            cache_key = f"price:{symbol}"
            cached_response = await self._get_cached_response(cache_key, "price")

            if not cached_response:
                return None

            if isinstance(cached_response, dict):
                data = cached_response.get("data", cached_response)
            else:
                data = cached_response

            if isinstance(data, dict) and "price" in data:
                return float(data.get("price", 0))

            if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
                return float(data["data"].get("price", 0))

            return None
        except Exception as e:
            logger.warning(f"Failed to get stale price for {symbol}", error=str(e))
            return None

    async def sync_market_data_batch(self, symbols: List[str], batch_size: int = 50) -> Dict[str, float]:
        results = {}
        batches = [symbols[i:i+batch_size] for i in range(0, len(symbols), batch_size)]
        current_backoff = 0
        for batch in batches:
            try:
                prices = await self._fetch_batch_with_retries(batch)
                results.update(prices)
            except Exception as e:
                if "429" in str(e):  # Rate limit detected
                    current_backoff = min(60, current_backoff + 10)  # Progressive backoff
                    await asyncio.sleep(current_backoff)
                    batch_size = max(10, batch_size // 2)  # Adaptive size reduction
                else:
                    logger.exception("Batch sync failed", exc_info=e)
                    # Stale cache fallback
                    for sym in batch:
                        results[sym] = await self._get_stale_price(sym) or 0.0
        return results
    
    async def get_exchange_rates(self) -> Dict[str, Any]:
        """Get USD exchange rates for fiat currencies."""
        try:
            # Use a free exchange rate API
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return {
                            "success": True,
                            "data": {
                                "base": "USD",
                                "rates": data.get("rates", {}),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }
                    else:
                        return {"success": False, "error": f"API error: {response.status}"}
                        
        except Exception as e:
            logger.error("Failed to get exchange rates", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _fetch_alpha_vantage_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch price from Alpha Vantage API."""
        try:
            if not self.api_keys.get("alpha_vantage"):
                return {"success": False, "error": "Alpha Vantage API key not configured"}
            
            if not await self._check_rate_limit("alpha_vantage"):
                return {"success": False, "error": "Rate limit exceeded for Alpha Vantage"}
            
            url = self.apis['alpha_vantage']['base_url']
            params = self._get_api_params("alpha_vantage", {
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": symbol,
                "to_currency": "USD"
            })
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        rate_data = data.get("Realtime Currency Exchange Rate", {})
                        
                        if rate_data:
                            price = float(rate_data.get("5. Exchange Rate", 0))
                            return {
                                "success": True,
                                "data": {
                                    "symbol": symbol,
                                    "price": price,
                                    "change_24h": 0,  # Alpha Vantage doesn't provide 24h change in this endpoint
                                    "volume_24h": 0,
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "source": "alpha_vantage"
                                }
                            }
                    
                    return {"success": False, "error": f"API error: {response.status}"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _fetch_finnhub_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch price from Finnhub API."""
        try:
            if not self.api_keys.get("finnhub"):
                return {"success": False, "error": "Finnhub API key not configured"}
            
            if not await self._check_rate_limit("finnhub"):
                return {"success": False, "error": "Rate limit exceeded for Finnhub"}
            
            # Finnhub crypto symbols format
            finnhub_symbol = f"BINANCE:{symbol}USDT"
            url = f"{self.apis['finnhub']['base_url']}/quote"
            
            params = self._get_api_params("finnhub", {
                "symbol": finnhub_symbol
            })
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("c"):  # Current price
                            current_price = float(data.get("c", 0))
                            prev_close = float(data.get("pc", current_price))
                            change_24h = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
                            
                            return {
                                "success": True,
                                "data": {
                                    "symbol": symbol,
                                    "price": current_price,
                                    "change_24h": change_24h,
                                    "volume_24h": 0,  # Finnhub doesn't provide volume in quote endpoint
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "source": "finnhub"
                                }
                            }
                    
                    return {"success": False, "error": f"API error: {response.status}"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _fetch_coinpaprika_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch price from CoinPaprika API as additional fallback."""
        try:
            if symbol not in self.symbol_mappings.get("coinpaprika", {}):
                return {"success": False, "error": f"Symbol {symbol} not supported"}
            
            if not await self._check_rate_limit("coinpaprika"):
                return {"success": False, "error": "Rate limit exceeded"}
            
            mapped_symbol = self.symbol_mappings["coinpaprika"][symbol]
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.apis['coinpaprika']['base_url']}/tickers/{mapped_symbol}"
                
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data and "quotes" in data and "USD" in data["quotes"]:
                            quote = data["quotes"]["USD"]
                            return {
                                "success": True,
                                "data": {
                                    "symbol": symbol,
                                    "price": float(quote["price"]),
                                    "market_cap": float(quote.get("market_cap", 0)),
                                    "volume_24h": float(quote.get("volume_24h", 0)),
                                    "percent_change_24h": float(quote.get("percent_change_24h", 0)),
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "source": "coinpaprika"
                                }
                            }
                    
                    return {"success": False, "error": f"API error: {response.status}"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global market data feeds instance
market_data_feeds = MarketDataFeeds()


# Convenience functions
async def get_crypto_price(symbol: str) -> Dict[str, Any]:
    """Get real-time crypto price."""
    return await market_data_feeds.get_real_time_price(symbol)


async def get_crypto_prices(symbols: List[str]) -> Dict[str, Any]:
    """Get multiple crypto prices."""
    return await market_data_feeds.get_multiple_prices(symbols)


async def get_market_overview() -> Dict[str, Any]:
    """Get market overview with top coins."""
    top_symbols = ["BTC", "ETH", "SOL", "ADA", "DOT", "MATIC", "LINK", "UNI"]
    return await market_data_feeds.get_multiple_prices(top_symbols)


async def get_market_snapshot(symbol: str, include_onchain: bool = False) -> Dict[str, Any]:
    """Convenience wrapper for aggregated market snapshots."""
    return await market_data_feeds.get_market_snapshot(symbol, include_onchain=include_onchain)


async def get_yield_opportunities(symbols: List[str]) -> Dict[str, Any]:
    """Convenience wrapper to fetch yield-bearing product information."""
    return await market_data_feeds.get_yield_opportunities(symbols)
