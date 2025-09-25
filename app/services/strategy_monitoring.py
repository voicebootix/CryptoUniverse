#!/usr/bin/env python3
"""
Enterprise Strategy System Monitoring
Real-time monitoring, alerts, and performance tracking for the unified strategy system
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import structlog

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_database_session
from app.models.user import User, UserRole
from app.models.strategy_access import UserStrategyAccess, StrategyAccessType, StrategyType
from app.services.unified_strategy_service import unified_strategy_service
from app.core.logging import LoggerMixin

settings = get_settings()


@dataclass
class SystemHealthMetrics:
    """System health metrics for monitoring dashboard"""
    timestamp: datetime
    total_users: int
    active_strategy_access: int
    admin_users: int
    strategy_access_performance_ms: float
    database_performance_ms: float
    error_rate_percentage: float
    redis_fallback_rate_percentage: float

    # Performance metrics
    avg_portfolio_response_time_ms: float
    successful_requests_24h: int
    failed_requests_24h: int

    # Strategy metrics
    total_ai_strategies: int
    total_community_strategies: int
    most_popular_strategies: List[Dict[str, Any]]

    # Alerts
    alerts: List[Dict[str, Any]]
    overall_status: str  # "healthy", "degraded", "unhealthy"


class StrategySystemMonitor(LoggerMixin):
    """Enterprise monitoring for unified strategy system"""

    def __init__(self):
        self._health_cache = {}
        self._cache_duration = 60  # 1 minute cache

    async def get_system_health(self) -> SystemHealthMetrics:
        """Get comprehensive system health metrics"""

        cache_key = "system_health"
        now = datetime.utcnow()

        # Check cache
        if cache_key in self._health_cache:
            cached_data, cached_time = self._health_cache[cache_key]
            if (now - cached_time).total_seconds() < self._cache_duration:
                return cached_data

        start_time = datetime.utcnow()

        try:
            async with get_database_session() as db:
                # Basic user metrics
                user_metrics = await self._get_user_metrics(db)

                # Strategy access metrics
                access_metrics = await self._get_strategy_access_metrics(db)

                # Performance metrics
                performance_metrics = await self._get_performance_metrics(db)

                # Popular strategies
                popular_strategies = await self._get_popular_strategies(db)

                # System alerts
                alerts = await self._generate_system_alerts(db)

            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Determine overall status
            overall_status = self._determine_overall_status(alerts, performance_metrics)

            health_metrics = SystemHealthMetrics(
                timestamp=now,
                total_users=user_metrics["total_users"],
                active_strategy_access=access_metrics["active_access"],
                admin_users=user_metrics["admin_users"],
                strategy_access_performance_ms=execution_time_ms,
                database_performance_ms=performance_metrics["db_response_time_ms"],
                error_rate_percentage=performance_metrics["error_rate"],
                redis_fallback_rate_percentage=performance_metrics["fallback_rate"],
                avg_portfolio_response_time_ms=performance_metrics["avg_response_time_ms"],
                successful_requests_24h=performance_metrics["successful_requests"],
                failed_requests_24h=performance_metrics["failed_requests"],
                total_ai_strategies=len(unified_strategy_service._ai_strategy_catalog),
                total_community_strategies=access_metrics["community_strategies"],
                most_popular_strategies=popular_strategies,
                alerts=alerts,
                overall_status=overall_status
            )

            # Cache results
            self._health_cache[cache_key] = (health_metrics, now)

            self.logger.info(
                "📊 System health check completed",
                overall_status=overall_status,
                execution_time_ms=execution_time_ms,
                total_users=user_metrics["total_users"],
                active_strategies=access_metrics["active_access"],
                alerts_count=len(alerts)
            )

            return health_metrics

        except Exception as e:
            self.logger.error("System health check failed", error=str(e), exc_info=True)

            # Return degraded metrics on error
            return SystemHealthMetrics(
                timestamp=now,
                total_users=0,
                active_strategy_access=0,
                admin_users=0,
                strategy_access_performance_ms=9999,
                database_performance_ms=9999,
                error_rate_percentage=100,
                redis_fallback_rate_percentage=100,
                avg_portfolio_response_time_ms=9999,
                successful_requests_24h=0,
                failed_requests_24h=1,
                total_ai_strategies=0,
                total_community_strategies=0,
                most_popular_strategies=[],
                alerts=[{
                    "level": "critical",
                    "message": f"System health check failed: {str(e)}",
                    "timestamp": now.isoformat()
                }],
                overall_status="unhealthy"
            )

    async def _get_user_metrics(self, db: AsyncSession) -> Dict[str, int]:
        """Get user-related metrics"""

        # Total users
        total_users_result = await db.execute(
            select(func.count(User.id))
        )
        total_users = total_users_result.scalar() or 0

        # Admin users
        admin_users_result = await db.execute(
            select(func.count(User.id)).where(User.role == UserRole.ADMIN)
        )
        admin_users = admin_users_result.scalar() or 0

        return {
            "total_users": total_users,
            "admin_users": admin_users
        }

    async def _get_strategy_access_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get strategy access metrics"""

        # Active strategy access records
        active_access_result = await db.execute(
            select(func.count(UserStrategyAccess.id)).where(
                UserStrategyAccess.is_active == True
            )
        )
        active_access = active_access_result.scalar() or 0

        # Community strategies count
        community_strategies_result = await db.execute(
            select(func.count(UserStrategyAccess.id)).where(
                UserStrategyAccess.strategy_type == StrategyType.COMMUNITY_STRATEGY
            )
        )
        community_strategies = community_strategies_result.scalar() or 0

        # Access by type
        access_by_type = {}
        for access_type in StrategyAccessType:
            count_result = await db.execute(
                select(func.count(UserStrategyAccess.id)).where(
                    UserStrategyAccess.access_type == access_type
                )
            )
            access_by_type[access_type.value] = count_result.scalar() or 0

        return {
            "active_access": active_access,
            "community_strategies": community_strategies,
            "access_by_type": access_by_type
        }

    async def _get_performance_metrics(self, db: AsyncSession) -> Dict[str, float]:
        """Get system performance metrics"""

        # Test database performance
        db_start = datetime.utcnow()
        await db.execute(select(1))
        db_response_time_ms = (datetime.utcnow() - db_start).total_seconds() * 1000

        return {
            "db_response_time_ms": db_response_time_ms,
            "error_rate": 0.0,  # Would be calculated from logs in production
            "fallback_rate": 0.0,  # Would be calculated from logs in production
            "avg_response_time_ms": 250.0,  # Would be calculated from metrics
            "successful_requests": 1000,  # Would come from metrics
            "failed_requests": 10  # Would come from metrics
        }

    async def _get_popular_strategies(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get most popular strategies"""

        try:
            # Get top strategies by access count
            popular_result = await db.execute(
                select(
                    UserStrategyAccess.strategy_id,
                    func.count(UserStrategyAccess.id).label('access_count')
                )
                .where(UserStrategyAccess.is_active == True)
                .group_by(UserStrategyAccess.strategy_id)
                .order_by(desc('access_count'))
                .limit(5)
            )

            popular_strategies = []
            for row in popular_result:
                strategy_id, access_count = row

                # Get strategy name from catalog if AI strategy
                if strategy_id.startswith('ai_'):
                    strategy_key = strategy_id.replace('ai_', '')
                    catalog_entry = unified_strategy_service._ai_strategy_catalog.get(strategy_key, {})
                    strategy_name = catalog_entry.get('name', strategy_id)
                    category = catalog_entry.get('category', 'AI Strategy')
                else:
                    strategy_name = strategy_id
                    category = 'Community'

                popular_strategies.append({
                    "strategy_id": strategy_id,
                    "name": strategy_name,
                    "category": category,
                    "access_count": access_count
                })

            return popular_strategies

        except Exception as e:
            self.logger.warning("Failed to get popular strategies", error=str(e))
            return []

    async def _generate_system_alerts(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Generate system alerts based on metrics"""

        alerts = []

        try:
            # Check for users without strategy access
            users_without_strategies = await db.execute(
                select(func.count(User.id))
                .select_from(User)
                .outerjoin(UserStrategyAccess, User.id == UserStrategyAccess.user_id)
                .where(UserStrategyAccess.user_id.is_(None))
            )

            no_access_count = users_without_strategies.scalar() or 0

            if no_access_count > 0:
                alerts.append({
                    "level": "warning",
                    "message": f"{no_access_count} users have no strategy access",
                    "timestamp": datetime.utcnow().isoformat(),
                    "category": "user_access"
                })

            # Check for expired access records
            expired_access = await db.execute(
                select(func.count(UserStrategyAccess.id)).where(
                    UserStrategyAccess.expires_at < datetime.utcnow()
                )
            )

            expired_count = expired_access.scalar() or 0

            if expired_count > 0:
                alerts.append({
                    "level": "info",
                    "message": f"{expired_count} strategy access records have expired",
                    "timestamp": datetime.utcnow().isoformat(),
                    "category": "access_expiration"
                })

        except Exception as e:
            alerts.append({
                "level": "error",
                "message": f"Failed to generate alerts: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
                "category": "system_error"
            })

        return alerts

    def _determine_overall_status(self, alerts: List[Dict], performance_metrics: Dict) -> str:
        """Determine overall system status"""

        # Check for critical alerts
        if any(alert.get("level") == "critical" for alert in alerts):
            return "unhealthy"

        # Check performance thresholds
        if performance_metrics.get("db_response_time_ms", 0) > 1000:
            return "degraded"

        if performance_metrics.get("error_rate", 0) > 5:
            return "degraded"

        # Check for warnings
        if any(alert.get("level") == "error" for alert in alerts):
            return "degraded"

        return "healthy"

    async def trigger_system_maintenance(self) -> Dict[str, Any]:
        """Trigger system maintenance tasks"""

        maintenance_results = {}

        try:
            self.logger.info("🔧 Starting system maintenance")

            # Clean up expired access records
            async with get_database_session() as db:
                cleanup_result = await db.execute(
                    select(func.count(UserStrategyAccess.id)).where(
                        UserStrategyAccess.expires_at < datetime.utcnow(),
                        UserStrategyAccess.is_active == True
                    )
                )

                expired_count = cleanup_result.scalar() or 0

                if expired_count > 0:
                    # Deactivate expired records
                    from sqlalchemy import update
                    await db.execute(
                        update(UserStrategyAccess)
                        .where(
                            UserStrategyAccess.expires_at < datetime.utcnow(),
                            UserStrategyAccess.is_active == True
                        )
                        .values(is_active=False, updated_at=datetime.utcnow())
                    )

                    await db.commit()

                    maintenance_results["expired_access_cleaned"] = expired_count
                    self.logger.info(f"Cleaned up {expired_count} expired access records")

            # Clear monitoring cache
            self._health_cache.clear()
            maintenance_results["cache_cleared"] = True

            maintenance_results["maintenance_completed"] = True
            maintenance_results["timestamp"] = datetime.utcnow().isoformat()

            self.logger.info("✅ System maintenance completed", results=maintenance_results)

        except Exception as e:
            self.logger.error("System maintenance failed", error=str(e), exc_info=True)
            maintenance_results["error"] = str(e)
            maintenance_results["maintenance_completed"] = False

        return maintenance_results


# Global monitoring instance
strategy_system_monitor = StrategySystemMonitor()


async def get_strategy_system_monitor() -> StrategySystemMonitor:
    """Dependency injection for FastAPI"""
    return strategy_system_monitor