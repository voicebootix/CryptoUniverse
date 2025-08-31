"""
Main API router for CryptoUniverse Enterprise v1.

This router includes all API endpoints for the enterprise platform.
"""

from fastapi import APIRouter
import structlog

# Import endpoint routers
from app.api.v1.endpoints import auth, trading, admin, exchanges, strategies, credits, telegram

logger = structlog.get_logger(__name__)

# Create the main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(trading.router, prefix="/trading", tags=["Trading"])
api_router.include_router(exchanges.router, prefix="/exchanges", tags=["Exchange Management"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["Trading Strategies"])
api_router.include_router(credits.router, prefix="/credits", tags=["Credit System"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["Telegram Integration"])
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
            "strategies": "/api/v1/strategies", 
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
