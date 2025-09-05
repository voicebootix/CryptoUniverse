"""
Main API router for CryptoUniverse Enterprise v1.

This router includes all API endpoints for the enterprise platform.
"""

import time
from datetime import datetime
from fastapi import APIRouter
import structlog

# Import endpoint routers
from app.api.v1.endpoints import (
    auth, trading, admin, exchanges, strategies, credits,
    telegram, paper_trading, chat, market_analysis, api_keys, ai_consensus,
    password_reset  # Add the new password reset endpoints
)

logger = structlog.get_logger(__name__)

# Create the main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(password_reset.router, tags=["Authentication"])  # Add password reset routes
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(trading.router, prefix="/trading", tags=["Trading"])
api_router.include_router(exchanges.router, prefix="/exchanges", tags=["Exchange Management"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["Trading Strategies"])
api_router.include_router(credits.router, prefix="/credits", tags=["Credit System"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["Telegram Integration"])
api_router.include_router(paper_trading.router, prefix="/paper-trading", tags=["Paper Trading"])
api_router.include_router(market_analysis.router, prefix="/market", tags=["Market Analysis"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])
api_router.include_router(chat.router, prefix="/chat", tags=["AI Chat"])
api_router.include_router(ai_consensus.router, prefix="/ai-consensus", tags=["AI Consensus"])

# Add monitoring endpoint that frontend expects
@api_router.get("/monitoring/alerts")
async def get_monitoring_alerts(
    current_user: dict = None  # Make optional for now
):
    """Get system monitoring alerts."""
    try:
        # Return basic alerts structure that frontend expects
        return {
            "success": True,
            "alerts": [],
            "system_status": "operational",
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "alerts": [],
            "system_status": "unknown",
            "last_updated": datetime.utcnow().isoformat()
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
            from sqlalchemy import text
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
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
        
        # 3. AI Consensus Service Health
        try:
            from app.services.ai_consensus_core import ai_consensus_service
            ai_health = await ai_consensus_service.health_check()
            health_status["checks"]["ai_consensus"] = {
                "status": "healthy" if ai_health.get("status") == "HEALTHY" else "degraded",
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            health_status["checks"]["ai_consensus"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        
        # 4. Market Data Service Health
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