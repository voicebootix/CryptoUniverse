"""
Main API router for CryptoUniverse Enterprise v1.

This router includes all API endpoints for the enterprise platform.
"""

import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status as http_status
import structlog
from sqlalchemy import text

# Import endpoint routers
from app.api.v1.endpoints import (
    auth, trading, admin, exchanges, strategies, credits,
    telegram, paper_trading, unified_chat, market_analysis, api_keys, ai_consensus,
    password_reset, health, opportunity_discovery, admin_testing, ab_testing, admin_strategy_access,
    signals, unified_strategies, risk, diagnostics, scan_diagnostics, system_monitoring
)

from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis_client
from app.services.system_monitoring import system_monitoring_service

logger = structlog.get_logger(__name__)

# Create the main API router
api_router = APIRouter()

# Include endpoint routers - keep the comprehensive list from HEAD with cleaner tags from main
api_router.include_router(health.router, prefix="/health", tags=["Health"])  # Add health check endpoints first
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(password_reset.router, tags=["Authentication"])  # Add password reset routes
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(trading.router, prefix="/trading", tags=["Trading"])
api_router.include_router(exchanges.router, prefix="/exchanges", tags=["Exchanges"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["Strategies"])
api_router.include_router(credits.router, prefix="/credits", tags=["Credits"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["Telegram"])
api_router.include_router(paper_trading.router, prefix="/paper-trading", tags=["Paper Trading"])
api_router.include_router(market_analysis.router, prefix="/market", tags=["Market Analysis"])
api_router.include_router(signals.router, tags=["Signal Intelligence"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(admin_testing.router, tags=["Admin Testing"])  # Admin testing endpoints
api_router.include_router(diagnostics.router, prefix="/diagnostics", tags=["Diagnostics"])
api_router.include_router(scan_diagnostics.router, prefix="/scan-diagnostics", tags=["Scan Diagnostics"])
api_router.include_router(system_monitoring.router, prefix="/monitoring", tags=["System Monitoring"])
# Unified chat - single source of truth
api_router.include_router(unified_chat.router, prefix="/chat", tags=["Unified Chat"])
api_router.include_router(risk.router, prefix="/risk", tags=["Risk Management"])

# Backwards compatibility routes
api_router.include_router(unified_chat.router, prefix="/unified-chat", tags=["Unified Chat (Compatibility)"])
api_router.include_router(unified_chat.router, prefix="/conversational-chat", tags=["Unified Chat (Compatibility)"])
api_router.include_router(ai_consensus.router, prefix="/ai-consensus", tags=["AI Consensus"])
api_router.include_router(opportunity_discovery.router, prefix="/opportunities", tags=["Opportunity Discovery"])
api_router.include_router(ab_testing.router, prefix="/ab-testing", tags=["A/B Testing"])
api_router.include_router(admin_strategy_access.router, tags=["Admin Strategy Management"])
api_router.include_router(unified_strategies.router, tags=["Enterprise Strategy Management"])

# Add monitoring endpoint that frontend expects
def _build_alert(
    severity: str,
    message: str,
    *,
    metric: str,
    value: Any,
    threshold: Optional[Any] = None
) -> Dict[str, Any]:
    """Helper to build a consistent alert payload."""

    alert: Dict[str, Any] = {
        "severity": severity,
        "message": message,
        "metric": metric,
        "observed_value": value,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if threshold is not None:
        alert["threshold"] = threshold
    return alert


def _collect_endpoint_metrics(
    window_minutes: int = 5,
) -> Dict[str, Dict[str, float]]:
    """Return latency statistics for critical endpoints from in-memory metrics."""

    metrics: Dict[str, Dict[str, float]] = {}
    collector_metrics = system_monitoring_service.metrics_collector.metrics.get(
        "http_request_duration_ms"
    )

    if not collector_metrics:
        return metrics

    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    critical_paths = {
        "/api/v1/auth/login": "login",
        "/api/v1/diagnostics/test-layers": "diagnostics_layers",
        "/api/v1/scan-diagnostics/scan-metrics": "scan_metrics",
    }

    bucket: Dict[str, List[float]] = {label: [] for label in critical_paths.values()}

    for point in collector_metrics:
        if point.timestamp < cutoff:
            continue
        path = point.tags.get("path") if point.tags else None
        if path in critical_paths:
            bucket[critical_paths[path]].append(point.value)

    for label, values in bucket.items():
        if not values:
            continue
        sorted_values = sorted(values)
        if len(sorted_values) > 1:
            index = max(0, int(len(sorted_values) * 0.95) - 1)
            p95 = sorted_values[index]
        else:
            p95 = sorted_values[0]
        metrics[label] = {
            "count": len(sorted_values),
            "avg_ms": sum(sorted_values) / len(sorted_values),
            "p95_ms": p95,
            "max_ms": sorted_values[-1],
        }

    return metrics


@api_router.get("/monitoring/alerts")
async def get_monitoring_alerts():
    """Get system monitoring alerts with live infrastructure checks."""

    alerts: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}

    # Database latency check
    db_latency_ms: Optional[float] = None
    try:
        async with AsyncSessionLocal() as session:
            start = time.perf_counter()
            await session.execute(text("SELECT 1"))
            db_latency_ms = (time.perf_counter() - start) * 1000
        metrics["database_latency_ms"] = round(db_latency_ms, 2)

        if db_latency_ms > 5000:
            alerts.append(
                _build_alert(
                    "critical",
                    "Database latency exceeded 5s",
                    metric="database_latency_ms",
                    value=round(db_latency_ms, 2),
                    threshold=5000,
                )
            )
        elif db_latency_ms > 2000:
            alerts.append(
                _build_alert(
                    "warning",
                    "Database latency is above 2s",
                    metric="database_latency_ms",
                    value=round(db_latency_ms, 2),
                    threshold=2000,
                )
            )
    except Exception as db_error:
        alerts.append(
            _build_alert(
                "critical",
                "Database health check failed",
                metric="database_latency_ms",
                value=str(db_error),
            )
        )
        metrics["database_error"] = str(db_error)

    # Redis health check
    redis_latency_ms: Optional[float] = None
    try:
        redis = await get_redis_client()
        if not redis:
            raise RuntimeError("Redis client unavailable")
        start = time.perf_counter()
        await redis.ping()
        redis_latency_ms = (time.perf_counter() - start) * 1000
        metrics["redis_latency_ms"] = round(redis_latency_ms, 2)

        if redis_latency_ms > 1000:
            alerts.append(
                _build_alert(
                    "warning",
                    "Redis ping latency is elevated",
                    metric="redis_latency_ms",
                    value=round(redis_latency_ms, 2),
                    threshold=1000,
                )
            )
    except Exception as redis_error:
        alerts.append(
            _build_alert(
                "critical",
                "Redis health check failed",
                metric="redis_latency_ms",
                value=str(redis_error),
            )
        )
        metrics["redis_error"] = str(redis_error)

    # Endpoint performance metrics
    endpoint_metrics = _collect_endpoint_metrics()
    metrics["endpoint_latency"] = endpoint_metrics

    for endpoint, stats in endpoint_metrics.items():
        max_latency = stats.get("max_ms")
        if max_latency is None:
            continue
        if max_latency > 5000:
            alerts.append(
                _build_alert(
                    "critical",
                    f"{endpoint.replace('_', ' ').title()} latency exceeded 5s",
                    metric=f"endpoint_latency.{endpoint}",
                    value=round(max_latency, 2),
                    threshold=5000,
                )
            )
        elif max_latency > 2000:
            alerts.append(
                _build_alert(
                    "warning",
                    f"{endpoint.replace('_', ' ').title()} latency above 2s",
                    metric=f"endpoint_latency.{endpoint}",
                    value=round(max_latency, 2),
                    threshold=2000,
                )
            )

    system_status = "operational"
    if any(alert["severity"] == "critical" for alert in alerts):
        system_status = "critical"
    elif any(alert["severity"] == "warning" for alert in alerts):
        system_status = "degraded"

    return {
        "success": len(alerts) == 0,
        "alerts": alerts,
        "system_status": system_status,
        "metrics": metrics,
        "last_updated": datetime.utcnow().isoformat(),
    }

@api_router.get("/status")
async def api_status():
    """API status endpoint."""
    return {
        "status": "operational",
        "version": "v1",
        "message": "CryptoUniverse Enterprise API v1 - AI Money Manager",
        "endpoints": {
            "authentication": "/api/v1/auth",
            "api_keys": "/api/v1/api-keys",
            "trading": "/api/v1/trading",
            "exchanges": "/api/v1/exchanges",
            "ai_consensus": "/api/v1/ai-consensus",
            "administration": "/api/v1/admin"
        },
        "features": [
            "JWT Authentication with MFA",
            "API Key Management with Rotation",
            "Manual & Autonomous Trading",
            "AI Consensus Decision Making",
            "Simulation & Live Mode",
            "Rate Limiting & Security",
            "Multi-tenant Support",
            "Enterprise Administration"
        ]
    }


@api_router.get("/health")
async def health_check():
    """ENTERPRISE comprehensive health check endpoint."""
    # Use top-level imports instead of inline imports
    from app.core.redis import redis_manager
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    from app.services.ai_consensus_core import ai_consensus_service
    from app.services.market_data_feeds import market_data_feeds
    
    # Use perf_counter for precise timing
    start_time = time.perf_counter()
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "v1",
        "checks": {},
        "overall_status": "healthy",
        "response_time_ms": 0
    }
    
    try:
        # 1. Redis Health Check with timeout and per-check timing
        check_start = time.perf_counter()
        try:
            redis_ping = await asyncio.wait_for(redis_manager.ping(), timeout=2.0)
            response_time_ms = round((time.perf_counter() - check_start) * 1000, 2)
            health_status["checks"]["redis"] = {
                "status": "healthy" if redis_ping else "unhealthy",
                "response_time_ms": response_time_ms
            }
        except asyncio.TimeoutError:
            logger.warning("health.redis_timeout", service="redis")
            health_status["checks"]["redis"] = {
                "status": "unhealthy", 
                "error": "timeout",
                "response_time_ms": round((time.perf_counter() - check_start) * 1000, 2)
            }
        except Exception as e:
            logger.warning("health.redis_unhealthy", error=str(e))
            health_status["checks"]["redis"] = {
                "status": "unhealthy", 
                "error": str(e),
                "response_time_ms": round((time.perf_counter() - check_start) * 1000, 2)
            }
        
        # 2. Database Health Check with timeout and per-check timing
        check_start = time.perf_counter()
        try:
            async def db_check():
                async with AsyncSessionLocal() as db:
                    await db.execute(text("SELECT 1"))
            
            await asyncio.wait_for(db_check(), timeout=2.0)
            response_time_ms = round((time.perf_counter() - check_start) * 1000, 2)
            health_status["checks"]["database"] = {
                "status": "healthy",
                "response_time_ms": response_time_ms
            }
        except asyncio.TimeoutError:
            logger.warning("health.database_timeout", service="database")
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "error": "timeout",
                "response_time_ms": round((time.perf_counter() - check_start) * 1000, 2)
            }
        except Exception as e:
            logger.warning("health.database_unhealthy", error=str(e))
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round((time.perf_counter() - check_start) * 1000, 2)
            }
        
        # 3. AI Consensus Service Health with timeout and per-check timing
        check_start = time.perf_counter()
        try:
            ai_health = await asyncio.wait_for(ai_consensus_service.health_check(), timeout=2.0)
            response_time_ms = round((time.perf_counter() - check_start) * 1000, 2)
            health_status["checks"]["ai_consensus"] = {
                "status": "healthy" if ai_health.get("status") == "HEALTHY" else "degraded",
                "response_time_ms": response_time_ms
            }
        except asyncio.TimeoutError:
            logger.warning("health.ai_consensus_timeout", service="ai_consensus")
            health_status["checks"]["ai_consensus"] = {
                "status": "unhealthy",
                "error": "timeout",
                "response_time_ms": round((time.perf_counter() - check_start) * 1000, 2)
            }
        except Exception as e:
            logger.warning("health.ai_consensus_unhealthy", error=str(e))
            health_status["checks"]["ai_consensus"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round((time.perf_counter() - check_start) * 1000, 2)
            }
        
        # 4. Market Data Service Health with timeout and per-check timing
        check_start = time.perf_counter()
        try:
            ping_result = await asyncio.wait_for(
                market_data_feeds.get_real_time_price("BTC"), 
                timeout=2.0
            )
            response_time_ms = round((time.perf_counter() - check_start) * 1000, 2)
            health_status["checks"]["market_data"] = {
                "status": "healthy" if ping_result.get("success") else "degraded",
                "response_time_ms": response_time_ms
            }
        except asyncio.TimeoutError:
            logger.warning("health.market_data_timeout", service="market_data")
            health_status["checks"]["market_data"] = {
                "status": "unhealthy",
                "error": "timeout",
                "response_time_ms": round((time.perf_counter() - check_start) * 1000, 2)
            }
        except Exception as e:
            logger.warning("health.market_data_unhealthy", error=str(e))
            health_status["checks"]["market_data"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round((time.perf_counter() - check_start) * 1000, 2)
            }
        
        # Determine overall status
        unhealthy_services = [k for k, v in health_status["checks"].items() if v.get("status") == "unhealthy"]
        if unhealthy_services:
            health_status["overall_status"] = "unhealthy"
            health_status["status"] = "unhealthy"
        elif any(v.get("status") == "degraded" for v in health_status["checks"].values()):
            health_status["overall_status"] = "degraded" 
            health_status["status"] = "degraded"
        
        health_status["response_time_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
        
        # Return HTTP 503 when overall status is degraded or unhealthy
        if health_status["overall_status"] in ["degraded", "unhealthy"]:
            logger.info("Health check returned degraded/unhealthy status", status=health_status["overall_status"])
            from fastapi.responses import JSONResponse
            return JSONResponse(
                content=health_status,
                status_code=503
            )
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e), exc_info=True)
        error_response = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_time_ms": round((time.perf_counter() - start_time) * 1000, 2)
        }
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=error_response,
            status_code=503
        )
