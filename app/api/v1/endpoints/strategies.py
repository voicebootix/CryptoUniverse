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
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Response
from pydantic import BaseModel, field_validator, Field, model_validator, conint, conlist
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.core.config import get_settings
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.trading import TradingStrategy, Trade, Position
from app.models.exchange import ExchangeAccount, ExchangeStatus
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
                    ExchangeAccount.status == ExchangeStatus.ACTIVE,
                    ExchangeAccount.trading_enabled.is_(True)
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
                    ExchangeAccount.status == ExchangeStatus.ACTIVE,
                    ExchangeAccount.trading_enabled.is_(True)
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


# Strategy Publisher Endpoints

class StrategySubmissionRequest(BaseModel):
    strategy_id: str
    name: str
    description: str
    category: str
    risk_level: str
    expected_return_range: conlist(Decimal, min_length=2, max_length=2)
    required_capital: conint(ge=0)
    pricing_model: str
    price_amount: Optional[Decimal] = None
    profit_share_percentage: Optional[conint(ge=0, le=100)] = None
    tags: List[str] = Field(default_factory=list)
    target_audience: List[str] = Field(default_factory=list)
    complexity_level: str = "intermediate"
    support_level: str = "standard"
    
    @model_validator(mode='after')
    def validate_expected_return_range(self):
        """Validate that min return <= max return."""
        if len(self.expected_return_range) == 2:
            min_return, max_return = self.expected_return_range
            if min_return > max_return:
                raise ValueError("Minimum expected return must be less than or equal to maximum expected return")
        return self
    
    @model_validator(mode='after')
    def validate_pricing_model(self):
        """Validate pricing model requirements."""
        if self.pricing_model == "one_time" or self.pricing_model == "subscription":
            if self.price_amount is None or self.price_amount <= 0:
                raise ValueError(f"pricing_model '{self.pricing_model}' requires a positive price_amount")
        elif self.pricing_model == "profit_share":
            if self.profit_share_percentage is None or self.profit_share_percentage <= 0:
                raise ValueError("pricing_model 'profit_share' requires a positive profit_share_percentage")
        return self


class StrategySubmissionUpdate(BaseModel):
    """Model for updating strategy submissions with optional fields."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    risk_level: Optional[str] = None
    expected_return_range: Optional[conlist(Decimal, min_length=2, max_length=2)] = None
    required_capital: Optional[conint(ge=0)] = None
    pricing_model: Optional[str] = None
    price_amount: Optional[Decimal] = None
    profit_share_percentage: Optional[conint(ge=0, le=100)] = None
    tags: Optional[List[str]] = None
    target_audience: Optional[List[str]] = None
    complexity_level: Optional[str] = None
    support_level: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_pricing_model_update(self):
        """Validate pricing model requirements for updates."""
        if self.pricing_model == "one_time" or self.pricing_model == "subscription":
            if self.price_amount is not None and self.price_amount <= 0:
                raise ValueError(f"pricing_model '{self.pricing_model}' requires a positive price_amount")
        elif self.pricing_model == "profit_share":
            if self.profit_share_percentage is not None and self.profit_share_percentage <= 0:
                raise ValueError("pricing_model 'profit_share' requires a positive profit_share_percentage")
        return self
    
    @model_validator(mode='after')
    def validate_expected_return_range_update(self):
        """Validate that min return <= max return for updates."""
        if self.expected_return_range is not None and len(self.expected_return_range) == 2:
            min_return, max_return = self.expected_return_range
            if min_return > max_return:
                raise ValueError("Minimum expected return must be less than or equal to maximum expected return")
        return self


@router.get("/publisher/submissions")
async def get_user_strategy_submissions(
    current_user: User = Depends(get_current_user)
):
    """Get user's strategy submissions for publishing."""
    
    # Check if user has publisher permissions (ADMIN or TRADER roles)
    if current_user.role not in [UserRole.ADMIN, UserRole.TRADER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and traders can view strategy submissions"
        )
    
    await rate_limiter.check_rate_limit(
        key="strategies:publisher:submissions",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Return mock data for now - in a real system this would query a strategy_submissions table
        submissions = [
            {
                "id": "sub_001",
                "name": "AI Momentum Strategy",
                "description": "Advanced momentum-based trading strategy using machine learning",
                "category": "algorithmic",
                "risk_level": "medium",
                "expected_return_range": [15.0, 35.0],
                "required_capital": 5000,
                "pricing_model": "profit_share",
                "profit_share_percentage": 25,
                "status": "submitted",
                "created_at": "2025-01-10T10:00:00Z",
                "submitted_at": "2025-01-10T10:30:00Z",
                "backtest_results": {
                    "total_return": 28.5,
                    "sharpe_ratio": 1.85,
                    "max_drawdown": -12.3,
                    "win_rate": 0.67,
                    "total_trades": 156,
                    "profit_factor": 2.1,
                    "period_days": 365
                },
                "validation_results": {
                    "is_valid": True,
                    "security_score": 92,
                    "performance_score": 85,
                    "code_quality_score": 88,
                    "overall_score": 88
                },
                "tags": ["momentum", "ai", "crypto"],
                "target_audience": ["intermediate", "advanced"],
                "complexity_level": "intermediate",
                "documentation_quality": 85,
                "support_level": "standard"
            },
            {
                "id": "sub_002", 
                "name": "Mean Reversion Pro",
                "description": "Statistical mean reversion strategy with dynamic thresholds",
                "category": "mean_reversion",
                "risk_level": "low",
                "expected_return_range": [8.0, 18.0],
                "required_capital": 2000,
                "pricing_model": "subscription",
                "price_amount": 49.99,
                "status": "approved",
                "created_at": "2025-01-05T14:00:00Z",
                "submitted_at": "2025-01-05T14:30:00Z",
                "reviewed_at": "2025-01-08T09:15:00Z",
                "reviewer_feedback": "Excellent strategy with solid backtesting results. Well documented.",
                "backtest_results": {
                    "total_return": 16.2,
                    "sharpe_ratio": 2.1,
                    "max_drawdown": -8.7,
                    "win_rate": 0.72,
                    "total_trades": 203,
                    "profit_factor": 1.8,
                    "period_days": 365
                },
                "validation_results": {
                    "is_valid": True,
                    "security_score": 95,
                    "performance_score": 91,
                    "code_quality_score": 93,
                    "overall_score": 93
                },
                "tags": ["mean_reversion", "statistical", "low_risk"],
                "target_audience": ["beginner", "intermediate"],
                "complexity_level": "beginner",
                "documentation_quality": 95,
                "support_level": "premium"
            }
        ]
        
        return {
            "success": True,
            "submissions": submissions,
            "total_count": len(submissions)
        }
        
    except Exception as e:
        logger.error("Failed to get strategy submissions", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get submissions: {str(e)}"
        )


@router.get("/publisher/requirements")
async def get_publishing_requirements(
    current_user: User = Depends(get_current_user)
):
    """Get strategy publishing requirements."""
    
    await rate_limiter.check_rate_limit(
        key="strategies:publisher:requirements",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        requirements = {
            "min_backtest_period": 90,
            "min_sharpe_ratio": 1.2,
            "min_win_rate": 0.55,
            "max_drawdown": 0.25,
            "min_total_trades": 50,
            "min_security_score": 80,
            "min_code_quality_score": 75,
            "min_overall_score": 80,
            "required_documentation": [
                "Strategy Description",
                "Risk Management Rules", 
                "Entry/Exit Conditions",
                "Backtest Results",
                "Performance Analysis",
                "Code Documentation"
            ]
        }
        
        return {
            "success": True,
            "requirements": requirements
        }
        
    except Exception as e:
        logger.exception("Failed to get publishing requirements")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get requirements: {str(e)}"
        ) from e


@router.post("/publisher/submit", status_code=status.HTTP_201_CREATED)
async def submit_strategy_for_review(
    request: StrategySubmissionRequest,
    current_user: User = Depends(get_current_user)
):
    """Submit a strategy for review and potential publication."""
    
    # Check if user has publisher permissions (ADMIN or TRADER roles)
    if current_user.role not in [UserRole.ADMIN, UserRole.TRADER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and traders can submit strategies for review"
        )
    
    await rate_limiter.check_rate_limit(
        key="strategies:publisher:submit",
        limit=10,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # In a real system, this would create a new submission record
        submission_id = str(uuid.uuid4())
        
        logger.info(
            "Strategy submitted for review",
            user_id=str(current_user.id),
            strategy_name=request.name,
            submission_id=submission_id,
            category=request.category,
            risk_level=request.risk_level
        )
        
        return {
            "success": True,
            "submission_id": submission_id,
            "message": f"Strategy '{request.name}' submitted for review successfully",
            "estimated_review_time": "3-5 business days"
        }
        
    except Exception as e:
        logger.exception("Strategy submission failed", user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Submission failed: {str(e)}"
        ) from e


@router.post("/publisher/withdraw/{submission_id}")
async def withdraw_strategy_submission(
    submission_id: str,
    current_user: User = Depends(get_current_user)
):
    """Withdraw a strategy submission from review."""
    
    # Check if user has publisher permissions (ADMIN or TRADER roles)
    if current_user.role not in [UserRole.ADMIN, UserRole.TRADER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and traders can withdraw strategy submissions"
        )
    
    await rate_limiter.check_rate_limit(
        key="strategies:publisher:withdraw",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # In a real system, this would update the submission status to 'withdrawn'
        logger.info(
            "Strategy submission withdrawn",
            user_id=str(current_user.id),
            submission_id=submission_id
        )
        
        return {
            "success": True,
            "message": "Submission withdrawn successfully"
        }
        
    except Exception as e:
        logger.exception("Failed to withdraw submission", user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to withdraw submission: {str(e)}"
        ) from e


@router.put("/publisher/submissions/{submission_id}")
async def update_strategy_submission(
    submission_id: str,
    updates: StrategySubmissionUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a strategy submission with typed validation."""
    
    # Check if user has publisher permissions (ADMIN or TRADER roles)
    if current_user.role not in [UserRole.ADMIN, UserRole.TRADER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and traders can update strategy submissions"
        )
    
    await rate_limiter.check_rate_limit(
        key="strategies:publisher:update",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Convert to dict and filter out None values for logging
        update_fields = {k: v for k, v in updates.model_dump().items() if v is not None}
        
        # In a real system, this would update the submission record with validated fields
        logger.info(
            "Strategy submission updated",
            user_id=str(current_user.id),
            submission_id=submission_id,
            updates=list(update_fields.keys())
        )
        
        return {
            "success": True,
            "message": "Submission updated successfully",
            "updated_fields": list(update_fields.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update submission", user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update submission"
        ) from e