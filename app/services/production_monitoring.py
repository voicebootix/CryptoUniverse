"""
Production Monitoring Service - Enterprise Grade

Comprehensive monitoring, alerting, and health checks for production deployment.
Tracks system performance, user activity, trading metrics, and service health.

No mock data - real production monitoring with alerting capabilities.
"""

import asyncio
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import structlog
from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_database, engine
from app.core.redis import get_redis_client
from app.core.logging import LoggerMixin
from app.models.user import User
from app.models.trading import Trade, Position, Order
from app.models.exchange import ExchangeAccount, ExchangeApiKey
from app.services.user_exchange_service import user_exchange_service

settings = get_settings()
logger = structlog.get_logger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_connections: int
    response_time_ms: float
    error_rate_percent: float
    uptime_seconds: float


@dataclass
class TradingMetrics:
    """Trading performance metrics."""
    total_trades_24h: int
    successful_trades_24h: int
    failed_trades_24h: int
    total_volume_24h_usd: float
    active_users_24h: int
    avg_trade_size_usd: float
    success_rate_percent: float


class ProductionMonitoringService(LoggerMixin):
    """
    Enterprise-grade production monitoring service.
    
    Provides comprehensive system monitoring, performance tracking,
    alerting, and health checks for production deployment.
    """
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.alert_thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "error_rate_percent": 5.0,
            "response_time_ms": 2000.0,
            "failed_trades_percent": 10.0
        }
        self.redis = None
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        try:
            # System metrics
            system_metrics = await self._get_system_metrics()
            
            # Database health
            db_health = await self._check_database_health()
            
            # Redis health
            redis_health = await self._check_redis_health()
            
            # Exchange connectivity
            exchange_health = await self._check_exchange_connectivity()
            
            # Trading performance
            trading_metrics = await self._get_trading_metrics()
            
            # Calculate overall health score
            health_score = self._calculate_health_score(
                system_metrics, db_health, redis_health, 
                exchange_health, trading_metrics
            )
            
            # Determine status
            if health_score >= 95:
                status = "excellent"
            elif health_score >= 85:
                status = "good"
            elif health_score >= 70:
                status = "warning"
            else:
                status = "critical"
            
            return {
                "status": status,
                "health_score": health_score,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_hours": (datetime.utcnow() - self.start_time).total_seconds() / 3600,
                "system_metrics": system_metrics.__dict__,
                "database_health": db_health,
                "redis_health": redis_health,
                "exchange_health": exchange_health,
                "trading_metrics": trading_metrics.__dict__,
                "alerts": await self._get_active_alerts()
            }
            
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return {
                "status": "error",
                "health_score": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_system_metrics(self) -> SystemMetrics:
        """Get system performance metrics."""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network connections (approximate)
            connections = len(psutil.net_connections())
            
            # Uptime
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
            
            # Response time (from recent requests)
            response_time_ms = await self._get_avg_response_time()
            
            # Error rate
            error_rate = await self._get_error_rate()
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                active_connections=connections,
                response_time_ms=response_time_ms,
                error_rate_percent=error_rate,
                uptime_seconds=uptime_seconds
            )
            
        except Exception as e:
            self.logger.error("Failed to get system metrics", error=str(e))
            return SystemMetrics(0, 0, 0, 0, 0, 0, 0)
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health and performance."""
        try:
            start_time = datetime.utcnow()
            
            async with engine.begin() as conn:
                # Test basic connectivity
                await conn.execute(text("SELECT 1"))
                
                # Get database stats
                result = await conn.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins + n_tup_upd + n_tup_del as total_operations
                    FROM pg_stat_user_tables 
                    ORDER BY total_operations DESC 
                    LIMIT 5
                """))
                table_stats = [dict(row._mapping) for row in result.fetchall()]
                
                # Get connection count
                result = await conn.execute(text("""
                    SELECT count(*) as active_connections 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """))
                active_connections = result.scalar()
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "active_connections": active_connections,
                "table_stats": table_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health and performance."""
        try:
            if not self.redis:
                self.redis = await get_redis_client()
            
            start_time = datetime.utcnow()
            
            # Test basic operations
            await self.redis.ping()
            await self.redis.set("health_check", "ok", ex=10)
            result = await self.redis.get("health_check")
            await self.redis.delete("health_check")
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            # Get Redis info
            info = await self.redis.info()
            
            return {
                "status": "healthy" if result == "ok" else "unhealthy",
                "response_time_ms": round(response_time, 2),
                "memory_usage_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands": info.get("total_commands_processed", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Redis health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_exchange_connectivity(self) -> Dict[str, Any]:
        """Check exchange API connectivity."""
        try:
            import aiohttp
            
            exchanges = [
                {"name": "binance", "url": "https://api.binance.com/api/v3/ping"},
                {"name": "kraken", "url": "https://api.kraken.com/0/public/SystemStatus"},
                {"name": "kucoin", "url": "https://api.kucoin.com/api/v1/status"},
                {"name": "coinbase", "url": "https://api.exchange.coinbase.com/time"}
            ]
            
            results = {}
            
            async with aiohttp.ClientSession() as session:
                for exchange in exchanges:
                    try:
                        start_time = datetime.utcnow()
                        async with session.get(
                            exchange["url"],
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            end_time = datetime.utcnow()
                            response_time = (end_time - start_time).total_seconds() * 1000
                            
                            results[exchange["name"]] = {
                                "status": "online" if response.status == 200 else "offline",
                                "response_time_ms": round(response_time, 2),
                                "status_code": response.status
                            }
                    except Exception as e:
                        results[exchange["name"]] = {
                            "status": "offline",
                            "error": str(e),
                            "response_time_ms": 5000  # Timeout
                        }
            
            online_count = sum(1 for result in results.values() if result["status"] == "online")
            
            return {
                "overall_status": "healthy" if online_count >= 2 else "degraded" if online_count >= 1 else "critical",
                "online_exchanges": online_count,
                "total_exchanges": len(exchanges),
                "exchange_details": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Exchange connectivity check failed", error=str(e))
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_trading_metrics(self) -> TradingMetrics:
        """Get trading performance metrics for last 24 hours."""
        try:
            async for db in get_database():
                # Get 24h trading data
                yesterday = datetime.utcnow() - timedelta(hours=24)
                
                # Total trades
                total_trades_result = await db.execute(
                    select(func.count(Trade.id)).where(Trade.created_at >= yesterday)
                )
                total_trades = total_trades_result.scalar() or 0
                
                # Successful trades
                from app.models.trading import TradeStatus
                successful_trades_result = await db.execute(
                    select(func.count(Trade.id)).where(
                        and_(
                            Trade.created_at >= yesterday,
                            Trade.status == TradeStatus.COMPLETED
                        )
                    )
                )
                successful_trades = successful_trades_result.scalar() or 0
                
                # Failed trades
                failed_trades = total_trades - successful_trades
                
                # Total volume
                volume_result = await db.execute(
                    select(func.sum(Trade.total_value)).where(
                        and_(
                            Trade.created_at >= yesterday,
                            Trade.status == TradeStatus.COMPLETED
                        )
                    )
                )
                total_volume = float(volume_result.scalar() or 0)
                
                # Active users
                active_users_result = await db.execute(
                    select(func.count(func.distinct(Trade.user_id))).where(
                        Trade.created_at >= yesterday
                    )
                )
                active_users = active_users_result.scalar() or 0
                
                # Calculate metrics
                success_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 100
                avg_trade_size = (total_volume / successful_trades) if successful_trades > 0 else 0
                
                return TradingMetrics(
                    total_trades_24h=total_trades,
                    successful_trades_24h=successful_trades,
                    failed_trades_24h=failed_trades,
                    total_volume_24h_usd=total_volume,
                    active_users_24h=active_users,
                    avg_trade_size_usd=avg_trade_size,
                    success_rate_percent=success_rate
                )
                
        except Exception as e:
            self.logger.error("Failed to get trading metrics", error=str(e))
            return TradingMetrics(0, 0, 0, 0.0, 0, 0.0, 0.0)
    
    async def _get_avg_response_time(self) -> float:
        """Get average response time from Redis metrics."""
        try:
            if not self.redis:
                self.redis = await get_redis_client()
            
            # Get recent response times
            response_times = await self.redis.lrange("response_times", 0, 99)
            
            if response_times:
                times = [float(rt) for rt in response_times]
                return sum(times) / len(times)
            
            return 0.0
            
        except Exception:
            return 0.0
    
    async def _get_error_rate(self) -> float:
        """Get error rate from Redis metrics."""
        try:
            if not self.redis:
                self.redis = await get_redis_client()
            
            # Get error count and total requests
            error_count = await self.redis.get("error_count_24h") or 0
            total_requests = await self.redis.get("total_requests_24h") or 0
            
            error_count = int(error_count)
            total_requests = int(total_requests)
            
            if total_requests > 0:
                return (error_count / total_requests) * 100
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_health_score(
        self,
        system_metrics: SystemMetrics,
        db_health: Dict[str, Any],
        redis_health: Dict[str, Any],
        exchange_health: Dict[str, Any],
        trading_metrics: TradingMetrics
    ) -> float:
        """Calculate overall health score (0-100)."""
        score = 100.0
        
        # System performance penalties
        if system_metrics.cpu_percent > self.alert_thresholds["cpu_percent"]:
            score -= 15
        if system_metrics.memory_percent > self.alert_thresholds["memory_percent"]:
            score -= 15
        if system_metrics.disk_percent > self.alert_thresholds["disk_percent"]:
            score -= 20
        if system_metrics.response_time_ms > self.alert_thresholds["response_time_ms"]:
            score -= 10
        if system_metrics.error_rate_percent > self.alert_thresholds["error_rate_percent"]:
            score -= 15
        
        # Database health penalties
        if db_health.get("status") != "healthy":
            score -= 25
        
        # Redis health penalties
        if redis_health.get("status") != "healthy":
            score -= 15
        
        # Exchange connectivity penalties
        if exchange_health.get("overall_status") == "critical":
            score -= 20
        elif exchange_health.get("overall_status") == "degraded":
            score -= 10
        
        # Trading performance penalties
        if trading_metrics.success_rate_percent < 90:
            score -= 10
        
        return max(0.0, score)
    
    async def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active system alerts."""
        alerts = []
        
        try:
            # Check system metrics against thresholds
            system_metrics = await self._get_system_metrics()
            
            if system_metrics.cpu_percent > self.alert_thresholds["cpu_percent"]:
                alerts.append({
                    "type": "system",
                    "severity": "warning",
                    "message": f"High CPU usage: {system_metrics.cpu_percent:.1f}%",
                    "threshold": self.alert_thresholds["cpu_percent"],
                    "current_value": system_metrics.cpu_percent
                })
            
            if system_metrics.memory_percent > self.alert_thresholds["memory_percent"]:
                alerts.append({
                    "type": "system",
                    "severity": "warning",
                    "message": f"High memory usage: {system_metrics.memory_percent:.1f}%",
                    "threshold": self.alert_thresholds["memory_percent"],
                    "current_value": system_metrics.memory_percent
                })
            
            if system_metrics.disk_percent > self.alert_thresholds["disk_percent"]:
                alerts.append({
                    "type": "system",
                    "severity": "critical",
                    "message": f"High disk usage: {system_metrics.disk_percent:.1f}%",
                    "threshold": self.alert_thresholds["disk_percent"],
                    "current_value": system_metrics.disk_percent
                })
            
            # Check trading metrics
            trading_metrics = await self._get_trading_metrics()
            
            if trading_metrics.success_rate_percent < 90:
                alerts.append({
                    "type": "trading",
                    "severity": "warning",
                    "message": f"Low trading success rate: {trading_metrics.success_rate_percent:.1f}%",
                    "threshold": 90.0,
                    "current_value": trading_metrics.success_rate_percent
                })
            
            return alerts
            
        except Exception as e:
            self.logger.error("Failed to get alerts", error=str(e))
            return []
    
    async def get_user_activity_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get user activity metrics."""
        try:
            async for db in get_database():
                since = datetime.utcnow() - timedelta(hours=hours)
                
                # Active users (users who made trades)
                active_users_result = await db.execute(
                    select(func.count(func.distinct(Trade.user_id))).where(
                        Trade.created_at >= since
                    )
                )
                active_users = active_users_result.scalar() or 0
                
                # Total users
                total_users_result = await db.execute(
                    select(func.count(User.id)).where(User.is_active == True)
                )
                total_users = total_users_result.scalar() or 0
                
                # Users with connected exchanges
                users_with_exchanges_result = await db.execute(
                    select(func.count(func.distinct(ExchangeAccount.user_id))).where(
                        ExchangeAccount.status == "active"
                    )
                )
                users_with_exchanges = users_with_exchanges_result.scalar() or 0
                
                # New registrations
                new_users_result = await db.execute(
                    select(func.count(User.id)).where(User.created_at >= since)
                )
                new_users = new_users_result.scalar() or 0
                
                return {
                    "period_hours": hours,
                    "total_users": total_users,
                    "active_users": active_users,
                    "users_with_exchanges": users_with_exchanges,
                    "new_registrations": new_users,
                    "user_engagement_rate": (active_users / total_users * 100) if total_users > 0 else 0,
                    "exchange_connection_rate": (users_with_exchanges / total_users * 100) if total_users > 0 else 0,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            self.logger.error("Failed to get user activity metrics", error=str(e))
            return {"error": str(e)}
    
    async def get_exchange_usage_stats(self) -> Dict[str, Any]:
        """Get exchange usage statistics."""
        try:
            async for db in get_database():
                # Exchange account distribution
                exchange_dist_result = await db.execute(
                    select(
                        ExchangeAccount.exchange_name,
                        func.count(ExchangeAccount.id).label("account_count"),
                        func.count(ExchangeAccount.id).filter(ExchangeAccount.status == "active").label("active_count")
                    ).group_by(ExchangeAccount.exchange_name)
                )
                
                exchange_distribution = []
                for row in exchange_dist_result.fetchall():
                    exchange_distribution.append({
                        "exchange": row.exchange_name,
                        "total_accounts": row.account_count,
                        "active_accounts": row.active_count,
                        "activation_rate": (row.active_count / row.account_count * 100) if row.account_count > 0 else 0
                    })
                
                # API key health
                api_key_health_result = await db.execute(
                    select(
                        ExchangeApiKey.status,
                        func.count(ExchangeApiKey.id).label("count")
                    ).group_by(ExchangeApiKey.status)
                )
                
                api_key_health = {}
                for row in api_key_health_result.fetchall():
                    api_key_health[row.status] = row.count
                
                return {
                    "exchange_distribution": exchange_distribution,
                    "api_key_health": api_key_health,
                    "total_exchange_accounts": sum(dist["total_accounts"] for dist in exchange_distribution),
                    "total_active_accounts": sum(dist["active_accounts"] for dist in exchange_distribution),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            self.logger.error("Failed to get exchange usage stats", error=str(e))
            return {"error": str(e)}
    
    async def record_request_metrics(self, response_time_ms: float, status_code: int):
        """Record request metrics for monitoring."""
        try:
            if not self.redis:
                self.redis = await get_redis_client()
            
            # Record response time
            await self.redis.lpush("response_times", response_time_ms)
            await self.redis.ltrim("response_times", 0, 999)  # Keep last 1000
            
            # Increment counters
            await self.redis.incr("total_requests_24h")
            await self.redis.expire("total_requests_24h", 86400)  # 24 hours
            
            if status_code >= 400:
                await self.redis.incr("error_count_24h")
                await self.redis.expire("error_count_24h", 86400)
            
        except Exception as e:
            self.logger.warning("Failed to record request metrics", error=str(e))


# Global service instance
production_monitoring = ProductionMonitoringService()


# FastAPI dependency
async def get_production_monitoring() -> ProductionMonitoringService:
    """Dependency injection for FastAPI."""
    return production_monitoring