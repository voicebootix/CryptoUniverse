"""
Trading Strategies API Endpoints - Enterprise Grade

Connects the sophisticated TradingStrategiesService with the UI.
Handles strategy activation, configuration, execution, and monitoring
for the 25+ professional trading strategies.

Real strategy execution with user exchange integration - no mock data.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.core.config import get_settings
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.trading import TradingStrategy, Trade, Position
from app.models.exchange import ExchangeAccount
from app.models.credit import CreditAccount, CreditTransaction
from app.services.trading_strategies import trading_strategies_service
from app.services.trade_execution import TradeExecutionService
from app.services.strategy_marketplace_service import strategy_marketplace_service
from app.services.rate_limit import rate_limiter

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()

# Initialize services
trade_executor = TradeExecutionService()


# Request/Response Models
class StrategyExecuteRequest(BaseModel):
    function: str  # Strategy function name (e.g., "spot_momentum_strategy", "futures_trade")
    symbol: str = "BTC/USDT"
    parameters: Optional[Dict[str, Any]] = None
    simulation_mode: bool = True
    
    @field_validator('function')
    @classmethod
    def validate_function(cls, v):
        # List of available strategy functions from your TradingStrategiesService
        available_functions = [
            # Derivatives
            "futures_trade", "options_trade", "complex_strategy", "perpetual_trade",
            "leverage_position", "margin_status", "funding_arbitrage", "hedge_position",
            
            # Spot Algorithms  
            "spot_momentum_strategy", "spot_mean_reversion", "spot_breakout_strategy",
            
            # Algorithmic Trading
            "algorithmic_trading", "pairs_trading", "statistical_arbitrage",
            "market_making", "scalping_strategy", "swing_trading",
            
            # Risk & Portfolio
            "position_management", "risk_management", "portfolio_optimization",
            "strategy_performance"
        ]
        
        if v not in available_functions:
            raise ValueError(f"Strategy function must be one of: {available_functions}")
        return v


class StrategyConfigRequest(BaseModel):
    strategy_name: str
    parameters: Dict[str, Any]
    risk_parameters: Dict[str, Any]
    entry_conditions: Dict[str, Any]
    exit_conditions: Dict[str, Any]
    target_symbols: List[str] = ["BTC", "ETH", "SOL"]
    target_exchanges: List[str] = ["binance"]
    max_positions: int = 1
    max_risk_per_trade: float = 2.0
    is_simulation: bool = True


class StrategyResponse(BaseModel):
    strategy_id: str
    name: str
    status: str
    is_active: bool
    total_trades: int
    winning_trades: int
    win_rate: float
    total_pnl: Decimal
    sharpe_ratio: Optional[float]
    created_at: datetime
    last_executed_at: Optional[datetime]


class StrategyExecutionResponse(BaseModel):
    success: bool
    strategy_function: str
    execution_result: Dict[str, Any]
    timestamp: datetime
    credits_used: int = 0


# Strategy Management Endpoints
@router.get("/list", response_model=List[StrategyResponse])
async def get_user_strategies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get user's configured trading strategies."""
    
    await rate_limiter.check_rate_limit(
        key="strategies:list",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Get user's trading strategies from database
        stmt = select(TradingStrategy).where(
            TradingStrategy.user_id == current_user.id
        ).order_by(desc(TradingStrategy.created_at))
        
        result = await db.execute(stmt)
        strategies = result.scalars().all()
        
        # Transform to response format
        strategy_list = []
        for strategy in strategies:
            strategy_list.append(StrategyResponse(
                strategy_id=str(strategy.id),
                name=strategy.name,
                status="active" if strategy.is_active else "inactive",
                is_active=strategy.is_active,
                total_trades=strategy.total_trades,
                winning_trades=strategy.winning_trades,
                win_rate=strategy.win_rate,
                total_pnl=strategy.total_pnl,
                sharpe_ratio=float(strategy.sharpe_ratio) if strategy.sharpe_ratio else None,
                created_at=strategy.created_at,
                last_executed_at=strategy.last_executed_at
            ))
        
        return strategy_list
        
    except Exception as e:
        logger.error("Failed to get user strategies", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strategies: {str(e)}"
        )


@router.post("/execute", response_model=StrategyExecutionResponse)
async def execute_strategy(
    request: StrategyExecuteRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Execute a specific trading strategy function."""
    
    await rate_limiter.check_rate_limit(
        key="strategies:execute",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )
    
    logger.info(
        "Strategy execution request",
        user_id=str(current_user.id),
        function=request.function,
        symbol=request.symbol,
        simulation=request.simulation_mode
    )
    
    try:
        # Check if user has exchange accounts for trading
        if not request.simulation_mode:
            stmt = select(ExchangeAccount).where(
                and_(
                    ExchangeAccount.user_id == current_user.id,
                    ExchangeAccount.status == "active",
                    ExchangeAccount.trading_enabled == True
                )
            )
            result = await db.execute(stmt)
            exchange_accounts = result.scalars().all()
            
            if not exchange_accounts:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active exchange accounts found. Connect an exchange first."
                )
        
        # Check credits for real trading
        credits_required = 1  # Base cost for strategy execution
        if not request.simulation_mode:
            from sqlalchemy import select
            credit_stmt = select(CreditAccount).where(CreditAccount.user_id == current_user.id)
            credit_result = await db.execute(credit_stmt)
            credit_account = credit_result.scalar_one_or_none()
            
            if not credit_account or credit_account.available_credits < credits_required:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Insufficient credits. Required: {credits_required}, Available: {credit_account.available_credits if credit_account else 0}"
                )
        
        # Execute strategy using your TradingStrategiesService
        execution_result = await trading_strategies_service.execute_strategy(
            function=request.function,
            symbol=request.symbol,
            parameters=request.parameters or {},
            user_id=str(current_user.id),
            simulation_mode=request.simulation_mode
        )
        
        if not execution_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Strategy execution failed: {execution_result.get('error', 'Unknown error')}"
            )
        
        # Deduct credits for real execution
        credits_used = 0
        if not request.simulation_mode and execution_result.get("success"):
            credit_account.available_credits -= credits_required
            credit_account.total_used_credits += credits_required
            credits_used = credits_required
            
            # Record credit transaction
            credit_tx = CreditTransaction(
                user_id=current_user.id,
                amount=-credits_required,
                transaction_type="strategy_execution",
                description=f"Strategy: {request.function} on {request.symbol}",
                reference_id=execution_result.get("execution_id")
            )
            db.add(credit_tx)
            await db.commit()
        
        # If strategy generated trades, execute them
        if execution_result.get("trade_signals"):
            background_tasks.add_task(
                execute_strategy_trades,
                execution_result["trade_signals"],
                str(current_user.id),
                request.simulation_mode
            )
        
        return StrategyExecutionResponse(
            success=execution_result["success"],
            strategy_function=request.function,
            execution_result=execution_result,
            timestamp=datetime.utcnow(),
            credits_used=credits_used
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Strategy execution failed", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strategy execution failed: {str(e)}"
        )


@router.post("/configure")
async def configure_strategy(
    request: StrategyConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Configure and save a new trading strategy."""
    
    await rate_limiter.check_rate_limit(
        key="strategies:configure",
        limit=10,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Create new strategy configuration
        from app.models.trading import StrategyType
        
        strategy = TradingStrategy(
            user_id=current_user.id,
            name=request.strategy_name,
            description=f"Custom strategy: {request.strategy_name}",
            strategy_type=StrategyType.ALGORITHMIC,
            parameters=request.parameters,
            risk_parameters=request.risk_parameters,
            entry_conditions=request.entry_conditions,
            exit_conditions=request.exit_conditions,
            target_symbols=request.target_symbols,
            target_exchanges=request.target_exchanges,
            max_positions=request.max_positions,
            max_risk_per_trade=Decimal(str(request.max_risk_per_trade)),
            is_simulation=request.is_simulation,
            is_active=False  # User needs to activate manually
        )
        
        db.add(strategy)
        await db.commit()
        await db.refresh(strategy)
        
        logger.info(
            "Strategy configured",
            user_id=str(current_user.id),
            strategy_id=str(strategy.id),
            strategy_name=request.strategy_name
        )
        
        return {
            "success": True,
            "strategy_id": str(strategy.id),
            "message": f"Strategy '{request.strategy_name}' configured successfully"
        }
        
    except Exception as e:
        logger.error("Strategy configuration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure strategy: {str(e)}"
        )


@router.post("/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Activate a configured trading strategy."""
    
    await rate_limiter.check_rate_limit(
        key="strategies:activate",
        limit=10,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Get strategy
        stmt = select(TradingStrategy).where(
            and_(
                TradingStrategy.id == strategy_id,
                TradingStrategy.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        # Check if user has exchange accounts for non-simulation strategies
        if not strategy.is_simulation:
            exchange_stmt = select(ExchangeAccount).where(
                and_(
                    ExchangeAccount.user_id == current_user.id,
                    ExchangeAccount.status == "active",
                    ExchangeAccount.trading_enabled == True
                )
            )
            exchange_result = await db.execute(exchange_stmt)
            exchanges = exchange_result.scalars().all()
            
            if not exchanges:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active exchange accounts found for live trading"
                )
        
        # Activate strategy
        strategy.is_active = True
        strategy.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info(
            "Strategy activated",
            user_id=str(current_user.id),
            strategy_id=strategy_id,
            strategy_name=strategy.name,
            simulation=strategy.is_simulation
        )
        
        return {
            "success": True,
            "message": f"Strategy '{strategy.name}' activated successfully",
            "is_simulation": strategy.is_simulation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Strategy activation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate strategy: {str(e)}"
        )


@router.post("/{strategy_id}/deactivate")
async def deactivate_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Deactivate a trading strategy."""
    
    try:
        # Get and deactivate strategy
        stmt = select(TradingStrategy).where(
            and_(
                TradingStrategy.id == strategy_id,
                TradingStrategy.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        strategy.is_active = False
        strategy.updated_at = datetime.utcnow()
        await db.commit()
        
        return {
            "success": True,
            "message": f"Strategy '{strategy.name}' deactivated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Strategy deactivation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate strategy: {str(e)}"
        )


@router.get("/marketplace")
async def get_strategy_marketplace(
    current_user: User = Depends(get_current_user),
    include_ai: bool = True,
    include_community: bool = True
):
    """Get unified strategy marketplace with AI strategies and community strategies."""
    
    await rate_limiter.check_rate_limit(
        key="strategies:marketplace",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Get marketplace strategies using the new unified service
        marketplace_result = await strategy_marketplace_service.get_marketplace_strategies(
            user_id=str(current_user.id),
            include_ai_strategies=include_ai,
            include_community_strategies=include_community
        )
        
        if not marketplace_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=marketplace_result.get("error", "Failed to get marketplace strategies")
            )
        
        return marketplace_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Strategy marketplace retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strategy marketplace: {str(e)}"
        )


@router.post("/purchase")
async def purchase_strategy_access(
    strategy_id: str,
    subscription_type: str = "monthly",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Purchase access to strategy using credits."""
    
    await rate_limiter.check_rate_limit(
        key="strategies:purchase",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        purchase_result = await strategy_marketplace_service.purchase_strategy_access(
            user_id=str(current_user.id),
            strategy_id=strategy_id,
            subscription_type=subscription_type
        )
        
        if not purchase_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=purchase_result.get("error", "Strategy purchase failed")
            )
        
        return purchase_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Strategy purchase failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strategy purchase failed: {str(e)}"
        )


@router.get("/my-portfolio")
async def get_user_strategy_portfolio(
    current_user: User = Depends(get_current_user)
):
    """Get user's purchased strategy portfolio."""
    
    try:
        portfolio_result = await strategy_marketplace_service.get_user_strategy_portfolio(
            user_id=str(current_user.id)
        )
        
        return portfolio_result
        
    except Exception as e:
        logger.error("Failed to get user strategy portfolio", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strategy portfolio: {str(e)}"
        )


@router.get("/available")
async def get_available_strategies(
    current_user: User = Depends(get_current_user)
):
    """Get list of available strategy functions with descriptions (legacy endpoint)."""
    
    # Your 25+ strategy functions with descriptions (now integrated with marketplace)
    available_strategies = {
        # Derivatives Trading
        "futures_trade": {
            "name": "Futures Trading",
            "category": "derivatives",
            "description": "Advanced futures contract trading with leverage management",
            "risk_level": "High",
            "min_capital": 5000,
            "parameters": ["leverage", "position_size", "stop_loss"]
        },
        "options_trade": {
            "name": "Options Trading", 
            "category": "derivatives",
            "description": "Sophisticated options strategies with Greeks calculation",
            "risk_level": "High",
            "min_capital": 10000,
            "parameters": ["strike_price", "expiry", "strategy_type"]
        },
        "complex_strategy": {
            "name": "Complex Derivatives",
            "category": "derivatives", 
            "description": "Multi-leg derivatives strategies (spreads, straddles, etc.)",
            "risk_level": "Very High",
            "min_capital": 25000,
            "parameters": ["strategy_type", "legs", "risk_profile"]
        },
        
        # Spot Trading
        "spot_momentum_strategy": {
            "name": "Spot Momentum",
            "category": "spot",
            "description": "Momentum-based spot trading with trend following",
            "risk_level": "Medium",
            "min_capital": 1000,
            "parameters": ["timeframe", "momentum_threshold", "position_size"]
        },
        "spot_mean_reversion": {
            "name": "Mean Reversion",
            "category": "spot",
            "description": "Trade on price reversals to statistical mean",
            "risk_level": "Medium",
            "min_capital": 1000,
            "parameters": ["lookback_period", "deviation_threshold", "position_size"]
        },
        "spot_breakout_strategy": {
            "name": "Breakout Trading",
            "category": "spot",
            "description": "Trade breakouts from support/resistance levels",
            "risk_level": "Medium-High",
            "min_capital": 2000,
            "parameters": ["breakout_threshold", "volume_confirmation", "position_size"]
        },
        
        # Algorithmic Trading
        "pairs_trading": {
            "name": "Pairs Trading",
            "category": "algorithmic",
            "description": "Statistical arbitrage between correlated assets",
            "risk_level": "Medium",
            "min_capital": 5000,
            "parameters": ["correlation_threshold", "spread_threshold", "hedge_ratio"]
        },
        "statistical_arbitrage": {
            "name": "Statistical Arbitrage",
            "category": "algorithmic",
            "description": "Systematic stat arb across crypto universe",
            "risk_level": "Medium-High",
            "min_capital": 10000,
            "parameters": ["lookback_window", "z_score_threshold", "rebalance_frequency"]
        },
        "market_making": {
            "name": "Market Making",
            "category": "algorithmic",
            "description": "Provide liquidity and capture bid-ask spread",
            "risk_level": "Medium",
            "min_capital": 15000,
            "parameters": ["spread_percentage", "order_size", "inventory_limits"]
        },
        "scalping_strategy": {
            "name": "Scalping",
            "category": "algorithmic",
            "description": "High-frequency scalping with micro-profit targeting",
            "risk_level": "High",
            "min_capital": 3000,
            "parameters": ["tick_size", "hold_time", "profit_target"]
        },
        
        # Risk & Portfolio Management
        "portfolio_optimization": {
            "name": "Portfolio Optimization",
            "category": "portfolio",
            "description": "Optimize portfolio allocation using modern portfolio theory",
            "risk_level": "Low-Medium",
            "min_capital": 5000,
            "parameters": ["rebalance_frequency", "target_allocation", "risk_tolerance"]
        },
        "risk_management": {
            "name": "Risk Management",
            "category": "portfolio",
            "description": "Dynamic risk assessment and position sizing",
            "risk_level": "Low",
            "min_capital": 1000,
            "parameters": ["var_threshold", "correlation_limit", "concentration_limit"]
        }
    }
    
    return {
        "success": True,
        "available_strategies": available_strategies,
        "total_count": len(available_strategies),
        "categories": list(set(s["category"] for s in available_strategies.values()))
    }


@router.get("/{strategy_id}/performance")
async def get_strategy_performance(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get detailed performance metrics for a strategy."""
    
    try:
        # Get strategy
        stmt = select(TradingStrategy).where(
            and_(
                TradingStrategy.id == strategy_id,
                TradingStrategy.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        # Get recent trades for this strategy
        trades_stmt = select(Trade).where(
            and_(
                Trade.strategy_id == strategy.id,
                Trade.user_id == current_user.id
            )
        ).order_by(desc(Trade.created_at)).limit(100)
        
        trades_result = await db.execute(trades_stmt)
        recent_trades = trades_result.scalars().all()
        
        # Calculate performance metrics
        total_pnl = sum(float(trade.profit_realized_usd) for trade in recent_trades)
        winning_trades = sum(1 for trade in recent_trades if trade.profit_realized_usd > 0)
        
        # Get performance data using your existing strategy performance function
        performance_result = await trading_strategies_service.strategy_performance(
            strategy_name=strategy.name,
            user_id=str(current_user.id)
        )
        
        return {
            "success": True,
            "strategy": {
                "id": str(strategy.id),
                "name": strategy.name,
                "type": strategy.strategy_type.value,
                "is_active": strategy.is_active,
                "total_trades": strategy.total_trades,
                "winning_trades": strategy.winning_trades,
                "win_rate": strategy.win_rate,
                "total_pnl": float(strategy.total_pnl),
                "sharpe_ratio": float(strategy.sharpe_ratio) if strategy.sharpe_ratio else None
            },
            "recent_trades": [
                {
                    "id": str(trade.id),
                    "symbol": trade.symbol,
                    "action": trade.action.value,
                    "quantity": float(trade.executed_quantity or trade.quantity),
                    "price": float(trade.executed_price or 0),
                    "pnl": float(trade.profit_realized_usd),
                    "executed_at": trade.executed_at.isoformat() if trade.executed_at else None
                }
                for trade in recent_trades[:20]
            ],
            "performance_analysis": performance_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get strategy performance", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance: {str(e)}"
        )


async def execute_strategy_trades(
    trade_signals: List[Dict[str, Any]],
    user_id: str,
    simulation_mode: bool
):
    """Background task to execute trades generated by strategy."""
    logger.info(
        "Executing strategy trades",
        user_id=user_id,
        signal_count=len(trade_signals),
        simulation=simulation_mode
    )
    
    for signal in trade_signals:
        try:
            # Execute each trade signal
            result = await trade_executor.execute_trade(
                signal,
                user_id,
                simulation_mode=simulation_mode
            )
            
            if result.get("success"):
                logger.info(
                    "Strategy trade executed",
                    user_id=user_id,
                    symbol=signal.get("symbol"),
                    action=signal.get("action")
                )
            else:
                logger.error(
                    "Strategy trade failed",
                    user_id=user_id,
                    error=result.get("error"),
                    signal=signal
                )
                
        except Exception as e:
            logger.error(
                "Strategy trade execution error",
                error=str(e),
                user_id=user_id,
                signal=signal
            )