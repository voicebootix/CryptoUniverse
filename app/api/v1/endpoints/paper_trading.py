"""
Paper Trading API Endpoints - Risk-Free Trading Experience

Provides comprehensive paper trading functionality for users to:
- Practice trading strategies without risk
- Build confidence before live trading
- Analyze "what if" scenarios
- Compare paper vs live performance
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.services.paper_trading_engine import get_paper_trading_engine, PaperTradingEngine
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


class PaperTradeRequest(BaseModel):
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    strategy_used: str
    order_type: str = "market"


class WhatIfAnalysisRequest(BaseModel):
    strategy: str
    symbol: str
    timeframe_days: int = 30


@router.post("/setup")
async def setup_paper_trading(
    current_user: User = Depends(get_current_user),
    paper_engine: PaperTradingEngine = Depends(get_paper_trading_engine)
):
    """Setup paper trading account for user."""
    
    try:
        result = await paper_engine.setup_paper_trading_account(str(current_user.id))
        
        if result.get("success"):
            portfolio = result.get("virtual_portfolio") or result.get("portfolio") or {}

            return {
                "success": True,
                "message": result.get("message", "Paper trading account created successfully"),
                "virtual_portfolio": portfolio
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to setup paper trading")
            )
            
    except Exception as e:
        logger.error("Paper trading setup failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Paper trading setup failed: {str(e)}"
        )


@router.post("/execute")
async def execute_paper_trade(
    request: PaperTradeRequest,
    current_user: User = Depends(get_current_user),
    paper_engine: PaperTradingEngine = Depends(get_paper_trading_engine)
):
    """Execute a paper trade."""
    
    try:
        result = await paper_engine.execute_paper_trade(
            user_id=str(current_user.id),
            symbol=request.symbol.upper(),
            side=request.side.lower(),
            quantity=request.quantity,
            strategy_used=request.strategy_used,
            order_type=request.order_type
        )
        
        if result.get("success"):
            return {
                "success": True,
                "paper_trade": result["paper_trade"],
                "virtual_portfolio": result["virtual_portfolio"],
                "message": result["message"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Paper trade execution failed")
            )
            
    except Exception as e:
        logger.error("Paper trade execution failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Paper trade failed: {str(e)}"
        )


@router.get("/performance")
async def get_paper_trading_performance(
    current_user: User = Depends(get_current_user),
    paper_engine: PaperTradingEngine = Depends(get_paper_trading_engine)
):
    """Get comprehensive paper trading performance."""
    
    try:
        result = await paper_engine.get_paper_trading_performance(str(current_user.id))
        
        if result.get("success"):
            return {
                "success": True,
                "paper_portfolio": result["paper_portfolio"],
                "confidence_metrics": result["confidence_metrics"],
                "ready_for_live_trading": result["ready_for_live_trading"],
                "live_trading_recommendation": result["live_trading_recommendation"]
            }
        else:
            if result.get("needs_setup"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Paper trading account not found. Please setup first."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.get("error", "Failed to get paper trading performance")
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Performance analysis failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Performance analysis failed: {str(e)}"
        )


@router.get("/stats")
async def get_paper_trading_stats(
    current_user: User = Depends(get_current_user),
    paper_engine: PaperTradingEngine = Depends(get_paper_trading_engine)
):
    """Return simplified paper trading statistics for dashboard views."""

    try:
        result = await paper_engine.get_paper_trading_performance(str(current_user.id))

        if result.get("success"):
            portfolio = result.get("paper_portfolio", {})
            performance_metrics = portfolio.get("performance_metrics", {})

            stats = {
                "total_trades": performance_metrics.get("total_trades", 0),
                "win_rate": performance_metrics.get("win_rate", 0),
                "total_profit": performance_metrics.get("total_profit_loss", 0),
                "best_trade": performance_metrics.get("best_trade", 0),
                "worst_trade": performance_metrics.get("worst_trade", 0)
            }

            return {
                "success": True,
                "virtual_portfolio": portfolio,
                "stats": stats,
                "confidence_metrics": result.get("confidence_metrics", {}),
                "ready_for_live_trading": result.get("ready_for_live_trading", False),
                "live_trading_recommendation": result.get("live_trading_recommendation", {})
            }

        if result.get("needs_setup"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paper trading account not found. Please setup first."
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to get paper trading stats")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Paper trading stats failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Paper trading stats failed: {str(e)}"
        )


@router.post("/reset")
async def reset_paper_trading_account(
    current_user: User = Depends(get_current_user),
    paper_engine: PaperTradingEngine = Depends(get_paper_trading_engine)
):
    """Reset the user's paper trading account to the initial balance."""

    try:
        result = await paper_engine.reset_paper_trading_account(str(current_user.id))

        if result.get("success"):
            return {
                "success": True,
                "message": result.get("message", "Paper trading account reset successfully"),
                "virtual_portfolio": result.get("virtual_portfolio", {})
            }

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to reset paper trading account")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Paper trading reset failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Paper trading reset failed: {str(e)}"
        )


@router.post("/what-if-analysis")
async def run_what_if_analysis(
    request: WhatIfAnalysisRequest,
    current_user: User = Depends(get_current_user),
    paper_engine: PaperTradingEngine = Depends(get_paper_trading_engine)
):
    """Run 'what if' analysis to show potential profits."""
    
    try:
        result = await paper_engine.run_paper_trading_what_if_analysis(
            user_id=str(current_user.id),
            strategy=request.strategy,
            symbol=request.symbol.upper(),
            timeframe_days=request.timeframe_days
        )
        
        if result.get("success"):
            return {
                "success": True,
                "what_if_analysis": result["what_if_analysis"],
                "simulated_trades": result["simulated_trades"],
                "performance_summary": result["performance_summary"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "What-if analysis failed")
            )
            
    except Exception as e:
        logger.error("What-if analysis failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"What-if analysis failed: {str(e)}"
        )


@router.get("/vs-live-comparison")
async def get_paper_vs_live_comparison(
    current_user: User = Depends(get_current_user),
    paper_engine: PaperTradingEngine = Depends(get_paper_trading_engine)
):
    """Compare paper trading performance with live trading projections."""
    
    try:
        result = await paper_engine.get_paper_vs_live_comparison(str(current_user.id))
        
        if result.get("success"):
            return {
                "success": True,
                "comparison": result["comparison"],
                "transition_readiness": result["transition_readiness"],
                "confidence_score": result["confidence_score"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Comparison analysis failed")
            )
            
    except Exception as e:
        logger.error("Paper vs live comparison failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison failed: {str(e)}"
        )