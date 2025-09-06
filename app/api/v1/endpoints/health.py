"""
Health Check Endpoints for CryptoUniverse
Simple endpoints to verify server functionality and diagnose issues.
"""

import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_database
from app.core.redis import get_redis_client
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


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
        result = await db.execute("SELECT 1")
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
        
        return {
            "status": "healthy", 
            "redis": "connected",
            "timestamp": datetime.utcnow().isoformat()
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
        result = await db.execute("SELECT 1")
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
            health_status["checks"]["redis"] = {"status": "healthy", "connected": True}
        else:
            health_status["checks"]["redis"] = {"status": "unhealthy", "error": "Redis client not available"}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    return health_status