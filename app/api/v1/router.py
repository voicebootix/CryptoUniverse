"""
Main API router for CryptoUniverse Enterprise v1.

This router includes all API endpoints for the enterprise platform.
"""

from fastapi import APIRouter
import structlog

# Import endpoint routers
from app.api.v1.endpoints import auth, trading, admin, exchanges, market_analysis

logger = structlog.get_logger(__name__)

# Create the main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(trading.router, prefix="/trading", tags=["Trading"])
api_router.include_router(exchanges.router, prefix="/exchanges", tags=["Exchange Management"])
api_router.include_router(market_analysis.router, prefix="/market", tags=["Market Analysis"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])

@api_router.get("/status")
async def api_status():
    """API status endpoint."""
    return {
        "status": "operational",
        "version": "v1",
        "message": "CryptoUniverse Enterprise API v1 - AI Money Manager",
        "endpoints": {
            "authentication": "/api/v1/auth",
            "trading": "/api/v1/trading",
            "exchanges": "/api/v1/exchanges",
            "market_analysis": "/api/v1/market",
            "administration": "/api/v1/admin"
        },
        "features": [
            "JWT Authentication with MFA",
            "Manual & Autonomous Trading",
            "Simulation & Live Mode",
            "Rate Limiting & Security",
            "Multi-tenant Support",
            "Enterprise Administration"
        ]
    }


@api_router.get("/health")
async def health_check():
    """ENTERPRISE comprehensive health check endpoint."""
    import time
    from datetime import datetime
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "v1",
        "checks": {},
        "overall_status": "healthy",
        "response_time_ms": 0
    }
    
    start_time = time.time()
    
    try:
        # 1. Redis Health Check
        try:
            from app.core.redis import redis_manager
            redis_ping = await redis_manager.ping()
            health_status["checks"]["redis"] = {
                "status": "healthy" if redis_ping else "unhealthy",
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            health_status["checks"]["redis"] = {
                "status": "unhealthy", 
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        
        # 2. Database Health Check
        try:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                await db.execute("SELECT 1")
            health_status["checks"]["database"] = {
                "status": "healthy",
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        
        # 3. Market Data Service Health
        try:
            from app.services.market_data_feeds import market_data_feeds
            ping_result = await market_data_feeds.get_real_time_price("BTC")
            health_status["checks"]["market_data"] = {
                "status": "healthy" if ping_result.get("success") else "degraded",
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            health_status["checks"]["market_data"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        
        # 4. System Resources Check
        try:
            import psutil
            health_status["checks"]["system"] = {
                "status": "healthy",
                "cpu_usage_pct": psutil.cpu_percent(interval=0.1),
                "memory_usage_pct": psutil.virtual_memory().percent,
                "disk_usage_pct": psutil.disk_usage('/').percent if hasattr(psutil.disk_usage('/'), 'percent') else 0
            }
        except Exception:
            health_status["checks"]["system"] = {
                "status": "unknown",
                "message": "System monitoring unavailable"
            }
        
        # Determine overall status
        unhealthy_services = [k for k, v in health_status["checks"].items() if v.get("status") == "unhealthy"]
        if unhealthy_services:
            health_status["overall_status"] = "unhealthy"
            health_status["status"] = "unhealthy"
        elif any(v.get("status") == "degraded" for v in health_status["checks"].values()):
            health_status["overall_status"] = "degraded" 
            health_status["status"] = "degraded"
        
        health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return health_status
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }


@api_router.get("/monitoring/dashboard")
async def get_monitoring_dashboard(duration_minutes: int = 60):
    """ENTERPRISE comprehensive monitoring dashboard with metrics."""
    try:
        from app.services.system_monitoring import system_monitoring_service
        return system_monitoring_service.get_metrics_dashboard(duration_minutes)
    except Exception as e:
        logger.error("Monitoring dashboard failed", error=str(e))
        return {
            "error": "Monitoring dashboard unavailable",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@api_router.get("/monitoring/alerts")
async def get_active_alerts():
    """Get all active system alerts."""
    try:
        from app.services.system_monitoring import system_monitoring_service
        return {
            "active_alerts": system_monitoring_service.get_active_alerts(),
            "monitoring_status": system_monitoring_service.get_monitoring_status(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Alerts retrieval failed", error=str(e))
        return {
            "error": "Alerts unavailable", 
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@api_router.post("/monitoring/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve a specific alert."""
    try:
        from app.services.system_monitoring import system_monitoring_service
        success = system_monitoring_service.resolve_alert(alert_id)
        return {
            "success": success,
            "alert_id": alert_id,
            "message": "Alert resolved" if success else "Alert not found",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Alert resolution failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@api_router.post("/monitoring/start")
async def start_monitoring(interval_seconds: int = 30):
    """Start enhanced system monitoring."""
    try:
        from app.services.system_monitoring import system_monitoring_service
        await system_monitoring_service.start_monitoring(interval_seconds)
        return {
            "success": True,
            "message": f"Enhanced monitoring started with {interval_seconds}s interval",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Failed to start monitoring", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }