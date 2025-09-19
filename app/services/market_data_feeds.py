"""
Market Data Feeds - Real Free APIs

Provides real-time market data using free APIs like CoinGecko, CoinCap,
and other free sources for the AI money manager platform.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import aiohttp
import structlog
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.core.supabase import supabase_client

settings = get_settings()
logger = structlog.get_logger(__name__)


class MarketDataFeeds:
    """Real market data feeds using free APIs."""
    
    def __init__(self):
        self.redis = None
        
        # Load API keys from environment
        self.api_keys = {
            "alpha_vantage": settings.ALPHA_VANTAGE_API_KEY if hasattr(settings, 'ALPHA_VANTAGE_API_KEY') else None,
            "coingecko": settings.COINGECKO_API_KEY if hasattr(settings, 'COINGECKO_API_KEY') else None,
            "finnhub": settings.FINNHUB_API_KEY if hasattr(settings, 'FINNHUB_API_KEY') else None
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
        self.cache_ttl = {
            "price": 30,      # 30 seconds for prices
            "market": 300,    # 5 minutes for market data
            "trending": 600,  # 10 minutes for trending
            "global": 900     # 15 minutes for global data
        }
        
        # ENTERPRISE API fallback hierarchy with circuit breaker status
        self.api_fallbacks = {
            "price": ["coingecko", "coincap", "coinpaprika"],
            "market": ["coingecko", "alpha_vantage", "finnhub"],
            "trending": ["coingecko", "coinpaprika"],
            "global": ["coingecko", "coinpaprika"]
        }
        
        # ENTERPRISE CIRCUIT BREAKER STATE for external APIs
        self.circuit_breakers = {}
        for api_name in self.apis.keys():
            self.circuit_breakers[api_name] = {
                "failures": 0,
                "last_failure": 0,
                "open_until": 0,
                "max_failures": 5,
                "timeout": 300,  # 5 minutes
                "state": "closed",
                "last_success": 0,
                "recovery_attempts": 0
            }
        
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
        
        # Cache settings
        self.cache_ttl = {
            "price": 30,      # 30 seconds for prices
            "detailed": 300,  # 5 minutes for detailed data
            "markets": 600    # 10 minutes for market data
        }
    
    async def async_init(self):
        try:
            self.redis = await get_redis_client()
        except Exception as e:
            logger.warning("Redis not available for MarketDataFeeds", error=str(e))
            self.redis = None
    
    async def _check_rate_limit(self, api_name: str) -> bool:
        """ENTERPRISE: Check rate limits with circuit breaker protection."""
        current_time = time.time()
        
        # ENTERPRISE CIRCUIT BREAKER CHECK
        breaker = self.circuit_breakers.get(api_name, {})
        if current_time < breaker.get("open_until", 0):
            logger.debug(f"Circuit breaker OPEN for {api_name}")
            return False
        
        # Check traditional rate limits
        limiter = self.rate_limiters.get(api_name, {})
        
        # Reset window if needed (1 minute windows)
        if current_time - limiter.get("window_start", 0) >= 60:
            limiter["requests"] = 0
            limiter["window_start"] = current_time
        
        # Check if under limit
        if limiter["requests"] < limiter["max_requests"]:
            limiter["requests"] += 1
            return True
        
        return False
    
    def _handle_api_failure(self, api_name: str, error: str):
        """ENTERPRISE: Handle API failure - update circuit breaker with intelligent recovery."""
        breaker = self.circuit_breakers.get(api_name, {})
        current_time = time.time()
        
        breaker["failures"] = breaker.get("failures", 0) + 1
        breaker["last_failure"] = current_time
        
        # Intelligent failure threshold based on API characteristics
        max_failures = breaker.get("max_failures", 5)
        
        # Adjust thresholds for known API patterns
        if api_name == "coingecko":
            max_failures = 7  # CoinGecko can handle more requests
        elif api_name == "alpha_vantage":
            max_failures = 3  # Alpha Vantage has strict rate limits
        
        # Open circuit breaker if too many failures
        if breaker["failures"] >= max_failures:
            # Adaptive timeout based on failure pattern
            base_timeout = breaker.get("timeout", 300)
            
            # Exponential backoff for repeated failures
            recovery_attempts = breaker.get("recovery_attempts", 0)
            adaptive_timeout = min(base_timeout * (2 ** recovery_attempts), 1800)  # Max 30 minutes
            
            breaker["open_until"] = current_time + adaptive_timeout
            breaker["state"] = "open"
            breaker["recovery_attempts"] = recovery_attempts + 1
            
            logger.warning(
                f"Circuit breaker OPENED for {api_name} after {breaker['failures']} failures",
                adaptive_timeout=adaptive_timeout,
                recovery_attempts=recovery_attempts,
                error=error
            )
        else:
            logger.warning(
                f"API failure recorded for {api_name}",
                failures=breaker["failures"],
                max_failures=max_failures,
                error=error
            )
    
    def _handle_api_success(self, api_name: str):
        """ENTERPRISE: Handle API success - intelligent circuit breaker recovery."""
        breaker = self.circuit_breakers.get(api_name, {})
        current_time = time.time()
        
        # Record success metrics
        breaker["last_success"] = current_time
        
        # If circuit was open, transition to half-open first
        if breaker.get("state") == "open":
            breaker["state"] = "half_open"
            logger.info(f"Circuit breaker transitioning to HALF_OPEN for {api_name} - testing recovery")
        elif breaker.get("state") == "half_open":
            # Successful call in half-open state - close the circuit
            breaker["failures"] = 0
            breaker["last_failure"] = 0
            breaker["open_until"] = 0
            breaker["state"] = "closed"
            breaker["recovery_attempts"] = 0  # Reset recovery attempts on successful recovery
            
            logger.info(f"Circuit breaker CLOSED for {api_name} - API fully recovered")
        else:
            # Normal operation - just reset failure count
            breaker["failures"] = max(0, breaker.get("failures", 0) - 1)  # Gradual recovery
            
        self.circuit_breakers[api_name] = breaker
    
    def _get_api_params(self, api_name: str, base_params: Dict = None) -> Dict[str, Any]:
        """Get API parameters including API key if required."""
        params = base_params or {}
        
        api_config = self.apis.get(api_name, {})
        if api_config.get("requires_key") and self.api_keys.get(api_name):
            key_param = api_config.get("api_key_param", "apikey")
            params[key_param] = self.api_keys[api_name]
        
        return params
    
    async def get_real_time_price(self, symbol: str) -> Dict[str, Any]:
        """Get real-time price data for a symbol."""
        try:
            # ENTERPRISE REDIS RESILIENCE - Check cache first if Redis is available
            cache_key = f"price:{symbol}"
            if self.redis:
                cached_data = await self.redis.get(cache_key)
                
                if cached_data:
                    try:
                        import json
                        return json.loads(cached_data)
                    except:
                        pass
            
            # Try APIs in order of preference with rate limiting
            apis_to_try = [
                ("coingecko", self._fetch_coingecko_price),
                ("alpha_vantage", self._fetch_alpha_vantage_price),
                ("finnhub", self._fetch_finnhub_price),
                ("coincap", self._fetch_coincap_price)
            ]
            
            price_data = {"success": False, "error": "No APIs available"}
            
            for api_name, fetch_method in apis_to_try:
                try:
                    # ENTERPRISE: Check circuit breaker before API call
                    if not await self._check_rate_limit(api_name):
                        continue
                    
                    price_data = await fetch_method(symbol)
                    if price_data.get("success"):
                        # ENTERPRISE: Record successful API call
                        self._handle_api_success(api_name)
                        break
                    else:
                        # ENTERPRISE: Handle API failure
                        self._handle_api_failure(api_name, price_data.get("error", "Unknown error"))
                except Exception as e:
                    logger.warning(f"Failed to fetch from {api_name}", error=str(e))
                    # ENTERPRISE: Handle API exception
                    self._handle_api_failure(api_name, str(e))
                    continue
            
            if price_data.get("success"):
                # ENTERPRISE REDIS RESILIENCE - Cache the result if Redis is available
                if self.redis:
                    import json
                    await self.redis.setex(
                        cache_key,
                        self.cache_ttl["price"],
                        json.dumps(price_data)
                    )
                
                # Sync to Supabase (if available)
                try:
                    from app.core.supabase import supabase_client
                    await supabase_client.sync_market_data(symbol, price_data.get("data", {}))
                except ImportError:
                    # Supabase not configured, skip sync
                    pass
                except Exception as e:
                    logger.warning("Supabase sync failed", error=str(e))
            
            return price_data
            
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def get_price_with_enterprise_fallback(self, symbol: str, data_type: str = "price") -> Dict[str, Any]:
        """ENTERPRISE-GRADE price fetching with comprehensive fallback strategies."""
        cache_key = f"{data_type}:{symbol}"
        
        try:
            # Check cache first if Redis is available
            if self.redis:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    import json
                    return json.loads(cached_data)
            
            # Get fallback hierarchy for this data type
            api_hierarchy = self.api_fallbacks.get(data_type, ["coingecko", "coincap"])
            
            last_error = None
            for api_name in api_hierarchy:
                try:
                    # Check rate limits
                    if not self._check_rate_limit(api_name):
                        logger.warning(f"Rate limit exceeded for {api_name}, trying next API")
                        continue
                    
                    # Attempt to fetch data
                    if api_name == "coingecko":
                        result = await self._fetch_coingecko_price(symbol)
                    elif api_name == "coincap":
                        result = await self._fetch_coincap_price(symbol)
                    elif api_name == "coinpaprika":
                        result = await self._fetch_coinpaprika_price(symbol)
                    else:
                        continue
                    
                    if result.get("success"):
                        # Cache successful result if Redis is available
                        if self.redis:
                            import json
                            await self.redis.setex(
                                cache_key,
                                self.cache_ttl.get(data_type, 60),
                                json.dumps(result)
                            )
                        return result
                        
                except Exception as e:
                    logger.warning(f"API {api_name} failed for {symbol}: {str(e)}")
                    last_error = e
                    continue
            
            # All APIs failed, return error
            return {
                "success": False,
                "error": f"All APIs failed. Last error: {str(last_error)}",
                "data": {}
            }
            
        except Exception as e:
            logger.error(f"Enterprise fallback failed for {symbol}: {str(e)}")
            return {"success": False, "error": str(e), "data": {}}

    async def get_detailed_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get detailed market data including volume, market cap, etc."""
        try:
            # ENTERPRISE REDIS RESILIENCE
            cache_key = f"detailed:{symbol}"
            if self.redis:
                cached_data = await self.redis.get(cache_key)
                
                if cached_data:
                    try:
                        import json
                        return json.loads(cached_data)
                    except:
                        pass
            
            # Get detailed data from CoinGecko
            detailed_data = await self._fetch_coingecko_detailed(symbol)
            
            if detailed_data.get("success"):
                # ENTERPRISE REDIS RESILIENCE - Cache if Redis is available
                if self.redis:
                    import json
                    await self.redis.setex(
                        cache_key,
                        self.cache_ttl["detailed"],
                        json.dumps(detailed_data)
                    )
            
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
            
            async with aiohttp.ClientSession() as session:
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
                            
                            # ENTERPRISE REDIS RESILIENCE - Cache individual prices if Redis is available
                            if self.redis:
                                await self.redis.setex(
                                    f"price:{symbol}",
                                    self.cache_ttl["price"],
                                    str({
                                        "success": True,
                                        "data": result["data"][symbol]
                                    })
                                )
                        
                        return result
                    else:
                        return {"success": False, "error": f"API error: {response.status}"}
                        
        except Exception as e:
            logger.error("Failed to get multiple prices", error=str(e))
            return {"success": False, "error": str(e)}
    
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
                        
                        # Try to return cached data if available
                        if self.redis:
                            try:
                                cached_key = f"market_price:{symbol.lower()}"
                                cached_data = await self.redis.get(cached_key)
                                if cached_data:
                                    price_data = json.loads(cached_data)
                                    price_data["from_cache"] = True
                                    return {"success": True, "data": price_data}
                            except Exception:
                                pass
                        
                        return {"success": False, "error": error_msg}
                    
                    return {"success": False, "error": f"API error: {response.status}"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _fetch_coincap_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch price from CoinCap API as fallback."""
        try:
            if symbol not in self.symbol_mappings["coincap"]:
                return {"success": False, "error": f"Symbol {symbol} not supported"}
            
            asset_id = self.symbol_mappings["coincap"][symbol]
            url = f"{self.apis['coincap']['base_url']}/assets/{asset_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        data = response_data.get("data", {})
                        
                        if data:
                            return {
                                "success": True,
                                "data": {
                                    "symbol": symbol,
                                    "price": float(data.get("priceUsd", 0)),
                                    "change_24h": float(data.get("changePercent24Hr", 0)),
                                    "volume_24h": float(data.get("volumeUsd24Hr", 0)),
                                    "market_cap": float(data.get("marketCapUsd", 0)),
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "source": "coincap"
                                }
                            }
                    
                    return {"success": False, "error": f"API error: {response.status}"}
                    
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
                "developer_data": "false"
            }
            
            # Enterprise-grade retry logic with exponential backoff
            max_retries = 3
            base_delay = 1.0
            
            for attempt in range(max_retries):
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                        async with session.get(url, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                market_data = data.get("market_data", {})
                                
                                return {
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
                                        "source": "coingecko"
                                    }
                                }
                            elif response.status == 429:
                                # Rate limit exceeded - implement exponential backoff
                                if attempt < max_retries - 1:
                                    delay = base_delay * (2 ** attempt) + (time.time() % 1)  # Add jitter
                                    logger.warning(f"CoinGecko rate limit hit for {symbol}, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                                    await asyncio.sleep(delay)
                                    continue
                                else:
                                    logger.error(f"CoinGecko rate limit exceeded for {symbol} after {max_retries} attempts")
                                    return {"success": False, "error": "Rate limit exceeded", "status_code": 429}
                            else:
                                return {"success": False, "error": f"API error: {response.status}", "status_code": response.status}
                                
                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"CoinGecko timeout for {symbol}, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        return {"success": False, "error": "Request timeout"}
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"CoinGecko request failed for {symbol}: {e}, retrying in {delay:.2f}s")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # On final attempt, return error instead of raising
                        logger.error(f"CoinGecko request failed for {symbol} after {max_retries} attempts: {e}")
                        return {"success": False, "error": str(e), "final_attempt": True}
            
            return {"success": False, "error": "Max retries exceeded"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
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
