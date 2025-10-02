"""
Health Check Endpoints for CryptoUniverse
Simple endpoints to verify server functionality and diagnose issues.
"""

import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_database
from app.core.redis import get_redis_client
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


async def _collect_market_cache_metrics(redis) -> dict:
    """Gather cache freshness metrics for market overview and price snapshots."""
    metrics: dict = {}
    now = datetime.utcnow()

    async def _record_timestamp(redis_key: str, label: str) -> None:
        value = await redis.get(redis_key)
        if not value:
            return

        if isinstance(value, bytes):
            value = value.decode("utf-8")

        metrics[label] = value

        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return

        age_seconds = max(0.0, (now - parsed).total_seconds())
        metrics[f"{label}_age_seconds"] = round(age_seconds, 2)

    await _record_timestamp("market_analysis:last_overview_refresh", "market_overview_last_refresh")
    await _record_timestamp("market_analysis:last_price_refresh", "price_snapshot_last_refresh")
    await _record_timestamp("market_analysis:last_onchain_refresh", "onchain_metrics_last_refresh")
    await _record_timestamp("market_analysis:last_cache_warmer_run", "cache_warmer_last_run")

    overview_cache_key = await redis.get("market_analysis:last_overview_cache_key")
    if overview_cache_key:
        if isinstance(overview_cache_key, bytes):
            overview_cache_key = overview_cache_key.decode("utf-8")
        metrics["market_overview_cache_key"] = overview_cache_key
        try:
            ttl = await redis.ttl(overview_cache_key)
        except Exception:
            ttl = None
        if isinstance(ttl, int) and ttl >= 0:
            metrics["market_overview_ttl_seconds"] = ttl

    price_cache_key = await redis.get("market_analysis:last_price_cache_key")
    if price_cache_key:
        if isinstance(price_cache_key, bytes):
            price_cache_key = price_cache_key.decode("utf-8")
        metrics["price_snapshot_cache_key"] = price_cache_key
        try:
            ttl = await redis.ttl(price_cache_key)
        except Exception:
            ttl = None
        if isinstance(ttl, int) and ttl >= 0:
            metrics["price_snapshot_ttl_seconds"] = ttl

    return metrics


@router.get("/ping")
async def ping():
    """Simple ping endpoint with no dependencies."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Server is responsive"
    }


@router.get("/health")
async def health_check():
    """Basic health check without external dependencies."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "server": "running",
        "environment": "production"
    }


@router.get("/health/database")  
async def database_health(db: AsyncSession = Depends(get_database)):
    """Check database connectivity."""
    try:
        # Simple database query
        result = await db.execute(text("SELECT 1"))
        row = result.fetchone()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")


@router.get("/health/redis")
async def redis_health():
    """Check Redis connectivity."""
    try:
        redis = await get_redis_client()
        if not redis:
            raise Exception("Redis client not available")

        # Simple Redis operation
        await redis.ping()

        cache_metrics = await _collect_market_cache_metrics(redis)

        return {
            "status": "healthy",
            "redis": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "cache_metrics": cache_metrics,
        }
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Redis unhealthy: {str(e)}")


@router.get("/health/full")
async def full_health_check(db: AsyncSession = Depends(get_database)):
    """Comprehensive health check."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Database check
    try:
        result = await db.execute(text("SELECT 1"))
        row = result.fetchone()
        health_status["checks"]["database"] = {"status": "healthy", "connected": True}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Redis check
    try:
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            cache_metrics = await _collect_market_cache_metrics(redis)
            health_status["checks"]["redis"] = {
                "status": "healthy",
                "connected": True,
                "cache_metrics": cache_metrics,
            }
        else:
            health_status["checks"]["redis"] = {"status": "unhealthy", "error": "Redis client not available"}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    return health_status
