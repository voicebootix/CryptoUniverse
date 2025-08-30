"""
Health Monitoring Service for Market Analysis

Monitors the health of all market data sources, exchanges, and APIs
with automatic failover and alerting capabilities.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import structlog

from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.services.market_data_feeds import MarketDataFeeds
from app.services.market_analysis_core import MarketAnalysisService

settings = get_settings()
logger = structlog.get_logger(__name__)


class HealthMonitor:
    """Comprehensive health monitoring for all market services."""
    
    def __init__(self):
        self.redis = None
        self.market_data_feeds = MarketDataFeeds()
        self.market_analysis = MarketAnalysisService()
        
        # Health check intervals (seconds)
        self.check_intervals = {
            "api_health": 60,      # Check API health every minute
            "exchange_health": 120, # Check exchange health every 2 minutes
            "service_health": 300   # Check service health every 5 minutes
        }
        
        # Health status tracking
        self.health_status = {
            "apis": {},
            "exchanges": {},
            "services": {},
            "overall": "UNKNOWN",
            "last_check": None
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            "api_failure_rate": 0.5,      # 50% failure rate
            "response_time_ms": 5000,      # 5 second response time
            "consecutive_failures": 3       # 3 consecutive failures
        }
    
    async def initialize(self):
        """Initialize the health monitor."""
        try:
            self.redis = await get_redis_client()
            await self.market_data_feeds.async_init()
            logger.info("Health monitor initialized")
        except Exception as e:
            logger.error("Failed to initialize health monitor", error=str(e))
    
    async def check_api_health(self) -> Dict[str, Any]:
        """Check health of all external APIs."""
        api_health = {}
        
        # Test each API with a simple request
        test_symbol = "BTC"
        
        # CoinGecko
        start_time = time.time()
        try:
            result = await self.market_data_feeds._fetch_coingecko_price(test_symbol)
            response_time = (time.time() - start_time) * 1000
            
            api_health["coingecko"] = {
                "status": "HEALTHY" if result.get("success") else "DEGRADED",
                "response_time_ms": round(response_time, 2),
                "last_check": datetime.utcnow().isoformat(),
                "error": result.get("error") if not result.get("success") else None
            }
        except Exception as e:
            api_health["coingecko"] = {
                "status": "UNHEALTHY",
                "response_time_ms": (time.time() - start_time) * 1000,
                "last_check": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        
        # Alpha Vantage (if API key available)
        if self.market_data_feeds.api_keys.get("alpha_vantage"):
            start_time = time.time()
            try:
                result = await self.market_data_feeds._fetch_alpha_vantage_price(test_symbol)
                response_time = (time.time() - start_time) * 1000
                
                api_health["alpha_vantage"] = {
                    "status": "HEALTHY" if result.get("success") else "DEGRADED",
                    "response_time_ms": round(response_time, 2),
                    "last_check": datetime.utcnow().isoformat(),
                    "error": result.get("error") if not result.get("success") else None
                }
            except Exception as e:
                api_health["alpha_vantage"] = {
                    "status": "UNHEALTHY",
                    "response_time_ms": (time.time() - start_time) * 1000,
                    "last_check": datetime.utcnow().isoformat(),
                    "error": str(e)
                }
        else:
            api_health["alpha_vantage"] = {
                "status": "NOT_CONFIGURED",
                "response_time_ms": 0,
                "last_check": datetime.utcnow().isoformat(),
                "error": "API key not configured"
            }
        
        # Finnhub (if API key available)
        if self.market_data_feeds.api_keys.get("finnhub"):
            start_time = time.time()
            try:
                result = await self.market_data_feeds._fetch_finnhub_price(test_symbol)
                response_time = (time.time() - start_time) * 1000
                
                api_health["finnhub"] = {
                    "status": "HEALTHY" if result.get("success") else "DEGRADED",
                    "response_time_ms": round(response_time, 2),
                    "last_check": datetime.utcnow().isoformat(),
                    "error": result.get("error") if not result.get("success") else None
                }
            except Exception as e:
                api_health["finnhub"] = {
                    "status": "UNHEALTHY",
                    "response_time_ms": (time.time() - start_time) * 1000,
                    "last_check": datetime.utcnow().isoformat(),
                    "error": str(e)
                }
        else:
            api_health["finnhub"] = {
                "status": "NOT_CONFIGURED",
                "response_time_ms": 0,
                "last_check": datetime.utcnow().isoformat(),
                "error": "API key not configured"
            }
        
        # CoinCap
        start_time = time.time()
        try:
            result = await self.market_data_feeds._fetch_coincap_price(test_symbol)
            response_time = (time.time() - start_time) * 1000
            
            api_health["coincap"] = {
                "status": "HEALTHY" if result.get("success") else "DEGRADED",
                "response_time_ms": round(response_time, 2),
                "last_check": datetime.utcnow().isoformat(),
                "error": result.get("error") if not result.get("success") else None
            }
        except Exception as e:
            api_health["coincap"] = {
                "status": "UNHEALTHY",
                "response_time_ms": (time.time() - start_time) * 1000,
                "last_check": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        
        self.health_status["apis"] = api_health
        return api_health
    
    async def check_exchange_health(self) -> Dict[str, Any]:
        """Check health of all exchange connections."""
        exchange_health = {}
        
        # Get exchange health from market analysis service
        try:
            health_result = await self.market_analysis.health_check()
            exchange_health = health_result.get("exchange_health", {})
            
            # Add response time checks
            for exchange in ["binance", "kraken", "kucoin", "coinbase", "bybit", "okx", "bitget", "gateio"]:
                if exchange not in exchange_health:
                    exchange_health[exchange] = {
                        "health_status": "UNKNOWN",
                        "circuit_breaker_state": "UNKNOWN",
                        "failure_count": 0,
                        "success_count": 0
                    }
                
                # Add last check timestamp
                exchange_health[exchange]["last_check"] = datetime.utcnow().isoformat()
        
        except Exception as e:
            logger.error("Exchange health check failed", error=str(e))
            # Provide fallback health status
            for exchange in ["binance", "kraken", "kucoin", "coinbase", "bybit", "okx", "bitget", "gateio"]:
                exchange_health[exchange] = {
                    "health_status": "UNKNOWN",
                    "error": str(e),
                    "last_check": datetime.utcnow().isoformat()
                }
        
        self.health_status["exchanges"] = exchange_health
        return exchange_health
    
    async def check_service_health(self) -> Dict[str, Any]:
        """Check health of all internal services."""
        service_health = {}
        
        # Redis health
        try:
            await self.redis.ping()
            service_health["redis"] = {
                "status": "HEALTHY",
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            service_health["redis"] = {
                "status": "UNHEALTHY",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
        
        # Market Analysis Service health
        try:
            market_health = await self.market_analysis.health_check()
            service_health["market_analysis"] = {
                "status": market_health.get("status", "UNKNOWN"),
                "performance_metrics": market_health.get("performance_metrics", {}),
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            service_health["market_analysis"] = {
                "status": "UNHEALTHY",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
        
        # Market Data Feeds health
        try:
            test_result = await self.market_data_feeds.get_real_time_price("BTC")
            service_health["market_data_feeds"] = {
                "status": "HEALTHY" if test_result.get("success") else "DEGRADED",
                "last_check": datetime.utcnow().isoformat(),
                "error": test_result.get("error") if not test_result.get("success") else None
            }
        except Exception as e:
            service_health["market_data_feeds"] = {
                "status": "UNHEALTHY",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
        
        self.health_status["services"] = service_health
        return service_health
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get comprehensive health status of all systems."""
        try:
            # Run all health checks in parallel
            api_health, exchange_health, service_health = await asyncio.gather(
                self.check_api_health(),
                self.check_exchange_health(),
                self.check_service_health(),
                return_exceptions=True
            )
            
            # Calculate overall health
            healthy_apis = sum(1 for api in api_health.values() if api.get("status") == "HEALTHY")
            total_apis = len(api_health)
            
            healthy_exchanges = sum(1 for ex in exchange_health.values() if ex.get("health_status") == "HEALTHY")
            total_exchanges = len(exchange_health)
            
            healthy_services = sum(1 for svc in service_health.values() if svc.get("status") == "HEALTHY")
            total_services = len(service_health)
            
            # Determine overall status
            if (healthy_apis / max(total_apis, 1) >= 0.8 and 
                healthy_services / max(total_services, 1) >= 0.8):
                overall_status = "HEALTHY"
            elif (healthy_apis / max(total_apis, 1) >= 0.5 and 
                  healthy_services / max(total_services, 1) >= 0.5):
                overall_status = "DEGRADED"
            else:
                overall_status = "UNHEALTHY"
            
            self.health_status.update({
                "overall": overall_status,
                "last_check": datetime.utcnow().isoformat(),
                "summary": {
                    "healthy_apis": f"{healthy_apis}/{total_apis}",
                    "healthy_exchanges": f"{healthy_exchanges}/{total_exchanges}",
                    "healthy_services": f"{healthy_services}/{total_services}",
                    "api_health_pct": round((healthy_apis / max(total_apis, 1)) * 100, 1),
                    "exchange_health_pct": round((healthy_exchanges / max(total_exchanges, 1)) * 100, 1),
                    "service_health_pct": round((healthy_services / max(total_services, 1)) * 100, 1)
                }
            })
            
            return self.health_status
            
        except Exception as e:
            logger.error("Overall health check failed", error=str(e))
            return {
                "overall": "UNHEALTHY",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def start_monitoring(self):
        """Start continuous health monitoring."""
        logger.info("Starting health monitoring")
        
        while True:
            try:
                await self.get_overall_health()
                
                # Store health status in Redis for quick access
                await self.redis.setex(
                    "system:health",
                    300,  # 5 minute cache
                    str(self.health_status)
                )
                
                # Check for alerts
                await self._check_alerts()
                
            except Exception as e:
                logger.error("Health monitoring cycle failed", error=str(e))
            
            # Wait before next check
            await asyncio.sleep(self.check_intervals["service_health"])
    
    async def _check_alerts(self):
        """Check for health alerts and log warnings."""
        try:
            # Check API failure rates
            for api_name, api_data in self.health_status.get("apis", {}).items():
                if api_data.get("status") == "UNHEALTHY":
                    logger.warning(f"API {api_name} is unhealthy", error=api_data.get("error"))
            
            # Check exchange health
            for exchange_name, exchange_data in self.health_status.get("exchanges", {}).items():
                if exchange_data.get("health_status") == "DEGRADED":
                    logger.warning(f"Exchange {exchange_name} is degraded")
            
            # Check service health
            for service_name, service_data in self.health_status.get("services", {}).items():
                if service_data.get("status") == "UNHEALTHY":
                    logger.error(f"Service {service_name} is unhealthy", error=service_data.get("error"))
        
        except Exception as e:
            logger.error("Alert checking failed", error=str(e))


# Global health monitor instance
health_monitor = HealthMonitor()


# Convenience functions
async def get_system_health() -> Dict[str, Any]:
    """Get current system health status."""
    return await health_monitor.get_overall_health()


async def get_api_health() -> Dict[str, Any]:
    """Get current API health status."""
    return await health_monitor.check_api_health()


async def get_exchange_health() -> Dict[str, Any]:
    """Get current exchange health status."""
    return await health_monitor.check_exchange_health()