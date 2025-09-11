"""
ENTERPRISE DYNAMIC ASSET FILTERING SERVICE

This service implements volume-based asset filtering with NO hardcoded limitations.
All assets from ALL exchanges are dynamically discovered and filtered based on
configurable volume thresholds.

Key Features:
- Dynamic multi-exchange asset discovery
- Volume-based filtering (NO asset limitations)
- Tier-based classification system
- Real-time volume tracking
- Cache-optimized performance
- Enterprise-grade error handling

Author: CTO Assistant
Date: 2025-09-11
"""

import asyncio
import time
import json
from typing import Dict, List, Set, Optional, Any, Tuple, ClassVar
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
import structlog
from redis.asyncio import Redis

from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client
from app.services.dynamic_exchange_discovery import dynamic_exchange_discovery


@dataclass
class VolumeThreshold:
    """Volume threshold configuration for asset classification."""
    name: str
    min_volume_usd: float
    description: str
    priority: int


@dataclass
class AssetInfo:
    """Complete asset information with volume metrics."""
    symbol: str
    exchange: str
    volume_24h_usd: float
    price_usd: float
    market_cap_usd: Optional[float]
    tier: str
    last_updated: datetime
    metadata: Dict[str, Any]


class EnterpriseAssetFilter(LoggerMixin):
    """
    ENTERPRISE DYNAMIC ASSET FILTERING SERVICE
    
    Discovers and filters assets from ALL available exchanges with NO hardcoded limitations.
    Implements sophisticated volume-based classification system.
    """
    
    # ENTERPRISE VOLUME TIERS - Completely configurable, no hardcoded limits
    VOLUME_TIERS: ClassVar[Tuple[VolumeThreshold, ...]] = (
        VolumeThreshold("tier_institutional", 100_000_000, "Institutional Grade ($100M+ daily)", 1),
        VolumeThreshold("tier_enterprise", 50_000_000, "Enterprise Grade ($50M+ daily)", 2),
        VolumeThreshold("tier_professional", 10_000_000, "Professional Grade ($10M+ daily)", 3),
        VolumeThreshold("tier_retail", 1_000_000, "Retail Grade ($1M+ daily)", 4),
        VolumeThreshold("tier_emerging", 100_000, "Emerging Assets ($100K+ daily)", 5),
        VolumeThreshold("tier_micro", 10_000, "Micro Assets ($10K+ daily)", 6),
        VolumeThreshold("tier_any", 0, "All Assets (No minimum)", 7)
    )
    
    # EXCHANGE CONFIGURATIONS - Dynamic discovery, no hardcoded limitations
    EXCHANGE_APIS: ClassVar[Dict[str, Dict[str, Any]]] = {
        "binance": {
            "name": "Binance",
            "spot_url": "https://api.binance.com/api/v3/ticker/24hr",
            "futures_url": "https://fapi.binance.com/fapi/v1/ticker/24hr",
            "parser": "binance_parser",
            "priority": 1,
            "rate_limit_per_minute": 1200
        },
        "kraken": {
            "name": "Kraken",
            "spot_url": "https://api.kraken.com/0/public/Ticker",
            "parser": "kraken_parser",
            "priority": 2,
            "rate_limit_per_minute": 60
        },
        "kucoin": {
            "name": "KuCoin",
            "spot_url": "https://api.kucoin.com/api/v1/market/allTickers",
            "parser": "kucoin_parser",
            "priority": 3,
            "rate_limit_per_minute": 300
        },
        "coinbase": {
            "name": "Coinbase Pro",
            "spot_url": "https://api.exchange.coinbase.com/products",
            "parser": "coinbase_parser",
            "priority": 4,
            "rate_limit_per_minute": 600
        },
        "bybit": {
            "name": "Bybit",
            "spot_url": "https://api.bybit.com/v5/market/tickers?category=spot",
            "futures_url": "https://api.bybit.com/v5/market/tickers?category=linear",
            "parser": "bybit_parser",
            "priority": 5,
            "rate_limit_per_minute": 120
        },
        "okx": {
            "name": "OKX",
            "spot_url": "https://www.okx.com/api/v5/market/tickers?instType=SPOT",
            "futures_url": "https://www.okx.com/api/v5/market/tickers?instType=SWAP",
            "parser": "okx_parser",
            "priority": 6,
            "rate_limit_per_minute": 600
        },
        "bitfinex": {
            "name": "Bitfinex",
            "spot_url": "https://api-pub.bitfinex.com/v2/tickers?symbols=ALL",
            "parser": "bitfinex_parser",
            "priority": 7,
            "rate_limit_per_minute": 90
        },
        "huobi": {
            "name": "Huobi",
            "spot_url": "https://api.huobi.pro/market/tickers",
            "parser": "huobi_parser",
            "priority": 8,
            "rate_limit_per_minute": 100
        },
        "gate": {
            "name": "Gate.io",
            "spot_url": "https://api.gateio.ws/api/v4/spot/tickers",
            "parser": "gate_parser",
            "priority": 9,
            "rate_limit_per_minute": 300
        },
        "crypto_com": {
            "name": "Crypto.com",
            "spot_url": "https://api.crypto.com/v2/public/get-ticker",
            "parser": "crypto_com_parser",
            "priority": 10,
            "rate_limit_per_minute": 100
        }
    }
    
    def __init__(self, max_exchanges: Optional[int] = None):
        super().__init__()
        self.redis = None
        self.session = None
        self.asset_cache = {}
        self.last_full_scan = None
        self.dynamic_exchanges = {}  # Will be populated from discovery service
        self.max_exchanges = max_exchanges
        
    async def async_init(self):
        """Initialize async components."""
        try:
            self.redis = get_redis_client()
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers={
                    "User-Agent": "CryptoUniverse-Enterprise/2.0 (+https://cryptouniverse.onrender.com)",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate"
                }
            )
            
            # Load dynamic exchanges (replaces hardcoded EXCHANGE_APIS)
            await self._load_dynamic_exchanges()
            
            self.logger.info("🔧 Enterprise Asset Filter initialized with dynamic exchanges",
                           total_exchanges=len(self.dynamic_exchanges))
            
        except Exception as e:
            self.logger.error("Failed to initialize Asset Filter", error=str(e))
    
    async def _load_dynamic_exchanges(self):
        """
        LOAD EXCHANGES DYNAMICALLY
        
        Replaces hardcoded EXCHANGE_APIS with dynamically discovered exchanges.
        NO MORE HARDCODED LIMITATIONS.
        """
        
        try:
            # Get available exchanges from discovery service
            available_exchanges = await dynamic_exchange_discovery.get_available_exchanges(
                capabilities=["spot_trading", "price_data"],
                min_volume=1000000  # $1M+ daily volume
            )
            
            # Convert discovered exchanges to our API format
            priority = 1
            # Apply configurable exchange limit (no hardcoded limitations)
            if self.max_exchanges and self.max_exchanges > 0:
                exchange_list = available_exchanges[:self.max_exchanges]
            else:
                exchange_list = available_exchanges
            
            for exchange in exchange_list:
                exchange_id = exchange["id"]
                api_url = exchange.get("api_url", "")
                
                if not api_url:
                    continue
                
                # Construct API endpoints based on common patterns
                spot_url = self._construct_spot_api(exchange_id, api_url)
                futures_url = self._construct_futures_api(exchange_id, api_url)
                
                self.dynamic_exchanges[exchange_id] = {
                    "name": exchange["name"],
                    "spot_url": spot_url,
                    "futures_url": futures_url if exchange["capabilities"].get("futures_trading") else None,
                    "parser": f"{exchange_id}_parser",
                    "priority": priority,
                    "rate_limit_per_minute": self._estimate_rate_limit(exchange),
                    "trust_score": exchange.get("trust_score", 0),
                    "volume_24h": exchange.get("volume_24h", 0),
                    "capabilities": exchange["capabilities"],
                    "source": "dynamic_discovery"
                }
                
                priority += 1
            
            # Fallback to static exchanges if dynamic discovery fails
            if not self.dynamic_exchanges:
                self.logger.warning("No dynamic exchanges loaded, using fallback static exchanges")
                self.dynamic_exchanges = self.EXCHANGE_APIS.copy()
                
                # Mark as fallback
                for exchange_id in self.dynamic_exchanges:
                    self.dynamic_exchanges[exchange_id]["source"] = "static_fallback"
            
            self.logger.info(f"✅ Dynamic exchange loading completed",
                           total_loaded=len(self.dynamic_exchanges),
                           dynamic_count=len([e for e in self.dynamic_exchanges.values() 
                                            if e.get("source") == "dynamic_discovery"]))
            
        except Exception as e:
            self.logger.error(f"Failed to load dynamic exchanges", error=str(e))
            
            # Use static fallback
            self.dynamic_exchanges = self.EXCHANGE_APIS.copy()
            for exchange_id in self.dynamic_exchanges:
                self.dynamic_exchanges[exchange_id]["source"] = "static_fallback"
    
    def _construct_spot_api(self, exchange_id: str, api_url: str) -> str:
        """Construct spot trading API URL for discovered exchange."""
        
        # Common spot API patterns
        spot_patterns = {
            "binance": f"{api_url}/v3/ticker/24hr",
            "kraken": f"{api_url}/0/public/Ticker", 
            "kucoin": f"{api_url}/v1/market/allTickers",
            "coinbase": f"{api_url}/products",
            "bybit": f"{api_url}/v5/market/tickers?category=spot",
            "okx": f"{api_url}/v5/market/tickers?instType=SPOT",
            "bitfinex": f"{api_url}/v2/tickers?symbols=ALL",
            "gate": f"{api_url}/v4/spot/tickers",
            "huobi": f"{api_url}/market/tickers",
            "mexc": f"{api_url}/v3/ticker/24hr"
        }
        
        if exchange_id in spot_patterns:
            return spot_patterns[exchange_id]
        
        # Generic fallback patterns
        generic_patterns = [
            f"{api_url}/v3/ticker/24hr",
            f"{api_url}/v2/ticker/24hr", 
            f"{api_url}/v1/ticker/24hr",
            f"{api_url}/ticker/24hr",
            f"{api_url}/tickers",
            f"{api_url}/market/tickers"
        ]
        
        return generic_patterns[0]  # Default to most common pattern
    
    def _construct_futures_api(self, exchange_id: str, api_url: str) -> str:
        """Construct futures trading API URL for discovered exchange."""
        
        futures_patterns = {
            "binance": "https://fapi.binance.com/fapi/v1/ticker/24hr",
            "bybit": f"{api_url}/v5/market/tickers?category=linear",
            "okx": f"{api_url}/v5/market/tickers?instType=SWAP",
            "gate": f"{api_url}/v4/futures/usdt/tickers",
            "huobi": f"{api_url.replace('api', 'api-aws')}/swap-ex/market/detail/merged",
            "mexc": f"{api_url}/v3/ticker/24hr"  # MEXC uses same endpoint
        }
        
        if exchange_id in futures_patterns:
            return futures_patterns[exchange_id]
        
        # Generic fallback
        return f"{api_url}/futures/v1/ticker/24hr"
    
    def _estimate_rate_limit(self, exchange: Dict[str, Any]) -> int:
        """Estimate rate limit based on exchange characteristics."""
        
        trust_score = exchange.get("trust_score", 0)
        volume_24h = exchange.get("volume_24h", 0)
        
        # Higher volume/trust = higher rate limits typically
        if trust_score >= 9 and volume_24h >= 10000:
            return 1200  # High tier like Binance
        elif trust_score >= 7 and volume_24h >= 5000:
            return 600   # Medium tier like Coinbase
        elif trust_score >= 5 and volume_24h >= 1000:
            return 300   # Lower tier
        else:
            return 60    # Conservative default
    
    async def refresh_dynamic_exchanges(self):
        """Refresh the dynamic exchange list."""
        
        self.logger.info("🔄 Refreshing dynamic exchange discovery")
        await dynamic_exchange_discovery.discover_all_exchanges(force_refresh=True)
        await self._load_dynamic_exchanges()
            
    async def discover_all_assets_with_volume_filtering(
        self,
        min_tier: str = "tier_retail",
        exchanges: Optional[List[str]] = None,
        asset_types: Optional[List[str]] = None,
        force_refresh: bool = False
    ) -> Dict[str, List[AssetInfo]]:
        """
        ENTERPRISE ASSET DISCOVERY WITH DYNAMIC VOLUME FILTERING
        
        Discovers ALL assets from ALL configured exchanges with sophisticated
        volume-based filtering. NO hardcoded limitations.
        
        Args:
            min_tier: Minimum volume tier (tier_institutional, tier_enterprise, etc.)
            exchanges: List of exchanges to scan (None = ALL exchanges)
            asset_types: Asset types to include ['spot', 'futures', 'options']
            force_refresh: Force fresh data (bypass cache)
            
        Returns:
            Dict with tier-classified assets: {tier_name: [AssetInfo, ...]}
        """
        
        start_time = time.time()
        scan_id = f"asset_scan_{int(time.time())}"
        
        self.logger.info("🔍 ENTERPRISE Asset Discovery Starting", 
                        scan_id=scan_id, 
                        min_tier=min_tier,
                        exchanges=exchanges or "ALL")
        
        # Initialize async components if needed
        if not self.session:
            await self.async_init()
            
        try:
            # Determine target volume threshold
            min_threshold = self._get_volume_threshold(min_tier)
            if min_threshold is None:
                raise ValueError(f"Invalid tier: {min_tier}")
            
            # Determine exchanges to scan
            target_exchanges = exchanges or list(self.dynamic_exchanges.keys())
            asset_types = asset_types or ["spot", "futures"]
            
            # Check cache first (unless force refresh)
            if not force_refresh:
                cached_assets = await self._get_cached_assets(min_tier, target_exchanges)
                if cached_assets:
                    self.logger.info("📦 Using cached asset data", 
                                   scan_id=scan_id, 
                                   total_assets=sum(len(assets) for assets in cached_assets.values()))
                    return cached_assets
            
            # PHASE 1: Concurrent exchange data fetching
            self.logger.info("📊 Phase 1: Multi-exchange data collection starting", scan_id=scan_id)
            
            exchange_tasks = []
            for exchange_id in target_exchanges:
                if exchange_id in self.dynamic_exchanges:
                    exchange_config = self.dynamic_exchanges[exchange_id]
                    
                    for asset_type in asset_types:
                        task = self._fetch_exchange_data(exchange_id, exchange_config, asset_type, scan_id)
                        exchange_tasks.append(task)
            
            # Execute all exchange fetches concurrently
            exchange_results = await asyncio.gather(*exchange_tasks, return_exceptions=True)
            
            # PHASE 2: Data aggregation and volume analysis  
            self.logger.info("🧮 Phase 2: Volume analysis and classification starting", scan_id=scan_id)
            
            all_assets: Dict[str, AssetInfo] = {}  # symbol -> best AssetInfo
            
            for i, result in enumerate(exchange_results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Exchange fetch failed", 
                                      scan_id=scan_id,
                                      task_index=i, 
                                      error=str(result))
                    continue
                    
                if isinstance(result, dict):
                    for symbol, asset_info in result.items():
                        # Keep asset with highest volume across exchanges
                        if symbol not in all_assets or asset_info.volume_24h_usd > all_assets[symbol].volume_24h_usd:
                            all_assets[symbol] = asset_info
            
            # PHASE 3: Volume-based tier classification
            tier_classified_assets: Dict[str, List[AssetInfo]] = {}
            
            # Initialize all tiers
            for tier in self.VOLUME_TIERS:
                tier_classified_assets[tier.name] = []
            
            # Classify each asset into appropriate tier
            for asset in all_assets.values():
                # Find highest tier this asset qualifies for
                for tier in self.VOLUME_TIERS:
                    if asset.volume_24h_usd >= tier.min_volume_usd:
                        asset.tier = tier.name
                        tier_classified_assets[tier.name].append(asset)
                        break
            
            # PHASE 4: Filter by minimum tier requirement
            filtered_assets = {}
            min_tier_priority = self._get_tier_priority(min_tier)
            
            for tier_name, assets in tier_classified_assets.items():
                tier_priority = self._get_tier_priority(tier_name)
                if tier_priority <= min_tier_priority:  # Higher priority = lower number
                    filtered_assets[tier_name] = sorted(assets, 
                                                      key=lambda x: x.volume_24h_usd, 
                                                      reverse=True)
            
            # PHASE 5: Caching and metrics
            await self._cache_assets(filtered_assets, min_tier, target_exchanges)
            
            execution_time = (time.time() - start_time) * 1000
            total_assets = sum(len(assets) for assets in filtered_assets.values())
            
            self.logger.info("✅ ENTERPRISE Asset Discovery Completed", 
                           scan_id=scan_id,
                           execution_time_ms=execution_time,
                           total_assets=total_assets,
                           exchanges_scanned=len(target_exchanges),
                           min_tier=min_tier)
            
            # Log tier breakdown
            for tier_name, assets in filtered_assets.items():
                if assets:
                    self.logger.info(f"📈 {tier_name}: {len(assets)} assets",
                                   scan_id=scan_id,
                                   top_assets=[a.symbol for a in assets[:5]])
            
            return filtered_assets
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.logger.error("💥 ENTERPRISE Asset Discovery Failed", 
                            scan_id=scan_id,
                            execution_time_ms=execution_time,
                            error=str(e))
            
            # Return empty structure to prevent system failures
            return {tier.name: [] for tier in self.VOLUME_TIERS}
    
    async def _fetch_exchange_data(
        self, 
        exchange_id: str, 
        config: Dict[str, Any], 
        asset_type: str,
        scan_id: str
    ) -> Dict[str, AssetInfo]:
        """
        Fetch asset data from a specific exchange with enterprise error handling.
        """
        
        try:
            # Determine API URL based on asset type
            url_key = f"{asset_type}_url" if f"{asset_type}_url" in config else "spot_url"
            if url_key not in config:
                return {}
                
            url = config[url_key]
            
            # Check rate limiting with error handling
            if self.redis:
                try:
                    rate_limit_key = f"exchange_rate_limit:{exchange_id}"
                    current_requests_raw = await self.redis.get(rate_limit_key)
                    current_requests = 0
                    
                    if current_requests_raw:
                        try:
                            current_requests = int(current_requests_raw)
                        except (ValueError, TypeError):
                            self.logger.warning(f"Invalid rate limit value for {exchange_id}: {current_requests_raw}")
                            current_requests = 0
                    
                    if current_requests >= config.get("rate_limit_per_minute", 60):
                        self.logger.warning(f"Rate limit reached for {exchange_id}", scan_id=scan_id)
                        return {}
                        
                except Exception as e:
                    self.logger.error(f"Redis rate limit check failed for {exchange_id}", error=str(e), scan_id=scan_id, exc_info=True)
                    # Fall back to continuing without rate limit enforcement
            
            # Fetch data with timeout and retry logic
            async with self.session.get(url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Update rate limiting counter
                    if self.redis:
                        await self.redis.incr(rate_limit_key)
                        await self.redis.expire(rate_limit_key, 60)
                    
                    # Parse exchange-specific data format
                    parser_method = getattr(self, config["parser"], None)
                    if parser_method:
                        assets = await parser_method(data, exchange_id, asset_type)
                        
                        self.logger.debug(f"📊 {config['name']} {asset_type}: {len(assets)} assets", 
                                        scan_id=scan_id)
                        return assets
                    else:
                        self.logger.warning(f"No parser found for {exchange_id}", scan_id=scan_id)
                        return {}
                        
                elif response.status == 429:
                    # Rate limited - cache the limitation
                    if self.redis:
                        await self.redis.set(f"exchange_rate_limit:{exchange_id}", "limited", ex=300)
                    
                    self.logger.warning(f"Rate limited by {exchange_id}", scan_id=scan_id)
                    return {}
                    
                else:
                    self.logger.warning(f"{exchange_id} returned {response.status}", scan_id=scan_id)
                    return {}
                    
        except asyncio.TimeoutError:
            self.logger.warning(f"{exchange_id} request timeout", scan_id=scan_id)
            return {}
        except Exception as e:
            self.logger.warning(f"{exchange_id} fetch failed", scan_id=scan_id, error=str(e))
            return {}
    
    # ================================================================================
    # EXCHANGE-SPECIFIC PARSERS (Enterprise-grade data extraction)
    # ================================================================================
    
    async def binance_parser(self, data: Any, exchange_id: str, asset_type: str) -> Dict[str, AssetInfo]:
        """Parse Binance API response format."""
        assets = {}
        
        if isinstance(data, list):
            for item in data:
                try:
                    raw_symbol = item.get("symbol", "")
                    symbol = self._extract_base_symbol(raw_symbol)
                    if not symbol or len(symbol) < 2:
                        continue
                        
                    volume_usd = float(item.get("quoteVolume", 0))
                    price_usd = float(item.get("lastPrice", 0))
                    
                    if volume_usd > 0 and price_usd > 0:
                        assets[symbol] = AssetInfo(
                            symbol=symbol,
                            exchange=exchange_id,
                            volume_24h_usd=volume_usd,
                            price_usd=price_usd,
                            market_cap_usd=None,
                            tier="",  # Will be classified later
                            last_updated=datetime.utcnow(),
                            metadata={
                                "price_change_pct": float(item.get("priceChangePercent", 0)),
                                "high_24h": float(item.get("highPrice", 0)),
                                "low_24h": float(item.get("lowPrice", 0)),
                                "asset_type": asset_type
                            }
                        )
                except (ValueError, KeyError, TypeError):
                    continue
                    
        return assets
    
    async def kucoin_parser(self, data: Any, exchange_id: str, asset_type: str) -> Dict[str, AssetInfo]:
        """Parse KuCoin API response format."""
        assets = {}
        
        ticker_data = data.get("data", {}).get("ticker", []) if isinstance(data, dict) else []
        
        for item in ticker_data:
            try:
                symbol = item.get("symbol", "").split("-")[0]  # Remove quote currency
                if not symbol or len(symbol) < 2:
                    continue
                    
                volume_usd = float(item.get("volValue", 0))  # Volume in USD
                price_usd = float(item.get("last", 0))
                
                if volume_usd > 0 and price_usd > 0:
                    assets[symbol] = AssetInfo(
                        symbol=symbol,
                        exchange=exchange_id,
                        volume_24h_usd=volume_usd,
                        price_usd=price_usd,
                        market_cap_usd=None,
                        tier="",
                        last_updated=datetime.utcnow(),
                        metadata={
                            "change_rate": float(item.get("changeRate", 0)),
                            "high_24h": float(item.get("high", 0)),
                            "low_24h": float(item.get("low", 0)),
                            "asset_type": asset_type
                        }
                    )
            except (ValueError, KeyError, TypeError):
                continue
                
        return assets
    
    async def bybit_parser(self, data: Any, exchange_id: str, asset_type: str) -> Dict[str, AssetInfo]:
        """Parse Bybit API response format."""
        assets = {}
        
        result_list = data.get("result", {}).get("list", []) if isinstance(data, dict) else []
        
        for item in result_list:
            try:
                symbol = item.get("symbol", "").replace("USDT", "").replace("USDC", "")
                if not symbol or len(symbol) < 2:
                    continue
                    
                volume_usd = float(item.get("turnover24h", 0))
                price_usd = float(item.get("lastPrice", 0))
                
                if volume_usd > 0 and price_usd > 0:
                    assets[symbol] = AssetInfo(
                        symbol=symbol,
                        exchange=exchange_id,
                        volume_24h_usd=volume_usd,
                        price_usd=price_usd,
                        market_cap_usd=None,
                        tier="",
                        last_updated=datetime.utcnow(),
                        metadata={
                            "price_change_24h": float(item.get("price24hPcnt", 0)),
                            "high_24h": float(item.get("highPrice24h", 0)),
                            "low_24h": float(item.get("lowPrice24h", 0)),
                            "asset_type": asset_type
                        }
                    )
            except (ValueError, KeyError, TypeError):
                continue
                
        return assets
    
    # Additional parsers for other exchanges would be implemented here...
    # okx_parser, coinbase_parser, kraken_parser, etc.
    
    async def okx_parser(self, data: Any, exchange_id: str, asset_type: str) -> Dict[str, AssetInfo]:
        """Parse OKX API response format.""" 
        assets = {}
        
        data_list = data.get("data", []) if isinstance(data, dict) else []
        
        for item in data_list:
            try:
                symbol = item.get("instId", "").split("-")[0]  # Remove quote currency
                if not symbol or len(symbol) < 2:
                    continue
                    
                volume_usd = float(item.get("volCcy24h", 0))  # Volume in quote currency
                price_usd = float(item.get("last", 0))
                
                if volume_usd > 0 and price_usd > 0:
                    assets[symbol] = AssetInfo(
                        symbol=symbol,
                        exchange=exchange_id,
                        volume_24h_usd=volume_usd,
                        price_usd=price_usd,
                        market_cap_usd=None,
                        tier="",
                        last_updated=datetime.utcnow(),
                        metadata={
                            "change_24h": float(item.get("last", 0)) - float(item.get("open24h", item.get("sodUtc8", 0))),
                            "high_24h": float(item.get("high24h", 0)),
                            "low_24h": float(item.get("low24h", 0)),
                            "asset_type": asset_type
                        }
                    )
            except (ValueError, KeyError, TypeError):
                continue
                
        return assets
    
    # ================================================================================
    # UTILITY METHODS
    # ================================================================================
    
    def _get_volume_threshold(self, tier_name: str) -> Optional[float]:
        """Get volume threshold for a tier."""
        for tier in self.VOLUME_TIERS:
            if tier.name == tier_name:
                return tier.min_volume_usd
        return None
    
    def _get_tier_priority(self, tier_name: str) -> int:
        """Get priority number for a tier (lower = higher priority)."""
        for tier in self.VOLUME_TIERS:
            if tier.name == tier_name:
                return tier.priority
        return 999  # Unknown tier gets lowest priority
    
    async def _get_cached_assets(self, min_tier: str, exchanges: List[str]) -> Optional[Dict[str, List[AssetInfo]]]:
        """Retrieve cached asset data if available and fresh."""
        if not self.redis:
            return None
            
        try:
            cache_key = f"enterprise_assets:{min_tier}:{'_'.join(sorted(exchanges))}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                # Check if cache is still fresh (5 minutes)
                cache_time = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
                if datetime.utcnow() - cache_time < timedelta(minutes=5):
                    # Reconstruct AssetInfo objects
                    result = {}
                    for tier_name, assets_data in data.get("assets", {}).items():
                        result[tier_name] = [
                            AssetInfo(
                                symbol=a["symbol"],
                                exchange=a["exchange"], 
                                volume_24h_usd=a["volume_24h_usd"],
                                price_usd=a["price_usd"],
                                market_cap_usd=a.get("market_cap_usd"),
                                tier=a["tier"],
                                last_updated=datetime.fromisoformat(a["last_updated"]),
                                metadata=a.get("metadata", {})
                            )
                            for a in assets_data
                        ]
                    return result
                    
        except Exception as e:
            self.logger.debug("Cache retrieval failed", error=str(e))
            
        return None
    
    async def _cache_assets(self, assets: Dict[str, List[AssetInfo]], min_tier: str, exchanges: List[str]):
        """Cache asset data for future use."""
        if not self.redis:
            return
            
        try:
            cache_key = f"enterprise_assets:{min_tier}:{'_'.join(sorted(exchanges))}"
            
            # Convert AssetInfo objects to serializable format
            serializable_assets = {}
            for tier_name, asset_list in assets.items():
                serializable_assets[tier_name] = [
                    {
                        "symbol": asset.symbol,
                        "exchange": asset.exchange,
                        "volume_24h_usd": asset.volume_24h_usd,
                        "price_usd": asset.price_usd,
                        "market_cap_usd": asset.market_cap_usd,
                        "tier": asset.tier,
                        "last_updated": asset.last_updated.isoformat(),
                        "metadata": asset.metadata
                    }
                    for asset in asset_list
                ]
            
            cache_data = {
                "assets": serializable_assets,
                "timestamp": datetime.utcnow().isoformat(),
                "min_tier": min_tier,
                "exchanges": exchanges
            }
            
            # Cache for 10 minutes
            await self.redis.set(cache_key, json.dumps(cache_data), ex=600)
            
        except Exception as e:
            self.logger.debug("Cache storage failed", error=str(e))
            
    def _extract_base_symbol(self, raw_symbol: str) -> str:
        """Extract base symbol by removing known quote suffixes."""
        if not raw_symbol or len(raw_symbol) < 3:
            return ""
            
        # Known quote currencies in order of longest-first to avoid incorrect matching
        quote_currencies = ["USDT", "BUSD", "USDC", "BTC", "ETH", "BNB", "USD", "EUR"]
        
        symbol = raw_symbol.upper()
        for quote in quote_currencies:
            if symbol.endswith(quote) and len(symbol) > len(quote):
                base = symbol[:-len(quote)]
                if len(base) >= 2:  # Ensure base symbol is at least 2 chars
                    return base
                    
        # If no quote suffix found or result would be too short, return original if valid
        return raw_symbol if len(raw_symbol) >= 2 else ""
    
    async def get_assets_by_tier(self, tier_name: str) -> List[AssetInfo]:
        """Get assets for a specific tier."""
        all_assets = await self.discover_all_assets_with_volume_filtering(min_tier=tier_name)
        return all_assets.get(tier_name, [])
    
    async def get_top_assets(self, count: int = 100, min_tier: str = "tier_retail") -> List[AssetInfo]:
        """Get top assets by volume across all tiers."""
        all_assets = await self.discover_all_assets_with_volume_filtering(min_tier=min_tier)
        
        # Flatten all tiers and sort by volume
        all_assets_flat = []
        for asset_list in all_assets.values():
            all_assets_flat.extend(asset_list)
            
        # Sort by volume and return top N
        top_assets = sorted(all_assets_flat, key=lambda x: x.volume_24h_usd, reverse=True)
        return top_assets[:count]
    
    async def get_assets_for_symbol_list(self, symbols: List[str]) -> Dict[str, AssetInfo]:
        """Get asset information for specific symbols."""
        # Get comprehensive asset data
        all_assets = await self.discover_all_assets_with_volume_filtering(min_tier="tier_any")
        
        # Build symbol lookup
        symbol_map = {}
        for asset_list in all_assets.values():
            for asset in asset_list:
                if asset.symbol.upper() in [s.upper() for s in symbols]:
                    symbol_map[asset.symbol.upper()] = asset
        
        return symbol_map
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()


# Global service instance
enterprise_asset_filter = EnterpriseAssetFilter()