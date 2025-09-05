"""
API Router Configuration
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    trading,
    admin,
    exchanges,
    strategies,
    credits,
    chat,
    telegram,
    paper_trading,
    password_reset  # Add the new password reset endpoints
)

# Create main router
router = APIRouter()

# Include all endpoint routers
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(password_reset.router, tags=["Authentication"])  # Add password reset routes
router.include_router(trading.router, prefix="/trading", tags=["Trading"])
router.include_router(exchanges.router, prefix="/exchanges", tags=["Exchanges"])
router.include_router(strategies.router, prefix="/strategies", tags=["Strategies"])
router.include_router(credits.router, prefix="/credits", tags=["Credits"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(telegram.router, prefix="/telegram", tags=["Telegram"])
router.include_router(paper_trading.router, prefix="/paper-trading", tags=["Paper Trading"])
router.include_router(admin.router, prefix="/admin", tags=["Admin"])