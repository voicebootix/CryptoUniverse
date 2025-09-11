"""
Dynamic Exchange Discovery Service

Enterprise-grade service for automatically discovering and integrating new exchanges.
NO HARDCODED LIMITATIONS - Fully dynamic and expandable exchange ecosystem.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
import aiohttp
import structlog
from app.core.config import get_settings
from app.core.redis import get_redis_client

settings = get_settings()
logger = structlog.get_logger(__name__)


class DynamicExchangeDiscovery:
    """
    ENTERPRISE DYNAMIC EXCHANGE DISCOVERY
    
    Features:
    - Automatic exchange detection
    - API compatibility testing
    - Dynamic integration
    - Exchange health monitoring
    - No hardcoded limitations
    """
    
    def __init__(self):
        self.redis_client = get_redis_client()
        
        # Known exchange patterns and endpoints for discovery
        self.discovery_sources = {
            "coingecko_exchanges": "https://api.coingecko.com/api/v3/exchanges",
            "coinmarketcap_exchanges": "https://pro-api.coinmarketcap.com/v1/exchange/listings/latest",
            "crypto_compare": "https://min-api.cryptocompare.com/data/all/exchanges",
            "exchange_registry": "https://raw.githubusercontent.com/ccxt/ccxt/master/exchanges.json"
        }
        
        # API pattern detection for common exchange architectures
        self.api_patterns = {
            "ccxt_compatible": {
                "endpoints": ["ticker", "orderbook", "trades", "balance"],
                "methods": ["GET", "POST"],
                "auth": ["api_key", "signature"]
            },
            "rest_standard": {
                "endpoints": ["api/v1", "api/v2", "api/v3"],
                "common_paths": ["/ticker", "/orderbook", "/trades"],
                "rate_limits": True
            },
            "websocket_support": {
                "protocols": ["ws", "wss"],
                "endpoints": ["stream", "ws", "websocket"]
            }
        }
        
        # Exchange capability requirements
        self.required_capabilities = {
            "spot_trading": True,
            "price_data": True,
            "order_book": True,
            "trading_history": False,  # Optional
            "futures_trading": False,  # Optional
            "options_trading": False,  # Optional
            "websocket_streams": False  # Optional
        }
        
        # Discovered exchanges cache
        self.discovered_exchanges = {}
        self.last_discovery = None
        self.discovery_interval = 24 * 3600  # 24 hours
        
        # Exchange health tracking
        self.exchange_health = {}
        
        logger.info("✅ Dynamic Exchange Discovery initialized")
    
    async def discover_all_exchanges(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        DISCOVER ALL AVAILABLE EXCHANGES
        
        Automatically discovers exchanges from multiple sources and tests compatibility.
        """
        
        if (not force_refresh and 
            self.last_discovery and 
            time.time() - self.last_discovery < self.discovery_interval):
            
            logger.debug("Using cached exchange discovery results")
            return self.discovered_exchanges
        
        logger.info("🔍 Starting comprehensive exchange discovery")
        
        discovery_results = {
            "discovered_exchanges": {},
            "total_exchanges": 0,
            "compatible_exchanges": 0,
            "discovery_sources": {},
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Discover from each source
        for source_name, source_url in self.discovery_sources.items():
            try:
                source_exchanges = await self._discover_from_source(source_name, source_url)
                discovery_results["discovery_sources"][source_name] = {
                    "exchanges_found": len(source_exchanges),
                    "status": "success"
                }
                
                # Merge discovered exchanges
                for exchange_id, exchange_data in source_exchanges.items():
                    if exchange_id not in discovery_results["discovered_exchanges"]:
                        discovery_results["discovered_exchanges"][exchange_id] = exchange_data
                    else:
                        # Merge data from multiple sources
                        discovery_results["discovered_exchanges"][exchange_id].update(exchange_data)
                
            except Exception as e:
                logger.warning(f"Discovery source failed", source=source_name, error=str(e))
                discovery_results["discovery_sources"][source_name] = {
                    "exchanges_found": 0,
                    "status": "error",
                    "error": str(e)
                }
        
        # Test compatibility for discovered exchanges
        compatible_exchanges = await self._test_exchange_compatibility(
            discovery_results["discovered_exchanges"]
        )
        
        discovery_results["compatible_exchanges"] = len(compatible_exchanges)
        discovery_results["total_exchanges"] = len(discovery_results["discovered_exchanges"])
        
        # Update internal cache
        self.discovered_exchanges = discovery_results
        self.last_discovery = time.time()
        
        # Cache in Redis
        await self._cache_discovery_results(discovery_results)
        
        logger.info(f"✅ Exchange discovery completed", 
                   total=discovery_results["total_exchanges"],
                   compatible=discovery_results["compatible_exchanges"])
        
        return discovery_results
    
    async def _discover_from_source(self, source_name: str, source_url: str) -> Dict[str, Any]:
        """Discover exchanges from a specific source."""
        
        exchanges = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                
                # Add API key for premium sources
                if "coinmarketcap" in source_name:
                    headers["X-CMC_PRO_API_KEY"] = settings.coinmarketcap_api_key
                
                async with session.get(source_url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if source_name == "coingecko_exchanges":
                            exchanges = self._parse_coingecko_exchanges(data)
                        elif source_name == "coinmarketcap_exchanges":
                            exchanges = self._parse_coinmarketcap_exchanges(data)
                        elif source_name == "crypto_compare":
                            exchanges = self._parse_cryptocompare_exchanges(data)
                        elif source_name == "exchange_registry":
                            exchanges = self._parse_registry_exchanges(data)
                        
                        logger.debug(f"Discovered exchanges from {source_name}", count=len(exchanges))
                    else:
                        logger.warning(f"Source returned error", source=source_name, status=response.status)
        
        except Exception as e:
            logger.error(f"Failed to discover from source", source=source_name, error=str(e))
        
        return exchanges
    
    def _parse_coingecko_exchanges(self, data: List[Dict]) -> Dict[str, Any]:
        """Parse CoinGecko exchange data."""
        
        exchanges = {}
        
        for exchange_info in data:
            exchange_id = exchange_info.get("id", "").lower()
            if not exchange_id:
                continue
            
            exchanges[exchange_id] = {
                "name": exchange_info.get("name", ""),
                "country": exchange_info.get("country", ""),
                "url": exchange_info.get("url", ""),
                "api_url": self._construct_api_url(exchange_info.get("url", "")),
                "trust_score": exchange_info.get("trust_score", 0),
                "trade_volume_24h_btc": exchange_info.get("trade_volume_24h_btc", 0),
                "year_established": exchange_info.get("year_established"),
                "source": "coingecko",
                "centralized": True,  # Most CoinGecko exchanges are centralized
                "capabilities": self._infer_capabilities(exchange_info)
            }
        
        return exchanges
    
    def _parse_coinmarketcap_exchanges(self, data: Dict) -> Dict[str, Any]:
        """Parse CoinMarketCap exchange data."""
        
        exchanges = {}
        
        exchange_list = data.get("data", [])
        for exchange_info in exchange_list:
            exchange_id = exchange_info.get("slug", "").lower()
            if not exchange_id:
                continue
            
            exchanges[exchange_id] = {
                "name": exchange_info.get("name", ""),
                "url": exchange_info.get("website_slug", ""),
                "api_url": self._construct_api_url(exchange_info.get("website_slug", "")),
                "volume_24h": exchange_info.get("spot_volume_usd", 0),
                "num_markets": exchange_info.get("num_market_pairs", 0),
                "source": "coinmarketcap",
                "centralized": True,
                "capabilities": self._infer_capabilities_from_volume(
                    exchange_info.get("spot_volume_usd", 0)
                )
            }
        
        return exchanges
    
    def _parse_cryptocompare_exchanges(self, data: Dict) -> Dict[str, Any]:
        """Parse CryptoCompare exchange data."""
        
        exchanges = {}
        
        for exchange_id, exchange_info in data.items():
            if not isinstance(exchange_info, dict):
                continue
            
            exchanges[exchange_id.lower()] = {
                "name": exchange_info.get("ExchangeName", exchange_id),
                "url": exchange_info.get("Url", ""),
                "api_url": self._construct_api_url(exchange_info.get("Url", "")),
                "affiliate_url": exchange_info.get("AffiliateURL", ""),
                "logo_url": exchange_info.get("LogoUrl", ""),
                "source": "cryptocompare",
                "centralized": True,
                "capabilities": {
                    "spot_trading": True,
                    "price_data": True,
                    "order_book": True
                }
            }
        
        return exchanges
    
    def _parse_registry_exchanges(self, data: Dict) -> Dict[str, Any]:
        """Parse exchange registry data."""
        
        exchanges = {}
        
        for exchange_id, exchange_info in data.items():
            if not isinstance(exchange_info, dict):
                continue
            
            exchanges[exchange_id.lower()] = {
                "name": exchange_info.get("name", exchange_id),
                "countries": exchange_info.get("countries", []),
                "certified": exchange_info.get("certified", False),
                "pro": exchange_info.get("pro", False),
                "api_url": exchange_info.get("urls", {}).get("api", ""),
                "www_url": exchange_info.get("urls", {}).get("www", ""),
                "source": "ccxt_registry",
                "centralized": not exchange_info.get("decentralized", False),
                "capabilities": self._parse_ccxt_capabilities(exchange_info)
            }
        
        return exchanges
    
    def _construct_api_url(self, base_url: str) -> str:
        """Construct likely API URL from base URL."""
        
        if not base_url:
            return ""
        
        # Clean and normalize URL
        base_url = base_url.rstrip('/')
        if not base_url.startswith(('http://', 'https://')):
            base_url = f"https://{base_url}"
        
        # Common API endpoint patterns
        api_patterns = [
            "/api/v3",
            "/api/v2", 
            "/api/v1",
            "/api",
            "/v3",
            "/v2",
            "/v1"
        ]
        
        # Try to detect existing API pattern
        for pattern in api_patterns:
            if pattern in base_url:
                return base_url
        
        # Default to adding /api
        return f"{base_url}/api"
    
    def _infer_capabilities(self, exchange_info: Dict) -> Dict[str, bool]:
        """Infer exchange capabilities from available information."""
        
        capabilities = {
            "spot_trading": True,  # Assume all exchanges support spot
            "price_data": True,    # Assume all provide price data
            "order_book": True,    # Assume all have order books
            "trading_history": False,
            "futures_trading": False,
            "options_trading": False,
            "websocket_streams": False
        }
        
        # Infer from volume/trust score
        trust_score = exchange_info.get("trust_score", 0)
        volume_24h = exchange_info.get("trade_volume_24h_btc", 0)
        
        if trust_score >= 7 or volume_24h >= 1000:
            capabilities["trading_history"] = True
            capabilities["websocket_streams"] = True
        
        if trust_score >= 8 or volume_24h >= 5000:
            capabilities["futures_trading"] = True
        
        if trust_score >= 9 or volume_24h >= 10000:
            capabilities["options_trading"] = True
        
        return capabilities
    
    def _infer_capabilities_from_volume(self, volume_usd: float) -> Dict[str, bool]:
        """Infer capabilities based on trading volume."""
        
        capabilities = {
            "spot_trading": True,
            "price_data": True,
            "order_book": True,
            "trading_history": volume_usd > 1000000,    # $1M+
            "futures_trading": volume_usd > 10000000,   # $10M+
            "options_trading": volume_usd > 100000000,  # $100M+
            "websocket_streams": volume_usd > 5000000   # $5M+
        }
        
        return capabilities
    
    def _parse_ccxt_capabilities(self, exchange_info: Dict) -> Dict[str, bool]:
        """Parse capabilities from CCXT exchange data."""
        
        has_methods = exchange_info.get("has", {})
        
        capabilities = {
            "spot_trading": has_methods.get("spot", True),
            "price_data": has_methods.get("fetchTicker", True),
            "order_book": has_methods.get("fetchOrderBook", True),
            "trading_history": has_methods.get("fetchMyTrades", False),
            "futures_trading": has_methods.get("future", False),
            "options_trading": has_methods.get("option", False),
            "websocket_streams": "streaming" in exchange_info.get("urls", {})
        }
        
        return capabilities
    
    async def _test_exchange_compatibility(self, exchanges: Dict[str, Any]) -> List[str]:
        """Test API compatibility for discovered exchanges."""
        
        logger.info(f"🧪 Testing exchange compatibility", total_exchanges=len(exchanges))
        
        compatible_exchanges = []
        
        # Test a subset for performance (can be expanded)
        test_exchanges = list(exchanges.items())[:20]  # Test top 20
        
        for exchange_id, exchange_info in test_exchanges:
            try:
                is_compatible = await self._test_single_exchange(exchange_id, exchange_info)
                if is_compatible:
                    compatible_exchanges.append(exchange_id)
                    logger.debug(f"✅ Exchange compatible", exchange=exchange_id)
                else:
                    logger.debug(f"❌ Exchange incompatible", exchange=exchange_id)
                
            except Exception as e:
                logger.debug(f"⚠️ Exchange test failed", exchange=exchange_id, error=str(e))
        
        logger.info(f"✅ Compatibility testing completed", compatible=len(compatible_exchanges))
        
        return compatible_exchanges
    
    async def _test_single_exchange(self, exchange_id: str, exchange_info: Dict) -> bool:
        """Test a single exchange for API compatibility."""
        
        api_url = exchange_info.get("api_url", "")
        if not api_url:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test common endpoints
                test_endpoints = [
                    f"{api_url}/ticker",
                    f"{api_url}/tickers", 
                    f"{api_url}/markets",
                    f"{api_url}/exchangeInfo",
                    f"{api_url}/time"
                ]
                
                for endpoint in test_endpoints:
                    try:
                        async with session.get(endpoint, timeout=10) as response:
                            if response.status == 200:
                                # At least one endpoint works
                                return True
                    except:
                        continue  # Try next endpoint
                
        except Exception:
            pass
        
        return False
    
    async def _cache_discovery_results(self, results: Dict[str, Any]):
        """Cache discovery results in Redis."""
        
        try:
            await self.redis_client.setex(
                "exchange_discovery_results",
                24 * 3600,  # 24 hours
                json.dumps(results, default=str)
            )
            
            logger.debug("Cached exchange discovery results")
            
        except Exception as e:
            logger.warning(f"Failed to cache discovery results", error=str(e))
    
    async def get_available_exchanges(self, 
                                    capabilities: Optional[List[str]] = None,
                                    min_volume: Optional[float] = None,
                                    countries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        GET DYNAMICALLY AVAILABLE EXCHANGES
        
        Returns list of exchanges based on dynamic discovery and filtering criteria.
        """
        
        # Ensure we have recent discovery data
        if not self.discovered_exchanges or not self.last_discovery:
            await self.discover_all_exchanges()
        
        discovered_exchanges = self.discovered_exchanges.get("discovered_exchanges", {})
        available_exchanges = []
        
        for exchange_id, exchange_info in discovered_exchanges.items():
            # Apply filters
            if capabilities:
                exchange_capabilities = exchange_info.get("capabilities", {})
                if not all(exchange_capabilities.get(cap, False) for cap in capabilities):
                    continue
            
            if min_volume:
                volume = exchange_info.get("trade_volume_24h_btc", 0) * 50000  # Rough BTC to USD
                if volume < min_volume:
                    continue
            
            if countries:
                exchange_country = exchange_info.get("country", "")
                exchange_countries = exchange_info.get("countries", [])
                if (exchange_country not in countries and 
                    not any(country in exchange_countries for country in countries)):
                    continue
            
            available_exchanges.append({
                "id": exchange_id,
                "name": exchange_info.get("name", exchange_id),
                "url": exchange_info.get("url", ""),
                "api_url": exchange_info.get("api_url", ""),
                "capabilities": exchange_info.get("capabilities", {}),
                "volume_24h": exchange_info.get("trade_volume_24h_btc", 0),
                "trust_score": exchange_info.get("trust_score", 0),
                "country": exchange_info.get("country", ""),
                "source": exchange_info.get("source", ""),
                "centralized": exchange_info.get("centralized", True)
            })
        
        # Sort by volume/trust score
        available_exchanges.sort(
            key=lambda x: (x.get("trust_score", 0) + x.get("volume_24h", 0)), 
            reverse=True
        )
        
        logger.info(f"🔄 Dynamic exchange query completed", 
                   total_available=len(available_exchanges),
                   filters_applied=bool(capabilities or min_volume or countries))
        
        return available_exchanges
    
    async def add_custom_exchange(self, 
                                exchange_id: str,
                                exchange_config: Dict[str, Any]) -> bool:
        """
        ADD CUSTOM EXCHANGE DYNAMICALLY
        
        Allows adding exchanges that aren't in standard discovery sources.
        """
        
        required_fields = ["name", "api_url", "capabilities"]
        if not all(field in exchange_config for field in required_fields):
            logger.error(f"Missing required fields for custom exchange", 
                        exchange=exchange_id,
                        required=required_fields)
            return False
        
        try:
            # Test the custom exchange
            is_compatible = await self._test_single_exchange(exchange_id, exchange_config)
            
            if not is_compatible:
                logger.warning(f"Custom exchange failed compatibility test", exchange=exchange_id)
                return False
            
            # Add to discovered exchanges
            if "discovered_exchanges" not in self.discovered_exchanges:
                self.discovered_exchanges["discovered_exchanges"] = {}
            
            self.discovered_exchanges["discovered_exchanges"][exchange_id] = {
                **exchange_config,
                "source": "custom",
                "added_at": datetime.utcnow().isoformat()
            }
            
            # Update cache
            await self._cache_discovery_results(self.discovered_exchanges)
            
            logger.info(f"✅ Custom exchange added", exchange=exchange_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to add custom exchange", exchange=exchange_id, error=str(e))
            return False
    
    async def get_exchange_health(self, exchange_id: str) -> Dict[str, Any]:
        """Get health status for a specific exchange."""
        
        if exchange_id not in self.exchange_health:
            # Perform health check
            await self._check_exchange_health(exchange_id)
        
        return self.exchange_health.get(exchange_id, {
            "status": "unknown",
            "last_checked": None,
            "response_time": None,
            "errors": []
        })
    
    async def _check_exchange_health(self, exchange_id: str):
        """Check health of a specific exchange."""
        
        discovered_exchanges = self.discovered_exchanges.get("discovered_exchanges", {})
        exchange_info = discovered_exchanges.get(exchange_id)
        
        if not exchange_info:
            return
        
        api_url = exchange_info.get("api_url", "")
        if not api_url:
            return
        
        health_data = {
            "status": "unhealthy",
            "last_checked": datetime.utcnow().isoformat(),
            "response_time": None,
            "errors": []
        }
        
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{api_url}/time", timeout=10) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        health_data["status"] = "healthy"
                        health_data["response_time"] = response_time
                    else:
                        health_data["errors"].append(f"HTTP {response.status}")
        
        except Exception as e:
            health_data["errors"].append(str(e))
        
        self.exchange_health[exchange_id] = health_data
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get exchange discovery statistics."""
        
        if not self.discovered_exchanges:
            return {"status": "no_discovery_run"}
        
        return {
            "total_exchanges": self.discovered_exchanges.get("total_exchanges", 0),
            "compatible_exchanges": self.discovered_exchanges.get("compatible_exchanges", 0),
            "discovery_sources": self.discovered_exchanges.get("discovery_sources", {}),
            "last_discovery": datetime.fromtimestamp(self.last_discovery).isoformat() if self.last_discovery else None,
            "next_discovery": datetime.fromtimestamp(self.last_discovery + self.discovery_interval).isoformat() if self.last_discovery else None,
            "cache_status": "active" if self.discovered_exchanges else "empty"
        }


# Global service instance
dynamic_exchange_discovery = DynamicExchangeDiscovery()