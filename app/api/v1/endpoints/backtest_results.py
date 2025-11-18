"""
Backtest Results API Endpoints

Provides endpoints to retrieve detailed backtest results including
individual trade records with entry/exit, stop loss, take profit, and position type.
"""

from typing import List, Optional
from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.market_data import BacktestResult

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/backtest-results")
async def get_backtest_results(
    strategy_id: Optional[str] = Query(None, description="Filter by strategy ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
) -> dict:
    """
    Get backtest results for the current user.
    
    Returns list of backtest results with summary metrics.
    """
    try:
        query = select(BacktestResult).where(
            BacktestResult.user_id == current_user.id
        )
        
        if strategy_id:
            query = query.where(BacktestResult.strategy_id == strategy_id)
        
        query = query.order_by(desc(BacktestResult.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        backtests = result.scalars().all()
        
        return {
            "success": True,
            "count": len(backtests),
            "results": [
                {
                    "id": str(bt.id),
                    "strategy_id": bt.strategy_id,
                    "strategy_name": bt.strategy_name,
                    "start_date": bt.start_date.isoformat(),
                    "end_date": bt.end_date.isoformat(),
                    "total_trades": bt.total_trades,
                    "win_rate": float(bt.win_rate) if bt.win_rate else 0,
                    "total_return_pct": float(bt.total_return_pct) if bt.total_return_pct else 0,
                    "profit_factor": float(bt.profit_factor) if bt.profit_factor else 0,
                    "sharpe_ratio": float(bt.sharpe_ratio) if bt.sharpe_ratio else 0,
                    "max_drawdown": float(bt.max_drawdown) if bt.max_drawdown else 0,
                    "created_at": bt.created_at.isoformat()
                }
                for bt in backtests
            ]
        }
    except Exception as e:
        logger.error("Failed to get backtest results", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve backtest results: {str(e)}"
        )


@router.get("/backtest-results/{backtest_id}")
async def get_backtest_result_details(
    backtest_id: str,
    include_trades: bool = Query(True, description="Include detailed trade records"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
) -> dict:
    """
    Get detailed backtest result including all individual trades.
    
    Returns complete backtest data including:
    - All 42 (or more) individual trades
    - Entry and exit prices/times
    - Position type (LONG/SHORT)
    - Stop loss and take profit levels
    - Exit reason (TAKE_PROFIT, STOP_LOSS, MANUAL, BACKTEST_END)
    - PnL and outcome (WIN/LOSS/BREAKEVEN)
    """
    try:
        # Convert string ID to UUID if needed
        try:
            bt_uuid = UUID(backtest_id)
        except ValueError:
            # Try finding by strategy_id if UUID fails
            query = select(BacktestResult).where(
                and_(
                    BacktestResult.strategy_id == backtest_id,
                    BacktestResult.user_id == current_user.id
                )
            ).order_by(desc(BacktestResult.created_at)).limit(1)
        else:
            query = select(BacktestResult).where(
                and_(
                    BacktestResult.id == bt_uuid,
                    BacktestResult.user_id == current_user.id
                )
            )
        
        result = await db.execute(query)
        backtest = result.scalar_one_or_none()
        
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest result not found"
            )
        
        # Extract detailed trades from execution_params
        closed_trades = []
        if backtest.execution_params and isinstance(backtest.execution_params, dict):
            closed_trades = backtest.execution_params.get('closed_trades', [])
        
        # Fallback to trade_log if closed_trades not available
        if not closed_trades and backtest.trade_log:
            # Convert legacy format if needed
            closed_trades = backtest.trade_log if isinstance(backtest.trade_log, list) else []
        
        response = {
            "success": True,
            "backtest_id": str(backtest.id),
            "strategy_id": backtest.strategy_id,
            "strategy_name": backtest.strategy_name,
            "start_date": backtest.start_date.isoformat(),
            "end_date": backtest.end_date.isoformat(),
            "period_days": (backtest.end_date - backtest.start_date).days,
            "initial_capital": float(backtest.initial_capital),
            "final_capital": float(backtest.final_capital),
            "total_return": float(backtest.total_return) if backtest.total_return else 0,
            "total_return_pct": float(backtest.total_return_pct) if backtest.total_return_pct else 0,
            "total_trades": backtest.total_trades,
            "winning_trades": backtest.winning_trades,
            "losing_trades": backtest.losing_trades,
            "win_rate": float(backtest.win_rate) if backtest.win_rate else 0,
            "profit_factor": float(backtest.profit_factor) if backtest.profit_factor else 0,
            "sharpe_ratio": float(backtest.sharpe_ratio) if backtest.sharpe_ratio else 0,
            "max_drawdown": float(backtest.max_drawdown) if backtest.max_drawdown else 0,
            "symbols": backtest.symbols if isinstance(backtest.symbols, list) else [],
            "data_source": backtest.data_source,
            "created_at": backtest.created_at.isoformat()
        }
        
        if include_trades:
            response["trades"] = closed_trades
            response["total_trades_detailed"] = len(closed_trades)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get backtest result details", error=str(e), backtest_id=backtest_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve backtest details: {str(e)}"
        )

