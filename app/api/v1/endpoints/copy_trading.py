"""
Copy trading API endpoints.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.copy_trading import (
    StrategyPublisher,
    StrategyFollower,
    StrategyPerformance,
    CopyTradeSignal,
    StrategyStatus
)
from app.models.trading import TradingStrategy
from app.services.copy_trading_service import CopyTradingService

router = APIRouter()

# Initialize service
copy_trading_service = CopyTradingService()


@router.get("/providers")
async def get_signal_providers(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    verified_only: bool = Query(False),
    tier: Optional[str] = Query(None),
    sort_by: str = Query("returns", regex="^(returns|winrate|followers|signals)$")
):
    """Get list of signal providers with their performance data."""
    try:
        providers = await copy_trading_service.get_signal_providers(
            db=db,
            limit=limit,
            offset=offset,
            verified_only=verified_only,
            tier=tier,
            sort_by=sort_by
        )
        return {
            "success": True,
            "data": providers,
            "total": len(providers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-stats")
async def get_my_copy_trading_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's copy trading statistics."""
    try:
        stats = await copy_trading_service.get_user_copy_trading_stats(
            db=db, user_id=current_user.id
        )
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/following")
async def get_following_strategies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get strategies user is following."""
    try:
        following = await copy_trading_service.get_user_following(
            db=db, user_id=current_user.id
        )
        return {
            "success": True,
            "data": following
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/copied-trades")
async def get_copied_trades(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_only: bool = Query(True)
):
    """Get user's copied trades."""
    try:
        trades = await copy_trading_service.get_user_copied_trades(
            db=db, user_id=current_user.id, active_only=active_only
        )
        return {
            "success": True,
            "data": trades
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaderboard")
async def get_leaderboard(
    db: Session = Depends(get_db),
    period: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    limit: int = Query(10, ge=1, le=50)
):
    """Get copy trading leaderboard."""
    try:
        leaderboard = await copy_trading_service.get_leaderboard(
            db=db, period=period, limit=limit
        )
        return {
            "success": True,
            "data": leaderboard
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/follow/{strategy_id}")
async def follow_strategy(
    strategy_id: UUID,
    allocation_percentage: float = Query(..., ge=1.0, le=100.0),
    max_drawdown: float = Query(20.0, ge=5.0, le=50.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Follow a trading strategy."""
    try:
        result = await copy_trading_service.follow_strategy(
            db=db,
            user_id=current_user.id,
            strategy_id=strategy_id,
            allocation_percentage=allocation_percentage,
            max_drawdown_percentage=max_drawdown
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/unfollow/{strategy_id}")
async def unfollow_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Unfollow a trading strategy."""
    try:
        result = await copy_trading_service.unfollow_strategy(
            db=db, user_id=current_user.id, strategy_id=strategy_id
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/feed")
async def get_signal_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100)
):
    """Get live signal feed from followed strategies."""
    try:
        signals = await copy_trading_service.get_user_signal_feed(
            db=db, user_id=current_user.id, limit=limit
        )
        return {
            "success": True,
            "data": signals
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/{strategy_id}")
async def get_strategy_performance(
    strategy_id: UUID,
    period: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    db: Session = Depends(get_db)
):
    """Get detailed performance data for a strategy."""
    try:
        performance = await copy_trading_service.get_strategy_performance(
            db=db, strategy_id=strategy_id, period=period
        )
        return {
            "success": True,
            "data": performance
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))