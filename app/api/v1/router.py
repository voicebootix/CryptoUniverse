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
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(password_reset.router, tags=["Authentication"])  # Add password reset routes
api_router.include_router(trading.router, prefix="/trading", tags=["Trading"])
api_router.include_router(exchanges.router, prefix="/exchanges", tags=["Exchanges"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["Strategies"])
api_router.include_router(credits.router, prefix="/credits", tags=["Credits"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["Telegram"])
api_router.include_router(paper_trading.router, prefix="/paper-trading", tags=["Paper Trading"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])