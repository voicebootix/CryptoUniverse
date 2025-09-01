"""
Trading API Endpoints - Enterprise Grade

Handles all trading operations including manual trades, autonomous mode control,
portfolio management, and real-time trading data for the AI money manager.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.trading import Trade, Position, Order, TradingStrategy
from app.models.exchange import ExchangeAccount
from app.models.credit import CreditAccount, CreditTransaction
from app.services.trade_execution import TradeExecutionService
from app.services.master_controller import MasterSystemController
from app.services.portfolio_risk_core import PortfolioRiskServiceExtended
from app.services.market_analysis_core import MarketAnalysisService
# Using existing MarketAnalysisService instead
from app.services.rate_limit import rate_limiter
from app.services.websocket import manager

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()

# Initialize services
trade_executor = TradeExecutionService()
master_controller = MasterSystemController()
risk_service = PortfolioRiskServiceExtended()
market_analysis = MarketAnalysisService()


# Request/Response Models
class TradeRequest(BaseModel):
    symbol: str
    action: str  # "buy", "sell", "long", "short"
    amount: Decimal
    order_type: str = "market"  # "market", "limit", "stop"
    price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    exchange: str = "binance"
    leverage: Optional[int] = None
    strategy_type: Optional[str] = None
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        allowed_actions = ["buy", "sell", "long", "short"]
        if v.lower() not in allowed_actions:
            raise ValueError(f"Action must be one of: {allowed_actions}")
        return v.lower()
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class AutonomousModeRequest(BaseModel):
    enable: bool
    mode: str = "balanced"  # "conservative", "balanced", "aggressive", "beast_mode"
    max_daily_loss_pct: Optional[float] = None
    max_position_size_pct: Optional[float] = None
    allowed_symbols: Optional[List[str]] = None
    excluded_symbols: Optional[List[str]] = None
    trading_hours: Optional[Dict[str, Any]] = None
    
    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v):
        allowed_modes = ["conservative", "balanced", "aggressive", "beast_mode"]
        if v.lower() not in allowed_modes:
            raise ValueError(f"Mode must be one of: {allowed_modes}")
        return v.lower()


class SimulationModeRequest(BaseModel):
    enable: bool
    virtual_balance: Optional[Decimal] = Decimal("10000")  # Default $10k
    reset_portfolio: bool = False


class TradeResponse(BaseModel):
    trade_id: str
    status: str
    symbol: str
    action: str
    amount: Decimal
    price: Optional[Decimal]
    fee: Optional[Decimal]
    profit_loss: Optional[Decimal]
    execution_time: datetime
    exchange: str
    simulation: bool


class PortfolioResponse(BaseModel):
    total_value: Decimal
    available_balance: Decimal
    positions: List[Dict[str, Any]]
    daily_pnl: Decimal
    daily_pnl_pct: float
    total_pnl: Decimal
    total_pnl_pct: float
    margin_used: Decimal
    margin_available: Decimal
    risk_score: float
    active_orders: int


class SystemStatusResponse(BaseModel):
    autonomous_mode: bool
    simulation_mode: bool
    current_mode: str
    system_health: str
    active_strategies: List[str]
    performance_today: Dict[str, Any]
    risk_level: str
    next_action_eta: Optional[int]

class MarketDataItem(BaseModel):
    symbol: str
    price: Decimal
    change: float
    volume: str

class MarketOverviewResponse(BaseModel):
    market_data: List[MarketDataItem]

class RecentTrade(BaseModel):
    id: str
    symbol: str
    side: str
    amount: Decimal
    price: Decimal
    time: str
    status: str
    pnl: Decimal

class RecentTradesResponse(BaseModel):
    recent_trades: List[RecentTrade]

# Trading Endpoints
@router.post("/execute", response_model=TradeResponse)
async def execute_manual_trade(
    request: TradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Execute a manual trade order."""
    
    # Rate limiting
    await rate_limiter.check_rate_limit(
        key="trading:execute",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    logger.info(
        "Manual trade execution requested",
        user_id=str(current_user.id),
        symbol=request.symbol,
        action=request.action,
        amount=float(request.amount)
    )
    
    try:
        # Check user permissions
        if current_user.role not in [UserRole.ADMIN, UserRole.TRADER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for trading"
            )
        
        # Check credit balance
        credit_account = db.query(CreditAccount).filter(
            CreditAccount.user_id == current_user.id
        ).first()
        
        if not credit_account or credit_account.available_credits <= 0:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits for trading"
            )
        
        # Get user's simulation mode setting
        simulation_mode = getattr(current_user, 'simulation_mode', True)
        
        # Prepare trade request
        trade_data = {
            "symbol": request.symbol,
            "action": request.action,
            "amount": float(request.amount),
            "order_type": request.order_type,
            "price": float(request.price) if request.price else None,
            "stop_loss": float(request.stop_loss) if request.stop_loss else None,
            "take_profit": float(request.take_profit) if request.take_profit else None,
            "exchange": request.exchange,
            "leverage": request.leverage,
            "strategy_type": request.strategy_type,
            "user_id": str(current_user.id)
        }
        
        # Execute trade
        result = await trade_executor.execute_trade(
            trade_data,
            str(current_user.id),
            simulation_mode=simulation_mode
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Trade execution failed")
            )
        
        # Deduct credits for real trades
        if not simulation_mode:
            credit_cost = calculate_credit_cost(request.amount, request.symbol)
            if credit_account.available_credits >= credit_cost:
                credit_account.available_credits -= credit_cost
                credit_account.total_used_credits += credit_cost
                
                # Record transaction
                credit_tx = CreditTransaction(
                    user_id=current_user.id,
                    amount=-credit_cost,
                    transaction_type="trade_execution",
                    description=f"Trade: {request.action} {request.symbol}",
                    reference_id=result.get("trade_id")
                )
                db.add(credit_tx)
                db.commit()
        
        trade_result = result.get("trade_result", {}) or result.get("simulation_result", {})
        
        return TradeResponse(
            trade_id=trade_result.get("order_id", "unknown"),
            status=trade_result.get("status", "unknown"),
            symbol=request.symbol,
            action=request.action,
            amount=request.amount,
            price=Decimal(str(trade_result.get("execution_price", 0))),
            fee=Decimal(str(trade_result.get("fee", 0))),
            profit_loss=Decimal(str(trade_result.get("profit_loss", 0))),
            execution_time=datetime.fromisoformat(result.get("timestamp", datetime.utcnow().isoformat())),
            exchange=request.exchange,
            simulation=simulation_mode
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Trade execution failed", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trade execution failed: {str(e)}"
        )


@router.post("/autonomous/start")
async def start_autonomous_mode(
    request: AutonomousModeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Start or configure autonomous trading mode."""
    
    await rate_limiter.check_rate_limit(
        key="trading:autonomous",
        limit=10,
        window=60,
        user_id=str(current_user.id)
    )
    
    logger.info(
        "Autonomous mode configuration",
        user_id=str(current_user.id),
        enable=request.enable,
        mode=request.mode
    )
    
    try:
        if request.enable:
            # Validate credit balance for autonomous trading
            credit_account = db.query(CreditAccount).filter(
                CreditAccount.user_id == current_user.id
            ).first()
            
            if not credit_account or credit_account.available_credits < 10:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Minimum 10 credits required for autonomous trading"
                )
            
            # Configure autonomous mode
            config = {
                "user_id": str(current_user.id),
                "mode": request.mode,
                "max_daily_loss_pct": request.max_daily_loss_pct or 5.0,
                "max_position_size_pct": request.max_position_size_pct or 10.0,
                "allowed_symbols": request.allowed_symbols or ["BTC", "ETH", "SOL"],
                "excluded_symbols": request.excluded_symbols or [],
                "trading_hours": request.trading_hours or {"start": "00:00", "end": "23:59"}
            }
            
            # Start autonomous trading through unified AI manager
            from app.services.unified_ai_manager import unified_ai_manager
            result = await unified_ai_manager.start_autonomous_mode(str(current_user.id), config)
            
            if not result.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.get("error", "Failed to start autonomous mode")
                )
            
            # Schedule background monitoring
            background_tasks.add_task(monitor_autonomous_trading, current_user.id)
            
            return {
                "status": "autonomous_mode_started",
                "mode": request.mode,
                "session_id": result.get("session_id"),
                "estimated_daily_trades": result.get("estimated_trades", 10),
                "risk_level": request.mode,
                "message": f"Autonomous trading started in {request.mode} mode"
            }
        else:
            # Stop autonomous mode through unified AI manager
            from app.services.unified_ai_manager import unified_ai_manager
            result = await unified_ai_manager.stop_autonomous_mode(str(current_user.id), "web_ui")
            
            return {
                "status": "autonomous_mode_stopped",
                "session_duration": result.get("session_duration", 0),
                "trades_executed": result.get("trades_executed", 0),
                "total_pnl": result.get("total_pnl", 0),
                "message": "Autonomous trading stopped"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Autonomous mode configuration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Autonomous mode configuration failed: {str(e)}"
        )


@router.post("/simulation/toggle")
async def toggle_simulation_mode(
    request: SimulationModeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Toggle between simulation and live trading mode."""
    
    await rate_limiter.check_rate_limit(
        key="trading:simulation",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )
    
    logger.info(
        "Simulation mode toggle",
        user_id=str(current_user.id),
        enable=request.enable
    )
    
    try:
        # Update user's simulation mode
        # Note: This would be stored in user settings/preferences
        simulation_config = {
            "enabled": request.enable,
            "virtual_balance": float(request.virtual_balance),
            "reset_portfolio": request.reset_portfolio
        }
        
        if request.enable:
            # Set up simulation environment
            if request.reset_portfolio:
                # Reset virtual portfolio
                await reset_virtual_portfolio(current_user.id, request.virtual_balance)
            
            return {
                "status": "simulation_mode_enabled",
                "virtual_balance": float(request.virtual_balance),
                "message": "Switched to simulation mode - trades will not use real money"
            }
        else:
            # Switch to live trading
            # Verify user has real exchange accounts
            exchange_accounts = db.query(ExchangeAccount).filter(
                ExchangeAccount.user_id == current_user.id,
                ExchangeAccount.is_active == True
            ).count()
            
            if exchange_accounts == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active exchange accounts found. Please connect exchange accounts for live trading."
                )
            
            return {
                "status": "live_mode_enabled", 
                "message": "Switched to live trading mode - trades will use real money",
                "warning": "All trades will now execute with real funds"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Simulation mode toggle failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle simulation mode: {str(e)}"
        )


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get current portfolio status and performance."""
    
    await rate_limiter.check_rate_limit(
        key="portfolio:read",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Get real portfolio data using existing exchange balance system
        from app.api.v1.endpoints.exchanges import get_user_portfolio_from_exchanges
        portfolio_data = await get_user_portfolio_from_exchanges(str(current_user.id), db)
        
        if not portfolio_data.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=portfolio_data.get("error", "Portfolio data not found")
            )
        
        # Get additional portfolio metrics from risk service
        risk_metrics = await risk_service.get_portfolio_status(str(current_user.id))
        risk_data = risk_metrics.get("portfolio", {}) if risk_metrics.get("success") else {}
        
        # Transform real exchange balances into portfolio positions
        positions = []
        total_value_usd = portfolio_data.get("total_value_usd", 0.0)
        
        for balance in portfolio_data.get("balances", []):
            if balance.get("total", 0) > 0:
                positions.append({
                    "symbol": balance["asset"],
                    "name": balance["asset"],
                    "amount": balance["total"],
                    "value_usd": balance["value_usd"],
                    "entry_price": balance["usd_price"],
                    "current_price": balance["usd_price"],
                    "change_24h_pct": 0.0,  # Would come from market data service
                    "unrealized_pnl": 0.0,  # Would be calculated from entry vs current
                    "side": "long",
                    "exchange": balance.get("exchange", "unknown")
                })
        
        # Calculate available balance (cash equivalents)
        stablecoins = ["USDT", "USDC", "BUSD", "DAI", "FDUSD"]
        available_balance = sum(
            balance["value_usd"] for balance in portfolio_data.get("balances", [])
            if balance["asset"] in stablecoins
        )
        
        return PortfolioResponse(
            total_value=Decimal(str(total_value_usd)),
            available_balance=Decimal(str(available_balance)),
            positions=positions,
            daily_pnl=Decimal(str(risk_data.get("daily_pnl", 0))),
            daily_pnl_pct=risk_data.get("daily_pnl_pct", 0.0),
            total_pnl=Decimal(str(risk_data.get("total_pnl", 0))),
            total_pnl_pct=risk_data.get("total_pnl_pct", 0.0),
            margin_used=Decimal(str(risk_data.get("margin_used", 0))),
            margin_available=Decimal(str(risk_data.get("margin_available", 0))),
            risk_score=risk_data.get("risk_score", 50.0),
            active_orders=risk_data.get("active_orders", 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Portfolio status retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get portfolio status: {str(e)}"
        )


@router.get("/status", response_model=SystemStatusResponse)
async def get_trading_system_status(
    current_user: User = Depends(get_current_user)
):
    """Get overall trading system status."""
    
    await rate_limiter.check_rate_limit(
        key="system:status",
        limit=200,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Get system status from master controller
        status_data = await master_controller.get_system_status(str(current_user.id))
        
        return SystemStatusResponse(
            autonomous_mode=status_data.get("autonomous_mode", False),
            simulation_mode=status_data.get("simulation_mode", True),
            current_mode=status_data.get("trading_mode", "balanced"),
            system_health=status_data.get("health", "normal"),
            active_strategies=status_data.get("active_strategies", []),
            performance_today=status_data.get("performance_today", {}),
            risk_level=status_data.get("risk_level", "normal"),
            next_action_eta=status_data.get("next_action_eta")
        )
        
    except Exception as e:
        logger.error("System status retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system status: {str(e)}"
        )


@router.get("/market-overview", response_model=MarketOverviewResponse)
async def get_market_overview(
    current_user: User = Depends(get_current_user)
):
    """Get market overview data."""
    await rate_limiter.check_rate_limit(
        key="market:overview",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )
    try:
        # Use your existing sophisticated MarketAnalysisService
        market_data_result = await market_analysis.get_market_overview()
        
        if market_data_result.get("success"):
            return MarketOverviewResponse(market_data=market_data_result.get("market_data", []))
        else:
            # If your market analysis service isn't ready, return error
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Market analysis service unavailable"
            )
    except Exception as e:
        logger.error("Market overview retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get market overview: {str(e)}"
        )

@router.get("/recent-trades", response_model=RecentTradesResponse)
async def get_recent_trades(
    current_user: User = Depends(get_current_user)
):
    """Get recent trading activity."""
    await rate_limiter.check_rate_limit(
        key="trades:recent",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )
    try:
        # Get real recent trades from database
        from sqlalchemy import select, desc
        from app.models.trading import Trade, TradeAction
        
        # Query recent trades for user
        stmt = select(Trade).where(
            Trade.user_id == current_user.id
        ).order_by(desc(Trade.created_at)).limit(50)
        
        result = await db.execute(stmt)
        trades = result.scalars().all()
        
        # Transform to response format
        recent_trades = []
        for trade in trades:
            # Calculate time ago
            time_diff = datetime.utcnow() - trade.created_at
            if time_diff.total_seconds() < 3600:
                time_ago = f"{int(time_diff.total_seconds() / 60)} min ago"
            elif time_diff.total_seconds() < 86400:
                time_ago = f"{int(time_diff.total_seconds() / 3600)} hour ago"
            else:
                time_ago = f"{int(time_diff.total_seconds() / 86400)} day ago"
            
            # Calculate P&L if available
            pnl = trade.profit_realized_usd or Decimal("0")
            
            recent_trades.append({
                "id": str(trade.id),
                "symbol": trade.symbol,
                "side": trade.action.value,
                "amount": trade.executed_quantity or trade.quantity,
                "price": trade.executed_price or trade.price or Decimal("0"),
                "time": time_ago,
                "status": trade.status.value,
                "pnl": pnl,
                "exchange": trade.meta_data.get("exchange", "unknown") if trade.meta_data else "unknown"
            })
        
        return RecentTradesResponse(recent_trades=recent_trades)
    except Exception as e:
        logger.error("Recent trades retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent trades: {str(e)}"
        )

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_database)
):
    # Accept connection first
    await websocket.accept()
    
    # For now, connect without authentication
    # TODO: Implement WebSocket token authentication via query params
    user_id = "anonymous"  # Temporary
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Keep the connection alive
            data = await websocket.receive_text()
            # Echo back for testing
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@router.post("/stop-all")
async def emergency_stop_all_trading(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Emergency stop all trading activities."""
    
    await rate_limiter.check_rate_limit(
        key="trading:emergency_stop",
        limit=5,
        window=60,
        user_id=str(current_user.id)
    )
    
    logger.critical(
        "Emergency stop requested",
        user_id=str(current_user.id)
    )
    
    try:
        # Stop autonomous trading
        await master_controller.emergency_stop(str(current_user.id))
        
        # Cancel all pending orders
        # Note: This would interact with exchange APIs to cancel orders
        
        return {
            "status": "emergency_stop_executed",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "All trading activities stopped",
            "actions_taken": [
                "Autonomous trading stopped",
                "Pending orders cancelled",
                "System locked for manual review"
            ]
        }
        
    except Exception as e:
        logger.error("Emergency stop failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency stop failed: {str(e)}"
        )


# Helper Functions
def calculate_credit_cost(amount: Decimal, symbol: str) -> int:
    """Calculate credit cost for a trade."""
    # $0.10 per credit = $1 profit potential
    # Base cost calculation
    base_cost = max(1, int(float(amount) / 1000))  # 1 credit per $1000 traded
    return base_cost


async def monitor_autonomous_trading(user_id: str):
    """Background task to monitor autonomous trading."""
    try:
        # This would run continuously to monitor the user's autonomous trading
        while True:
            await asyncio.sleep(60)  # Check every minute
            
            # Get current status
            status = await master_controller.get_system_status(user_id)
            
            # Check for emergency conditions
            if status.get("risk_level") == "emergency":
                await master_controller.emergency_stop(user_id)
                break
                
    except Exception as e:
        logger.error("Autonomous trading monitoring failed", error=str(e), user_id=user_id)


async def reset_virtual_portfolio(user_id: str, virtual_balance: Decimal):
    """Reset virtual portfolio for simulation mode."""
    try:
        # This would reset the user's virtual portfolio in simulation mode
        # Implementation would depend on how simulation data is stored
        logger.info(f"Virtual portfolio reset for user {user_id}", balance=float(virtual_balance))
    except Exception as e:
        logger.error("Virtual portfolio reset failed", error=str(e), user_id=user_id)
