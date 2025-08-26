"""
Main API router for CryptoUniverse Enterprise v1.

This router will include all API endpoints for the enterprise platform.
"""

from fastapi import APIRouter
import structlog

logger = structlog.get_logger(__name__)

# Create the main API router
api_router = APIRouter()

# TODO: Add endpoint routers
# from app.api.v1.endpoints import auth, trading, portfolio, users, admin

# Include endpoint routers
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
# api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

@api_router.get("/status")
async def api_status():
    """API status endpoint."""
    return {
        "status": "operational",
        "version": "v1",
        "message": "CryptoUniverse Enterprise API v1"
    }
