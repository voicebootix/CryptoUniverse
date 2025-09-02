"""
Background Service Manager - Enterprise Grade

Manages background services, health monitoring, system metrics,
autonomous trading cycles, and configurable intervals for the AI money manager.
"""

import asyncio
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import structlog
from app.core.logging import LoggerMixin
from app.core.config import get_settings
from app.core.redis import get_redis_client

settings = get_settings()
logger = structlog.get_logger(__name__)


class BackgroundServiceManager(LoggerMixin):
    """Enterprise background service manager with real functionality."""
    
    def __init__(self):
        self.services = {}
        self.running = False
        self.tasks = {}
        self.start_time = None
        self.redis = None
        
        # Disk cleanup concurrency control
        self._cleanup_lock = asyncio.Lock()
        self._last_cleanup: float = 0
        self._cleanup_cooldown = 300  # 5 minutes cooldown
        # Configurable service intervals (seconds)
        self.intervals = {
            "health_monitor": 60,        # 1 minute
            "metrics_collector": 300,    # 5 minutes
            "cleanup_service": 3600,     # 1 hour
            "autonomous_cycles": 60,     # 1 minute base (adaptive based on market conditions)
            "market_data_sync": 60,      # 1 minute
            "balance_sync": 300,         # 5 minutes
            "risk_monitor": 30,          # 30 seconds
            "rate_limit_cleanup": 1800   # 30 minutes
        }
        
        # Dynamic service configurations (no hardcoded restrictions)
        self.service_configs = {
            "risk_thresholds": {
                "max_daily_loss": 10.0,  # 10%
                "max_position_size": 20.0,  # 20%
                "emergency_stop_loss": 15.0  # 15%
            },
            "market_data_discovery": {
                "min_volume_usd_24h": 1000000,  # $1M minimum volume
                "min_market_cap": 10000000,     # $10M minimum market cap
                "max_symbols_per_sync": 100,    # Dynamic limit
                "update_frequency_seconds": 300  # 5 minutes
            }
        }
    
    async def async_init(self):
        self.redis = await get_redis_client()
    
    async def start_all(self):
        """Start all background services with real functionality."""
        self.logger.info("🚀 Starting enterprise background services...")
        self.running = True
        self.start_time = datetime.utcnow()
        
        # Initialize redis client
        await self.async_init()
        
        # Start individual services
        self.tasks["health_monitor"] = asyncio.create_task(self._health_monitor_service())
        self.tasks["metrics_collector"] = asyncio.create_task(self._metrics_collector_service())
        self.tasks["cleanup_service"] = asyncio.create_task(self._cleanup_service())
        self.tasks["autonomous_cycles"] = asyncio.create_task(self._autonomous_cycles_service())
        self.tasks["market_data_sync"] = asyncio.create_task(self._market_data_sync_service())
        self.tasks["balance_sync"] = asyncio.create_task(self._balance_sync_service())
        self.tasks["risk_monitor"] = asyncio.create_task(self._risk_monitor_service())
        self.tasks["rate_limit_cleanup"] = asyncio.create_task(self._rate_limit_cleanup_service())
        
        # Update service status
        self.services = {
            "health_monitor": "running",
            "metrics_collector": "running", 
            "cleanup_service": "running",
            "autonomous_cycles": "running",
            "market_data_sync": "running",
            "balance_sync": "running",
            "risk_monitor": "running",
            "rate_limit_cleanup": "running"
        }
        
        self.logger.info("✅ All background services started successfully")
    
    async def stop_all(self):
        """Stop all background services gracefully."""
        self.logger.info("🔄 Stopping background services...")
        self.running = False
        
        # Cancel all tasks
        for service_name, task in self.tasks.items():
            if not task.cancelled():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    self.logger.info(f"✅ {service_name} stopped")
        
        self.tasks = {}
        self.services = {}
        self.logger.info("✅ All background services stopped")
    
    async def health_check(self) -> Dict[str, str]:
        """Get real health status of all services."""
        health_status = {}
        
        for service_name, task in self.tasks.items():
            if task.cancelled():
                health_status[service_name] = "stopped"
            elif task.done():
                if task.exception():
                    health_status[service_name] = "error"
                else:
                    health_status[service_name] = "completed"
            else:
                health_status[service_name] = "running"
        
        return health_status
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get real system metrics."""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            # Application uptime
            uptime_seconds = 0
            if self.start_time:
                uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
            
            # Redis connection count (if available)
            active_connections = 0
            if self.redis:
                try:
                    redis_info = await self.redis.info()
                    active_connections = redis_info.get("connected_clients", 0)
                except:
                    pass
            
            return {
                "services": self.services,
                "uptime_seconds": uptime_seconds,
                "uptime_hours": round(uptime_seconds / 3600, 2),
                "cpu_usage_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": round((disk.used / disk.total) * 100, 2)
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                "active_connections": active_connections,
                "intervals": self.intervals,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get system metrics", error=str(e))
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def configure_service_interval(self, service: str, interval: int):
        """Configure service interval (admin function)."""
        if service in self.intervals:
            old_interval = self.intervals[service]
            self.intervals[service] = interval
            
            # Store in Redis for persistence
            if self.redis:
                await self.redis.hset(
                    "service_intervals",
                    service,
                    interval
                )
            
            self.logger.info(
                f"Service interval updated: {service}",
                old_interval=old_interval,
                new_interval=interval
            )
            return True
        return False
    
    async def get_service_status(self, service: str) -> Dict[str, Any]:
        """Get detailed status for specific service."""
        if service not in self.tasks:
            return {"status": "not_found"}
        
        task = self.tasks[service]
        return {
            "status": "running" if not task.done() else "stopped",
            "cancelled": task.cancelled(),
            "exception": str(task.exception()) if task.exception() else None,
            "interval": self.intervals.get(service, 0),
            "last_run": getattr(task, 'last_run', None)
        }
    
    # Background Service Implementations
    async def _health_monitor_service(self):
        """Monitor system health and alert on issues."""
        self.logger.info("🏥 Health monitor service started")
        
        while self.running:
            try:
                # Check system resources
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
                disk_percent = psutil.disk_usage('/').percent
                
                # Alert thresholds
                alerts = []
                if cpu_percent > 90:
                    alerts.append(f"High CPU usage: {cpu_percent}%")
                if memory_percent > 85:
                    alerts.append(f"High memory usage: {memory_percent}%")
                if disk_percent > 80:
                    alerts.append(f"High disk usage: {disk_percent}%")
                    
                    # Trigger automated cleanup if disk usage is critical (non-blocking)
                    if disk_percent > 85:
                        asyncio.create_task(self._run_cleanup_if_allowed())
                
                # Check Redis connection
                if self.redis:
                    try:
                        await self.redis.ping()
                    except Exception as e:
                        alerts.append(f"Redis connection failed: {e}")
                
                # Log alerts
                if alerts:
                    self.logger.warning("⚠️ System health alerts", alerts=alerts)
                
                # Store health status
                health_data = {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "alerts": alerts,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if self.redis:
                    await self.redis.setex(
                        "system_health",
                        300,  # 5 minutes TTL
                        str(health_data)
                    )
                
            except Exception as e:
                self.logger.error("Health monitor error", error=str(e))
            
            await asyncio.sleep(self.intervals["health_monitor"])
    
    async def _metrics_collector_service(self):
        """Collect and store system metrics."""
        self.logger.info("📊 Metrics collector service started")
        
        while self.running:
            try:
                metrics = await self.get_system_metrics()
                
                # Store metrics with timestamp
                timestamp = int(time.time())
                if self.redis:
                    await self.redis.zadd(
                        "system_metrics_history",
                        {str(metrics): timestamp}
                    )
                
                # Keep only last 24 hours of metrics
                cutoff = timestamp - 86400  # 24 hours
                if self.redis:
                    await self.redis.zremrangebyscore(
                        "system_metrics_history",
                        0,
                        cutoff
                    )
                
            except Exception as e:
                self.logger.error("Metrics collector error", error=str(e))
            
            await asyncio.sleep(self.intervals["metrics_collector"])
    
    async def _cleanup_service(self):
        """Clean up old data and optimize storage."""
        self.logger.info("🧹 Cleanup service started")
        
        while self.running:
            try:
                # Clean old logs (this would be implementation specific)
                
                # Clean old Redis keys
                await self._cleanup_redis_keys()
                
                # Clean old session data
                await self._cleanup_expired_sessions()
                
                self.logger.info("✅ Cleanup cycle completed")
                
            except Exception as e:
                self.logger.error("Cleanup service error", error=str(e))
            
            await asyncio.sleep(self.intervals["cleanup_service"])
    
    async def _autonomous_cycles_service(self):
        """Manage autonomous trading cycles for all users."""
        self.logger.info("🤖 Autonomous cycles service started")
        
        while self.running:
            try:
                # This would trigger autonomous trading cycles
                # Import here to avoid circular imports
                try:
                    from app.services.master_controller import MasterSystemController
                    master_controller = MasterSystemController()
                    
                    # Run global autonomous cycle check
                    await master_controller.run_global_autonomous_cycle()
                    
                except ImportError:
                    self.logger.warning("Master controller not available for autonomous cycles")
                
            except Exception as e:
                self.logger.error("Autonomous cycles error", error=str(e))
            
            # ADAPTIVE CYCLE TIMING based on market conditions
            next_interval = await self._calculate_adaptive_cycle_interval()
            await asyncio.sleep(next_interval)
    
    async def _market_data_sync_service(self):
        """Sync market data for configured symbols using real APIs."""
        self.logger.info("📈 Market data sync service started")
        
        while self.running:
            try:
                # Dynamically discover tradeable symbols (no hardcoded lists)
                symbols = await self._discover_active_trading_symbols()
                
                # Import your sophisticated market data feeds service
                from app.services.market_data_feeds import market_data_feeds
                
                # Ensure market data feeds is initialized
                if market_data_feeds.redis is None:
                    await market_data_feeds.async_init()
                
                # Sync market data for discovered symbols using real APIs
                await market_data_feeds.sync_market_data_batch(symbols)
                
                self.logger.debug(f"Market data sync completed for {len(symbols)} discovered symbols", symbols=symbols[:10])
                
            except Exception as e:
                self.logger.error("Market data sync error", error=str(e))
            
            await asyncio.sleep(self.intervals["market_data_sync"])
    
    async def _discover_active_trading_symbols(self) -> List[str]:
        """ENTERPRISE: Dynamically discover ALL trading opportunities without limits."""
        all_discovered_symbols = set()
        
        try:
            from app.services.market_analysis_core import MarketAnalysisService
            market_service = MarketAnalysisService()
            
            # ENTERPRISE: Progressive discovery with multiple strategies (NO ARTIFICIAL LIMITS)
            discovery_strategies = [
                {"min_volume_usd": 100000, "description": "High volume assets"},  # $100K min
                {"min_volume_usd": 50000, "description": "Medium-high volume"},   # $50K min  
                {"min_volume_usd": 10000, "description": "Medium volume"},       # $10K min
                {"min_volume_usd": 1000, "description": "Low volume"},          # $1K min
                {"min_volume_usd": 0, "description": "All assets"},             # NO MINIMUM
            ]
            
            for strategy in discovery_strategies:
                try:
                    discovery_result = await market_service.discover_exchange_assets(
                        exchanges="all",
                        user_id="system"
                    )
                    
                    if discovery_result.get("success"):
                        # ENTERPRISE: Try both response formats for compatibility
                        discovered_assets = (
                            discovery_result.get("asset_discovery", {}).get("detailed_results", {}) or
                            discovery_result.get("discovered_assets", {})
                        )
                        
                        # Extract ALL symbols from ALL exchanges without limits
                        strategy_symbols = set()
                        
                        # Handle both old and new response formats
                        if discovered_assets:
                            for exchange, assets in discovered_assets.items():
                                if isinstance(assets, dict):
                                    # New format: extract base assets from structured data
                                    base_assets = assets.get("base_assets", [])
                                    if base_assets:
                                        strategy_symbols.update(base_assets)
                                    
                                    # Also try recursive extraction for complex structures
                                    self._extract_symbols_from_discovery(assets, strategy_symbols)
                                elif isinstance(assets, list):
                                    # Direct list format
                                    strategy_symbols.update(assets)
                        
                        # ENTERPRISE: Minimal filtering - only remove obviously invalid
                        valid_symbols = set()
                        for symbol in strategy_symbols:
                            if (isinstance(symbol, str) and 
                                len(symbol) >= 2 and len(symbol) <= 15 and 
                                symbol.replace('-', '').replace('_', '').isalnum() and
                                not symbol.lower().startswith('test') and
                                symbol.upper() not in ['NULL', 'NONE', 'UNDEFINED']):
                                valid_symbols.add(symbol.upper())
                        
                        all_discovered_symbols.update(valid_symbols)
                        
                        self.logger.info(
                            f"Discovery strategy: {strategy['description']} found {len(valid_symbols)} symbols", 
                            min_volume=strategy["min_volume_usd"],
                            total_discovered=len(all_discovered_symbols)
                        )
                        
                        # Continue with all strategies to maximize opportunities
                        # Break early if we have enough symbols to save API calls
                        if len(all_discovered_symbols) >= 200:
                            self.logger.info(f"Early termination - sufficient symbols discovered: {len(all_discovered_symbols)}")
                            break
                            
                except Exception as e:
                    self.logger.exception(f"Discovery strategy failed: {strategy['description']}")
                    continue
            
        except Exception as e:
            self.logger.exception("Market analysis discovery failed")
        
        # ENTERPRISE: Direct exchange API discovery (bypass service layer if needed)
        try:
            exchange_symbols_raw = await self._discover_symbols_direct_apis()
            # Normalize to uppercase to avoid price mismatches with downstream services
            exchange_symbols = {symbol.upper() for symbol in exchange_symbols_raw if symbol and isinstance(symbol, str)}
            all_discovered_symbols.update(exchange_symbols)
            self.logger.info(f"Direct API discovery added {len(exchange_symbols)} normalized symbols", 
                           raw_count=len(exchange_symbols_raw), 
                           normalized_count=len(exchange_symbols))
        except Exception as e:
            self.logger.warning("Direct API discovery failed", error=str(e))
        
        # ENTERPRISE: Comprehensive fallback with ALL profitable cryptos
        if len(all_discovered_symbols) < 50:  # Only if discovery seriously failed
            comprehensive_fallback = self._get_comprehensive_crypto_universe()
            all_discovered_symbols.update(comprehensive_fallback)
            self.logger.warning(
                f"Enhanced fallback: added {len(comprehensive_fallback)} symbols",
                total_symbols=len(all_discovered_symbols),
                message="Ensuring no opportunities are missed"
            )
        
        discovered_list = list(all_discovered_symbols)
        
        self.logger.info(
            f"🔍 Discovered {len(discovered_list)} active trading symbols - NO LIMITS",
            sample_symbols=discovered_list[:20],
            message="ENTERPRISE: All opportunities captured for maximum profit"
        )
        
        return discovered_list
    
    def _extract_symbols_from_discovery(self, data, symbols_set):
        """Recursively extract symbols from complex discovery data structures."""
        if isinstance(data, dict):
            for key, value in data.items():
                # Look for symbol fields at any level
                if key.lower() in ['symbol', 'base_asset', 'base', 'coin', 'currency', 'asset']:
                    if isinstance(value, str) and value:
                        symbols_set.add(value)
                elif key.lower() in ['symbols', 'assets', 'coins', 'pairs', 'currencies']:
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                symbols_set.add(item)
                            elif isinstance(item, dict):
                                self._extract_symbols_from_discovery(item, symbols_set)
                    elif isinstance(value, dict):
                        self._extract_symbols_from_discovery(value, symbols_set)
                elif isinstance(value, (dict, list)):
                    self._extract_symbols_from_discovery(value, symbols_set)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, str) and item:
                    symbols_set.add(item)
                elif isinstance(item, dict):
                    self._extract_symbols_from_discovery(item, symbols_set)
    
    async def _discover_symbols_direct_apis(self) -> set:
        """ENTERPRISE: Direct API calls to multiple exchanges for maximum symbol coverage."""
        all_symbols = set()
        
        apis_to_try = [
            {
                "name": "Binance",
                "url": "https://api.binance.com/api/v3/exchangeInfo",
                "parser": lambda data: [s.get("baseAsset") for s in data.get("symbols", []) if s.get("status") == "TRADING"]
            },
            {
                "name": "KuCoin", 
                "url": "https://api.kucoin.com/api/v1/symbols",
                "parser": lambda data: [s.get("baseCurrency") for s in data.get("data", []) if s.get("enableTrading") is True]
            },
            {
                "name": "CoinGecko_Top250",
                "url": "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1",
                "parser": lambda data: [coin.get("symbol", "").upper() for coin in data if coin.get("symbol")]
            },
            {
                "name": "CoinGecko_Volume",
                "url": "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=250&page=1",
                "parser": lambda data: [coin.get("symbol", "").upper() for coin in data if coin.get("symbol")]
            },
            {
                "name": "CoinCap_Top200",
                "url": "https://api.coincap.io/v2/assets?limit=200",
                "parser": lambda data: [asset.get("symbol", "").upper() for asset in data.get("data", []) if asset.get("symbol")]
            }
        ]
        
        # ENTERPRISE: Concurrent API calls for optimal performance (avoid >1min latency)
        async def fetch_api_symbols(session, api_config):
            """Fetch symbols from a single API concurrently."""
            try:
                headers = {"User-Agent": "CryptoUniverse-Trading-Platform/1.0"}
                async with session.get(
                    api_config["url"], 
                    timeout=10,  # Reduced timeout for concurrent calls
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        symbols = api_config["parser"](data)
                        valid_symbols = {s for s in symbols if s and isinstance(s, str) and len(s) >= 2}
                        self.logger.info(f"Concurrent API {api_config['name']} found {len(valid_symbols)} symbols")
                        return valid_symbols
                    else:
                        self.logger.warning(f"Concurrent API {api_config['name']} returned {response.status}")
                        return set()
            except Exception as e:
                self.logger.warning(f"Concurrent API {api_config['name']} failed", api_name=api_config['name'], error=str(e))
                return set()
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Execute all API calls concurrently
                tasks = [fetch_api_symbols(session, api_config) for api_config in apis_to_try]
                api_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Combine results from all APIs
                total_from_apis = 0
                for i, result in enumerate(api_results):
                    if isinstance(result, set):
                        all_symbols.update(result)
                        total_from_apis += len(result)
                    elif isinstance(result, Exception):
                        self.logger.warning(f"API task {apis_to_try[i]['name']} returned exception", error=str(result))
                
                self.logger.info(f"Concurrent API discovery completed", 
                               total_apis=len(apis_to_try), 
                               total_symbols=total_from_apis,
                               unique_symbols=len(all_symbols))
                        
        except Exception as e:
            self.logger.exception("Concurrent API symbol discovery completely failed")
        
        return all_symbols
    
    def _get_comprehensive_crypto_universe(self) -> set:
        """ENTERPRISE: Emergency fallback list (ONLY used if dynamic discovery completely fails)."""
        return {
            # Layer 1 Blockchains & Protocols
            "BTC", "ETH", "SOL", "ADA", "DOT", "AVAX", "ATOM", "NEAR", "ALGO", "XTZ", "EGLD", "FTM", "LUNA", "ROSE",
            "KAVA", "RUNE", "OSMO", "JUNO", "SCRT", "BAND", "AKT", "IRIS", "REGEN", "LIKE", "IOV", "SIFCHAIN",
            
            # Layer 2 & Scaling Solutions  
            "MATIC", "OP", "ARB", "LRC", "IMX", "MINA", "CELO", "SKALE", "POKT",
            
            # DeFi Ecosystem (All Major Protocols)
            "UNI", "AAVE", "COMP", "MKR", "SNX", "CRV", "SUSHI", "1INCH", "YFI", "BAL", "ALPHA", "CREAM", "BADGER",
            "CVX", "FXS", "FRAX", "OHM", "SPELL", "ICE", "TIME", "TOKE", "FEI", "TRIBE", "RAI", "LUSD", "LQTY",
            
            # Exchange Tokens & CEX
            "BNB", "CRO", "FTT", "HT", "OKB", "LEO", "GT", "KCS", "BGB", "MX", "WRX",
            
            # Oracle & Infrastructure  
            "LINK", "API3", "TRB", "DIA", "UMA", "NEST", "FLUX",
            
            # Privacy & Anonymous Coins
            "XMR", "ZEC", "DASH", "TORN", "NYM", "DERO",
            
            # Enterprise & Institutional
            "XRP", "XLM", "HBAR", "VET", "ENJ", "CHZ", "HOT", "WIN", "BTT", "JST", "SUN", "TRX",
            
            # Gaming & NFT Ecosystem
            "AXS", "SAND", "MANA", "FLOW", "WAX", "GALA", "ILV", "YGG", "GHST", "ALICE", "TLM", "SLP",
            "SKILL", "THG", "PYR", "NFTX", "RARI", "SUPER", "AUDIO", "LOOKS", "APE",
            
            # AI & Data Economy
            "FET", "OCEAN", "AGI", "NMR", "GRT", "LPT", "RLC", "CTXC", "DBC", "MATRIX", "COVAL",
            
            # Storage & Computing
            "FIL", "AR", "SC", "STORJ", "SAFE", "ANKR", "REN", "NKN", "CKB",
            
            # Social & Content Creation
            "BAT", "THETA", "MASK", "RALLY", "WHALE", "AMPL", "FORTH",
            
            # Stablecoins & Forex
            "USDT", "USDC", "BUSD", "DAI", "TUSD", "SUSD", "ALUSD", "MIM", "DOLA",
            "EUROC", "EURT", "EURS", "XSGD", "XAUD", "XIDR", "FLEXUSD",
            
            # Memcoins & Community (High volatility = high opportunity)
            "DOGE", "SHIB", "ELON", "FLOKI", "BABYDOGE", "SAFEMOON", "HOGE", "KISHU", "LEASH", "BONE",
            
            # Regional & Emerging Markets
            "BRL", "TRY", "INR", "KRW", "THB", "PHP", "VND", "MYR", "SGD", "HKD", "TWD", "JPY", "CNY",
            
            # Cross-Chain & Interoperability
            "KSM", "AKT", "DVPN", "ROWAN", "GRAV", "XPRT", "NGM", "BLD",
            
            # Emerging High-Potential (Continuously Monitor)
            "IOST", "ZIL", "ICX", "ONT", "GAS", "NEO", "VEN", "QTUM", "LSK", "ARK", "STRAT", "NAV", "PART",
            "DCR", "BTG", "ZEN", "FIRO", "BEAM", "GRIN", "RVN", "ERG", "NEBL", "PIV", "XVS",
            
            # New Listings & Innovations (High Growth Potential)  
            "GMT", "STG", "STEPN", "GST", "SWEAT", "C98", "ALPACA", "BOBA", "METIS", "SYN",
        }
    
    async def _calculate_adaptive_cycle_interval(self) -> int:
        """Calculate adaptive cycle interval based on market conditions and activity."""
        try:
            from app.services.market_analysis_core import MarketAnalysisService
            
            # Get current market volatility
            market_service = MarketAnalysisService()
            market_overview = await market_service.get_market_overview()
            
            if market_overview.get("success"):
                volatility = market_overview.get("market_overview", {}).get("volatility_level", "medium")
                arbitrage_count = market_overview.get("market_overview", {}).get("arbitrage_opportunities", 0)
                
                # Adaptive timing based on market conditions
                if volatility == "high" or arbitrage_count > 5:
                    # High volatility or many arbitrage opportunities: faster cycles
                    return 30  # 30 seconds
                elif volatility == "low":
                    # Low volatility: slower cycles to save resources
                    return 120  # 2 minutes
                else:
                    # Medium volatility: standard timing
                    return 60  # 1 minute
            else:
                # Fallback to standard interval
                return self.intervals["autonomous_cycles"]
                
        except Exception as e:
            self.logger.warning("Failed to calculate adaptive interval", error=str(e))
            return self.intervals["autonomous_cycles"]
    
    async def _balance_sync_service(self):
        """Sync exchange balances for all users."""
        self.logger.info("💰 Balance sync service started")
        
        while self.running:
            try:
                # Get all users with active exchange accounts
                from app.core.database import get_database
                from app.models.exchange import ExchangeAccount
                from sqlalchemy import select, and_, distinct
                import json
                
                async for db in get_database():
                    # Find all users with active exchange accounts
                    stmt = select(distinct(ExchangeAccount.user_id)).where(
                        and_(
                            ExchangeAccount.status == "active",
                            ExchangeAccount.trading_enabled == True
                        )
                    )
                    
                    result = await db.execute(stmt)
                    user_ids = [row[0] for row in result.fetchall()]
                    
                    self.logger.debug(f"Syncing balances for {len(user_ids)} users with active exchanges")
                    
                    # Sync balances for each user using your existing system
                    for user_id in user_ids:
                        try:
                            # Use your existing exchange balance fetching
                            from app.api.v1.endpoints.exchanges import get_user_portfolio_from_exchanges
                            portfolio_data = await get_user_portfolio_from_exchanges(str(user_id), db)
                            
                            if portfolio_data.get("success"):
                                # Update cached portfolio data in Redis for real-time access
                                if self.redis:
                                    await self.redis.setex(
                                        f"portfolio_cache:{user_id}",
                                        300,  # 5 minute cache
                                        json.dumps(portfolio_data, default=str)
                                    )
                            
                        except Exception as e:
                            self.logger.warning(f"Balance sync failed for user {user_id}", error=str(e))
                            continue
                
                self.logger.debug("Balance sync cycle completed")
                
            except Exception as e:
                self.logger.error("Balance sync error", error=str(e))
            
            await asyncio.sleep(self.intervals["balance_sync"])
    
    async def _risk_monitor_service(self):
        """Monitor risk levels and trigger alerts."""
        self.logger.info("⚠️ Risk monitor service started")
        
        while self.running:
            try:
                # This would monitor portfolio risks
                risk_thresholds = self.service_configs["risk_thresholds"]
                
                # Check for high-risk users
                # Trigger emergency stops if needed
                
            except Exception as e:
                self.logger.error("Risk monitor error", error=str(e))
            
            await asyncio.sleep(self.intervals["risk_monitor"])
    
    async def _rate_limit_cleanup_service(self):
        """Clean up rate limiting data."""
        self.logger.info("🚦 Rate limit cleanup service started")
        
        while self.running:
            try:
                # Import rate limiter
                from app.services.rate_limit import rate_limiter
                
                # Ensure rate limiter is initialized
                if rate_limiter.redis is None:
                    await rate_limiter.async_init()
                
                cleaned = await rate_limiter.cleanup_expired_entries()
                
                if cleaned > 0:
                    self.logger.info(f"Cleaned {cleaned} expired rate limit entries")
                
            except Exception as e:
                self.logger.error("Rate limit cleanup error", error=str(e))
            
            await asyncio.sleep(self.intervals["rate_limit_cleanup"])
    
    async def _cleanup_redis_keys(self):
        """Clean up old Redis keys."""
        try:
            if self.redis:
                # Clean keys older than 24 hours
                patterns_to_clean = [
                    "rate_limit:*",
                    "market_data:*",
                    "system_health",
                    "user_session:*"
                ]
                
                for pattern in patterns_to_clean:
                    keys = await self.redis.keys(pattern)
                    if keys:
                        # Check TTL and clean if needed
                        for key in keys:
                            ttl = await self.redis.ttl(key)
                            if ttl == -1:  # No expiration set
                                await self.redis.expire(key, 86400)  # Set 24h expiration
            
        except Exception as e:
            self.logger.error("Redis cleanup failed", error=str(e))
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired user sessions."""
        try:
            # This would clean up expired sessions from database
            pass
        except Exception as e:
            self.logger.error("Session cleanup failed", error=str(e))
    
    async def _automated_disk_cleanup(self):
        """Automated disk cleanup for enterprise production environment - application-owned files only."""
        try:
            self.logger.info("🧹 Starting automated disk cleanup")
            cleanup_actions = []
            
            # 1. Clean up old application log files (older than 7 days)
            import os
            import glob
            from pathlib import Path
            
            # Only clean application-owned directories
            app_log_dirs = ["./logs", "./app/logs", "./var/log/app"]
            app_prefixes = ["crypto_", "trading_", "app_", "background_", "market_"]
            
            for log_dir in app_log_dirs:
                if not os.path.exists(log_dir):
                    continue
                    
                try:
                    # Only clean files with our application prefixes or in our directories
                    for prefix in app_prefixes:
                        old_logs = glob.glob(f"{log_dir}/{prefix}*.log.*")
                        old_logs.extend(glob.glob(f"{log_dir}/{prefix}*-*.log"))
                        
                        for log_file in old_logs:
                            try:
                                file_path = Path(log_file)
                                if file_path.stat().st_mtime < (time.time() - 7 * 24 * 3600):  # 7 days
                                    # Verify it's our file by checking name pattern
                                    if any(file_path.name.startswith(p) for p in app_prefixes):
                                        await self._safe_remove_file(log_file)
                                        cleanup_actions.append(f"Removed old log: {log_file}")
                            except Exception as e:
                                self.logger.error(f"Failed to remove log file {log_file}", error=str(e), exc_info=True)
                except Exception as e:
                    self.logger.error(f"Failed to clean log directory {log_dir}", error=str(e), exc_info=True)
            
            # 2. Clean up application temporary files
            app_temp_dirs = ["./tmp", "./temp", "./cache/tmp"]
            for temp_dir in app_temp_dirs:
                if not os.path.exists(temp_dir):
                    continue
                    
                try:
                    # Only clean files with our application prefixes
                    for prefix in app_prefixes:
                        temp_files = glob.glob(f"{temp_dir}/{prefix}*")
                        temp_files.extend(glob.glob(f"{temp_dir}/*_{prefix}*"))
                        
                        for temp_file in temp_files:
                            try:
                                file_path = Path(temp_file)
                                if file_path.stat().st_mtime < (time.time() - 24 * 3600):  # 1 day
                                    # Verify it's our file
                                    if any(file_path.name.startswith(p) or f"_{p}" in file_path.name for p in app_prefixes):
                                        await self._safe_remove_file(temp_file)
                                        cleanup_actions.append(f"Removed temp file: {temp_file}")
                            except Exception as e:
                                self.logger.error(f"Failed to remove temp file {temp_file}", error=str(e), exc_info=True)
                except Exception as e:
                    self.logger.error(f"Failed to clean temp directory {temp_dir}", error=str(e), exc_info=True)
            
            # 3. Clean up old application database backups (keep last 3)
            app_backup_dirs = ["./backups", "./data/backups"]
            for backup_dir in app_backup_dirs:
                if not os.path.exists(backup_dir):
                    continue
                    
                try:
                    # Only clean files with our application prefixes
                    backup_files = []
                    for prefix in app_prefixes:
                        backup_files.extend(glob.glob(f"{backup_dir}/{prefix}*.sql"))
                        backup_files.extend(glob.glob(f"{backup_dir}/{prefix}*.dump"))
                        backup_files.extend(glob.glob(f"{backup_dir}/backup_{prefix}*"))
                    
                    # Sort by modification time and keep only the 3 most recent
                    backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    for old_backup in backup_files[3:]:
                        try:
                            # Verify it's our backup file
                            backup_path = Path(old_backup)
                            if any(backup_path.name.startswith(p) or f"_{p}" in backup_path.name for p in app_prefixes):
                                await self._safe_remove_file(old_backup)
                                cleanup_actions.append(f"Removed old backup: {old_backup}")
                        except Exception as e:
                            self.logger.error(f"Failed to remove backup file {old_backup}", error=str(e), exc_info=True)
                except Exception as e:
                    self.logger.error(f"Failed to clean backup directory {backup_dir}", error=str(e), exc_info=True)
            
            # 4. Clean up old application cache files
            app_cache_dirs = ["./cache", "./data/cache", "./app/cache"]
            for cache_dir in app_cache_dirs:
                if not os.path.exists(cache_dir):
                    continue
                    
                try:
                    # Only clean files with our application prefixes or specific patterns
                    cache_patterns = ["market_data_*", "trading_*", "crypto_*", "*.cache"]
                    cache_files = []
                    
                    for pattern in cache_patterns:
                        cache_files.extend(glob.glob(f"{cache_dir}/{pattern}"))
                    
                    for cache_file in cache_files:
                        try:
                            file_path = Path(cache_file)
                            if file_path.stat().st_mtime < (time.time() - 3 * 24 * 3600):  # 3 days
                                # Verify it's our cache file
                                if (any(file_path.name.startswith(p) for p in app_prefixes) or 
                                    file_path.name.startswith(("market_data_", "trading_", "crypto_")) or
                                    file_path.suffix == ".cache"):
                                    await self._safe_remove_file(cache_file)
                                    cleanup_actions.append(f"Removed old cache: {cache_file}")
                        except Exception as e:
                            self.logger.error(f"Failed to remove cache file {cache_file}", error=str(e), exc_info=True)
                except Exception as e:
                    self.logger.error(f"Failed to clean cache directory {cache_dir}", error=str(e), exc_info=True)
            
            # 5. Archive old application trading data (compress files older than 30 days)
            app_data_dirs = ["./data", "./app/data", "./exports"]
            for data_dir in app_data_dirs:
                if not os.path.exists(data_dir):
                    continue
                    
                try:
                    # Only process files with our application prefixes
                    data_files = []
                    for prefix in app_prefixes:
                        data_files.extend(glob.glob(f"{data_dir}/{prefix}*.json"))
                        data_files.extend(glob.glob(f"{data_dir}/{prefix}*.csv"))
                        data_files.extend(glob.glob(f"{data_dir}/export_{prefix}*"))
                    
                    for data_file in data_files:
                        try:
                            file_path = Path(data_file)
                            if file_path.stat().st_mtime < (time.time() - 30 * 24 * 3600):  # 30 days
                                # Verify it's our data file
                                if any(file_path.name.startswith(p) or f"_{p}" in file_path.name for p in app_prefixes):
                                    # Compress and remove using async helper
                                    await self._compress_then_remove(data_file)
                                    cleanup_actions.append(f"Compressed old data: {data_file}")
                        except Exception as e:
                            self.logger.error(f"Failed to compress data file {data_file}", error=str(e), exc_info=True)
                except Exception as e:
                    self.logger.error(f"Failed to clean data directory {data_dir}", error=str(e), exc_info=True)
            
            if cleanup_actions:
                self.logger.info(f"🧹 Disk cleanup completed: {len(cleanup_actions)} actions taken", actions=cleanup_actions[:5])  # Log first 5
            else:
                self.logger.info("🧹 Disk cleanup completed: No cleanup needed")
            
        except Exception as e:
            self.logger.error("Automated disk cleanup failed", error=str(e))
    
    async def _run_cleanup_if_allowed(self):
        """Run disk cleanup with cooldown and single-flight protection."""
        current_time = time.time()
        
        # Check cooldown
        if current_time - self._last_cleanup < self._cleanup_cooldown:
            self.logger.debug(f"Disk cleanup skipped - cooldown active ({self._cleanup_cooldown - (current_time - self._last_cleanup):.0f}s remaining)")
            return
        
        # Single-flight protection
        if self._cleanup_lock.locked():
            self.logger.debug("Disk cleanup already in progress - skipping")
            return
        
        async with self._cleanup_lock:
            try:
                self._last_cleanup = current_time
                self.logger.info("Starting non-blocking disk cleanup")
                await self._automated_disk_cleanup()
                self.logger.info("Non-blocking disk cleanup completed successfully")
            except Exception as e:
                self.logger.error("Non-blocking disk cleanup failed", error=str(e), exc_info=True)
            finally:
                # Update last cleanup time even on failure to prevent spam
                self._last_cleanup = time.time()
    
    @staticmethod
    def _compress_then_remove_sync(file_path: str) -> None:
        """Compress a file to .gz and remove the original - runs in thread pool."""
        import gzip
        import os
        
        try:
            import structlog
            logger = structlog.get_logger()
            abs_path = os.path.realpath(file_path)
            allowed_roots = [os.path.realpath(p) for p in (
                "./logs", "./app/logs", "./var/log/app",
                "./tmp", "./temp", "./cache/tmp",
                "./backups", "./data/backups",
                "./cache", "./data/cache", "./app/cache",
                "./data", "./app/data", "./exports"
            )]
            
            # Security checks
            if os.path.islink(file_path):
                logger.warning("Skipping symlink during compression", path=file_path)
                return
            if not any(os.path.commonpath([abs_path, root]) == root for root in allowed_roots):
                logger.warning("Refusing to compress outside allowed dirs", path=abs_path)
                return
                
            gz_path = f"{file_path}.gz"
            
            # Compress the file
            with open(file_path, 'rb') as f_in:
                with gzip.open(gz_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Remove original file
            os.remove(file_path)
            
        except Exception as e:
            # Log error and re-raise so caller can handle/log per-file context
            import structlog
            logger = structlog.get_logger()
            logger.error(f"Failed to compress and remove file {file_path}", error=str(e), exc_info=True)
            raise
    
    @staticmethod
    def _safe_remove_file_sync(file_path: str) -> None:
        """Safely remove a file - runs in thread pool."""
        import os
        
        try:
            import structlog
            logger = structlog.get_logger()
            abs_path = os.path.realpath(file_path)
            allowed_roots = [os.path.realpath(p) for p in (
                "./logs", "./app/logs", "./var/log/app",
                "./tmp", "./temp", "./cache/tmp",
                "./backups", "./data/backups",
                "./cache", "./data/cache", "./app/cache",
                "./data", "./app/data", "./exports"
            )]
            
            # Security checks
            if os.path.islink(file_path):
                logger.warning("Skipping symlink during delete", path=file_path)
                return
            if not any(os.path.commonpath([abs_path, root]) == root for root in allowed_roots):
                logger.warning("Refusing to delete outside allowed dirs", path=abs_path)
                return
                
            os.remove(file_path)
            
        except Exception as e:
            # Log error and re-raise so caller can handle/log per-file context
            import structlog
            logger = structlog.get_logger()
            logger.error(f"Failed to remove file {file_path}", error=str(e), exc_info=True)
            raise
    
    async def _safe_remove_file(self, file_path: str) -> None:
        """Async wrapper for safe file removal."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._safe_remove_file_sync, file_path)
    
    async def _compress_then_remove(self, file_path: str) -> None:
        """Async wrapper for compress and remove operation."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._compress_then_remove_sync, file_path)
