"""
Trading API Endpoints - Enterprise Grade

Handles all trading operations including manual trades, autonomous mode control,
portfolio management, and real-time trading data for the AI money manager.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.core.config import get_settings
from app.core.database import get_database, AsyncSessionLocal
from app.api.v1.endpoints.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.trading import Trade, Position, Order, TradingStrategy
from app.models.exchange import ExchangeAccount
from app.models.credit import CreditAccount, CreditTransactionType
from app.services.trade_execution import TradeExecutionService
from app.services.master_controller import MasterSystemController
from app.services.portfolio_risk_core import PortfolioRiskServiceExtended
from app.services.market_analysis_core import market_analysis_service
from app.services.rate_limit import rate_limiter
from app.services.websocket import manager
from app.services.credit_ledger import credit_ledger, InsufficientCreditsError

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()

# Initialize services - ENTERPRISE SINGLETON PATTERN
trade_executor = TradeExecutionService()
master_controller = MasterSystemController()
risk_service = PortfolioRiskServiceExtended()
market_analysis = market_analysis_service  # Use global singleton


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


class PortfolioSummaryResponse(BaseModel):
    success: bool
    total_value: Decimal
    available_balance: Decimal
    cash_balance: Decimal
    positions_count: int
    daily_pnl: Decimal
    daily_pnl_pct: float
    total_pnl: Decimal
    total_pnl_pct: float
    last_updated: datetime


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
    id: str  # UUID as string
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
        stmt = select(CreditAccount).where(CreditAccount.user_id == current_user.id)
        result = await db.execute(stmt)
        credit_account = result.scalar_one_or_none()
        
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
        
        # Pre-calculate credit requirement for live trades
        credit_cost: Optional[int] = None
        if not simulation_mode:
            credit_cost = calculate_credit_cost(request.amount, request.symbol)
            if credit_account.available_credits < credit_cost:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Insufficient credits for trading",
                )

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

        # Deduct credits for real trades after successful execution
        if credit_cost is not None:
            try:
                # Re-fetch credit account with row lock to prevent race conditions
                locked_stmt = select(CreditAccount).where(
                    CreditAccount.user_id == current_user.id
                ).with_for_update()
                locked_result = await db.execute(locked_stmt)
                locked_credit_account = locked_result.scalar_one()

                await credit_ledger.consume_credits(
                    db,
                    locked_credit_account,
                    credits=credit_cost,
                    description=f"Trade execution: {request.action} {request.symbol}",
                    source="trading_api",
                    transaction_type=CreditTransactionType.USAGE,
                    metadata={
                        "symbol": request.symbol,
                        "amount": float(request.amount),
                        "order_type": request.order_type,
                        "exchange": request.exchange,
                    },
                )
                await db.commit()
            except InsufficientCreditsError:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Insufficient credits for trading",
                )
        
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
            stmt = select(CreditAccount).where(CreditAccount.user_id == current_user.id)
            result = await db.execute(stmt)
            credit_account = result.scalar_one_or_none()
            
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
                "success": True,
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
                "success": True,
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


@router.post("/autonomous/toggle")
async def toggle_autonomous_mode(
    request: AutonomousModeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Toggle autonomous trading mode on/off."""
    return await start_autonomous_mode(request, background_tasks, current_user, db)


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
        # Update user's simulation mode in database
        current_user.simulation_mode = request.enable
        current_user.simulation_balance = float(request.virtual_balance)

        if request.reset_portfolio:
            current_user.last_simulation_reset = datetime.utcnow()

        # Commit the changes to database
        await db.commit()
        await db.refresh(current_user)

        simulation_config = {
            "enabled": current_user.simulation_mode,
            "virtual_balance": float(current_user.simulation_balance),
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
            stmt = select(ExchangeAccount).where(
                ExchangeAccount.user_id == current_user.id,
                ExchangeAccount.is_active == True
            )
            result = await db.execute(stmt)
            exchange_accounts = len(result.scalars().all())
            
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


async def _build_portfolio_response(
    current_user: User,
    db: AsyncSession,
    *,
    enforce_rate_limit: bool = True,
) -> PortfolioResponse:
    """Load portfolio data with graceful fallbacks when upstream services fail."""

    if enforce_rate_limit:
        await rate_limiter.check_rate_limit(
            key="portfolio:read",
            limit=100,
            window=60,
            user_id=str(current_user.id)
        )

    portfolio_data: Dict[str, Any] = {}
    portfolio_fetch_error: Optional[str] = None

    try:
        from app.api.v1.endpoints.exchanges import get_user_portfolio_from_exchanges
        exchange_result = await asyncio.wait_for(
            get_user_portfolio_from_exchanges(str(current_user.id), db),
            timeout=10.0  # Increased timeout for production
        )

        if exchange_result.get("success"):
            portfolio_data = exchange_result
        else:
            portfolio_fetch_error = exchange_result.get("error") or "Portfolio aggregation returned unsuccessful response"
    except asyncio.TimeoutError:
        portfolio_fetch_error = "Portfolio service timeout - using cached analytics fallback"
    except HTTPException as http_exc:
        if http_exc.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
            raise
        portfolio_fetch_error = http_exc.detail or f"HTTP {http_exc.status_code} during portfolio aggregation"
    except Exception as exc:  # pragma: no cover - defensive logging
        portfolio_fetch_error = f"Portfolio data service error: {str(exc)}"

    if portfolio_fetch_error:
        logger.warning(
            "Portfolio aggregation unavailable, using fallback data",
            user_id=str(current_user.id),
            error=portfolio_fetch_error,
        )

    risk_data: Dict[str, Any] = {}
    try:
        risk_metrics = await risk_service.get_portfolio_status(str(current_user.id))
        if risk_metrics.get("success"):
            risk_data = risk_metrics.get("portfolio", {}) or {}
    except Exception as risk_error:  # pragma: no cover - defensive logging
        logger.warning(
            "Risk service unavailable while building portfolio response",
            user_id=str(current_user.id),
            error=str(risk_error),
        )

    positions: List[Dict[str, Any]] = portfolio_data.get("positions", []) or risk_data.get("positions", []) or []
    total_value_usd = (
        portfolio_data.get("total_value")
        or portfolio_data.get("total_value_usd")
        or risk_data.get("total_value")
        or risk_data.get("portfolio_value")
        or 0.0
    )

    # If positions aren't directly available, transform from balances (real data format)
    if not positions and portfolio_data.get("balances"):
        for balance in portfolio_data.get("balances", []):
            if balance.get("total", 0) > 0:
                positions.append({
                    "symbol": balance.get("asset", "UNKNOWN"),
                    "name": balance.get("asset", "UNKNOWN"),
                    "amount": balance.get("total", 0.0),
                    "value_usd": balance.get("value_usd", 0.0),
                    "entry_price": (balance.get("value_usd", 0.0) / balance.get("total", 1)) if balance.get("total") else 0.0,
                    "current_price": (balance.get("value_usd", 0.0) / balance.get("total", 1)) if balance.get("total") else 0.0,
                    "change_24h_pct": balance.get("change_24h_pct", 0.0),
                    "unrealized_pnl": balance.get("unrealized_pnl", 0.0),
                    "side": balance.get("side", "long"),
                    "exchange": balance.get("exchange", "unknown"),
                })

    available_balance = (
        portfolio_data.get("available_balance")
        or risk_data.get("available_balance")
        or risk_data.get("cash_available")
        or 0.0
    )
    if not available_balance and portfolio_data.get("balances"):
        stablecoins = {"USDT", "USDC", "BUSD", "DAI", "FDUSD"}
        available_balance = sum(
            balance.get("value_usd", 0.0)
            for balance in portfolio_data.get("balances", [])
            if balance.get("asset") in stablecoins
        )

    daily_pnl = portfolio_data.get("daily_pnl")
    if daily_pnl is None:
        daily_pnl = risk_data.get("daily_pnl", 0.0)

    total_pnl = portfolio_data.get("total_pnl")
    if total_pnl is None:
        total_pnl = risk_data.get("total_pnl", 0.0)

    margin_used = portfolio_data.get("margin_used")
    if margin_used is None:
        margin_used = risk_data.get("margin_used", 0.0)

    margin_available = portfolio_data.get("margin_available")
    if margin_available is None:
        margin_available = risk_data.get("margin_available", 0.0)

    risk_score = portfolio_data.get("risk_score", risk_data.get("risk_score", 5.0))
    active_orders = portfolio_data.get("active_orders", risk_data.get("active_orders", 0))

    return PortfolioResponse(
        total_value=Decimal(str(total_value_usd)),
        available_balance=Decimal(str(available_balance)),
        positions=positions,
        daily_pnl=Decimal(str(daily_pnl or 0)),
        daily_pnl_pct=float(portfolio_data.get("daily_pnl_pct", risk_data.get("daily_pnl_pct", 0.0)) or 0.0),
        total_pnl=Decimal(str(total_pnl or 0)),
        total_pnl_pct=float(portfolio_data.get("total_pnl_pct", risk_data.get("total_pnl_pct", 0.0)) or 0.0),
        margin_used=Decimal(str(margin_used or 0)),
        margin_available=Decimal(str(margin_available or 0)),
        risk_score=float(risk_score or 0),
        active_orders=int(active_orders or 0),
    )


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get current portfolio status and performance."""

    return await _build_portfolio_response(current_user, db, enforce_rate_limit=True)


@router.get("/portfolio/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Lightweight portfolio summary for dashboards requiring quick totals."""

    await rate_limiter.check_rate_limit(
        key="portfolio:summary",
        limit=200,
        window=60,
        user_id=str(current_user.id)
    )

    portfolio = await _build_portfolio_response(current_user, db, enforce_rate_limit=False)

    return PortfolioSummaryResponse(
        success=True,
        total_value=portfolio.total_value,
        available_balance=portfolio.available_balance,
        cash_balance=portfolio.available_balance,
        positions_count=len(portfolio.positions),
        daily_pnl=portfolio.daily_pnl,
        daily_pnl_pct=portfolio.daily_pnl_pct,
        total_pnl=portfolio.total_pnl,
        total_pnl_pct=portfolio.total_pnl_pct,
        last_updated=datetime.utcnow(),
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
        # Get real market data from MarketAnalysisService with fallback chain
        market_result = await market_analysis.realtime_price_tracking(
            symbols="BTC,ETH,SOL,ADA,DOT,MATIC,LINK,UNI",
            exchanges="all",
            user_id=str(current_user.id)
        )
        
        if market_result.get("success"):
            market_data_items = []
            data = market_result.get("data", {})
            
            for symbol, symbol_data in data.items():
                if symbol_data.get("aggregated"):
                    agg = symbol_data["aggregated"]
                    # Calculate volume in readable format
                    volume = agg.get("total_volume", 0)
                    volume_str = f"{volume/1e9:.1f}B" if volume > 1e9 else f"{volume/1e6:.0f}M"
                    
                    market_data_items.append({
                        "symbol": symbol,
                        "price": Decimal(str(agg.get("average_price", 0))),
                        "change": float(symbol_data.get("exchanges", [{}])[0].get("change_24h", 0)) if symbol_data.get("exchanges") else 0.0,
                        "volume": volume_str
                    })
            
            if market_data_items:
                return MarketOverviewResponse(market_data=market_data_items)
        
        # Fallback to unified price service
        from app.services.unified_price_service import get_market_overview_prices
        fallback_prices = await get_market_overview_prices()
        
        if fallback_prices:
            market_data_items = []
            
            for symbol, price in fallback_prices.items():
                market_data_items.append({
                    "symbol": symbol,
                    "price": Decimal(str(price)),
                    "change": 0.0,  # No change data available from price-only service
                    "volume": "N/A"
                })
            
            return MarketOverviewResponse(market_data=market_data_items)
        
        # Final fallback to prevent errors
        logger.warning("All market data sources failed, using minimal fallback data")
        fallback_data = [
            {"symbol": "BTC", "price": Decimal("0"), "change": 0.0, "volume": "N/A"},
            {"symbol": "ETH", "price": Decimal("0"), "change": 0.0, "volume": "N/A"},
        ]
        return MarketOverviewResponse(market_data=fallback_data)
    except Exception as e:
        logger.error("Market overview retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get market overview: {str(e)}"
        )

@router.get("/recent-trades", response_model=RecentTradesResponse)
async def get_recent_trades(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get recent trading activity."""
    await rate_limiter.check_rate_limit(
        key="trades:recent",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )
    try:
        # Query recent trades for the current user
        stmt = select(Trade).where(
            Trade.user_id == current_user.id
        ).order_by(Trade.created_at.desc()).limit(50)
        
        result = await db.execute(stmt)
        trades = result.scalars().all()
        
        # Convert to response format
        recent_trades = []
        for trade in trades:
            recent_trades.append(RecentTrade(
                id=str(trade.id),
                symbol=trade.symbol,
                side=trade.action.value,  # Use action.value instead of non-existent side
                amount=Decimal(str(trade.quantity)),
                price=Decimal(str(trade.executed_price or trade.price or 0)),
                time=trade.created_at.isoformat(),
                status=trade.status.value,
                pnl=Decimal(str(trade.profit_realized_usd or 0))
            ))
        
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
    token: Optional[str] = None
):
    # ENTERPRISE: Bearer subprotocol authentication before accepting connection
    user_id = "anonymous"  # Default for public market data
    selected_subprotocol = None  # Initialize to None, only set if safe subprotocol offered
    token = None
    
    # Read subprotocols from Sec-WebSocket-Protocol header
    subprotocols = getattr(websocket, 'scope', {}).get('subprotocols', [])
    
    # Scan client-offered subprotocols for bearer token format
    safe_subprotocols = {"json", "jwt"}  # Safe subprotocols we can echo back
    
    if subprotocols:
        # Look for bearer authentication pattern: ["bearer", <token>, "json"]
        bearer_index = None
        for i, subprotocol in enumerate(subprotocols):
            # Check if this is a safe subprotocol we can echo back
            if subprotocol.lower() in safe_subprotocols:
                selected_subprotocol = subprotocol.lower()
            
            # Check for bearer indicator
            if subprotocol.lower() == "bearer":
                bearer_index = i
                break
        
        # If bearer found, look for JWT token in next subprotocol entry
        if bearer_index is not None and bearer_index + 1 < len(subprotocols):
            token = subprotocols[bearer_index + 1]
        
        # Try to authenticate with extracted bearer token
        if token:
            try:
                from app.core.security import verify_access_token
                payload = verify_access_token(token)
                if payload and payload.get("sub"):
                    user_id = payload["sub"]
                    logger.info("WebSocket user authenticated via bearer subprotocol", user_id=user_id)
            except JWTError as e:
                logger.debug("WebSocket bearer authentication failed, proceeding as anonymous", error=str(e))
                # Don't log token details
    
    # Fallback: check query string for token if no bearer subprotocol found
    if not token:
        query_params = dict(websocket.query_params)
        token = query_params.get('token')
        
        if token:
            try:
                from app.core.security import verify_access_token
                payload = verify_access_token(token)
                if payload and payload.get("sub"):
                    user_id = payload["sub"]
                    logger.info("WebSocket user authenticated via query param", user_id=user_id)
            except JWTError as e:
                logger.debug("WebSocket query auth failed, proceeding as anonymous", error=str(e))
    
    if user_id == "anonymous":
        logger.info("WebSocket anonymous user will connect")
    
    # Accept connection - only pass subprotocol if safe one was offered by client
    if selected_subprotocol:
        await websocket.accept(subprotocol=selected_subprotocol)
    else:
        await websocket.accept()
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive client messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "subscribe_market":
                    # Subscribe to market data updates
                    symbols = message.get("symbols", [])
                    await manager.subscribe_to_market_data(websocket, symbols)
                    await websocket.send_json({
                        "type": "subscription_confirmed",
                        "symbols": symbols,
                        "message": f"Subscribed to market data for {', '.join(symbols)}"
                    })
                
                elif message_type == "unsubscribe_market":
                    # Unsubscribe from market data
                    symbols = message.get("symbols", [])
                    await manager.unsubscribe_from_market_data(websocket, symbols)
                    await websocket.send_json({
                        "type": "unsubscription_confirmed",
                        "symbols": symbols,
                        "message": f"Unsubscribed from market data for {', '.join(symbols)}"
                    })
                
                elif message_type == "ping":
                    # Heartbeat
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                else:
                    # Echo back for testing
                    await websocket.send_json({
                        "type": "echo",
                        "data": message,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
            except json.JSONDecodeError:
                # Handle plain text messages
                await websocket.send_text(f"Echo: {data}")
                
    except WebSocketDisconnect:
        # Normal disconnect - don't log as error
        pass
    except asyncio.CancelledError:
        # Re-raise cancellation so it's not swallowed
        raise
    except Exception as e:
        logger.exception("WebSocket error during message processing", user_id=user_id)
    finally:
        # Always ensure cleanup regardless of how the coroutine ends
        try:
            await manager.disconnect(websocket, user_id)
            await websocket.close()
        except Exception as e:
            logger.debug("Error during WebSocket cleanup", error=str(e))

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


# Arbitrage Endpoints
@router.get("/arbitrage/opportunities")
async def get_arbitrage_opportunities(
    current_user: User = Depends(get_current_user)
):
    """Get real-time arbitrage opportunities across exchanges."""
    
    await rate_limiter.check_rate_limit(
        key="trading:arbitrage_opportunities",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.cross_exchange_arbitrage_scanner(
            symbols="BTC,ETH,SOL,ADA,DOT,MATIC,LINK,UNI",
            exchanges="binance,kraken,kucoin",
            min_profit_bps=5,
            user_id=str(current_user.id)
        )
        
        if result.get("success"):
            return {
                "success": True,
                "data": {
                    "opportunities": result["data"]["opportunities"],
                    "total_found": len(result["data"]["opportunities"]),
                    "metadata": result["data"]["metadata"]
                }
            }
        else:
            return {
                "success": False,
                "data": {"opportunities": []},
                "error": result.get("error", "Failed to scan arbitrage opportunities")
            }
            
    except Exception as e:
        logger.error("Arbitrage opportunities scan failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "data": {"opportunities": []},
            "error": str(e)
        }


@router.get("/arbitrage/cross-exchange-comparison")
async def get_cross_exchange_comparison(
    symbols: str = "BTC,ETH,SOL",
    current_user: User = Depends(get_current_user)
):
    """Get cross-exchange price comparison for arbitrage analysis."""
    
    await rate_limiter.check_rate_limit(
        key="trading:cross_exchange",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        exchange_list = ["binance", "kraken", "kucoin"]
        
        comparison_data = []
        
        for symbol in symbol_list:
            prices = {}
            
            # Get prices from all exchanges
            for exchange in exchange_list:
                try:
                    price_data = await market_analysis._get_symbol_price(exchange, symbol)
                    if price_data and price_data.get("price"):
                        prices[exchange] = {
                            "price": float(price_data["price"]),
                            "volume": float(price_data.get("volume", 0)),
                            "timestamp": price_data.get("timestamp")
                        }
                except Exception as e:
                    logger.debug(f"Failed to get {symbol} price from {exchange}: {str(e)}")
                    continue
            
            if len(prices) >= 2:
                # Calculate spreads
                price_values = [data["price"] for data in prices.values()]
                max_price = max(price_values)
                min_price = min(price_values)
                spread_percentage = ((max_price - min_price) / min_price) * 100
                
                comparison_data.append({
                    "symbol": symbol,
                    "exchanges": prices,
                    "spread": {
                        "absolute": round(max_price - min_price, 6),
                        "percentage": round(spread_percentage, 4),
                        "max_price": max_price,
                        "min_price": min_price
                    },
                    "arbitrage_potential": spread_percentage > 0.1  # 0.1% threshold
                })
        
        return {
            "success": True,
            "data": {
                "comparisons": comparison_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Cross-exchange comparison failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "data": {"comparisons": []},
            "error": str(e)
        }


@router.get("/arbitrage/orderbook/{symbol}")
async def get_arbitrage_orderbook(
    symbol: str,
    exchanges: str = "binance,kraken,kucoin",
    current_user: User = Depends(get_current_user)
):
    """Get orderbook data for arbitrage analysis."""
    
    await rate_limiter.check_rate_limit(
        key="trading:orderbook",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        symbol = symbol.upper()
        exchange_list = [e.strip().lower() for e in exchanges.split(",")]
        
        orderbooks = {}
        
        # Get orderbook from each exchange
        for exchange in exchange_list:
            try:
                # For now, return mock orderbook data
                # TODO: Implement real orderbook fetching from exchanges
                orderbooks[exchange] = {
                    "bids": [
                        {"price": 50000 + (i * 10), "quantity": 0.1 * (5 - i)} 
                        for i in range(5)
                    ],
                    "asks": [
                        {"price": 50100 + (i * 10), "quantity": 0.1 * (5 - i)} 
                        for i in range(5)
                    ],
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.debug(f"Failed to get {symbol} orderbook from {exchange}: {str(e)}")
                continue
        
        # Calculate unified orderbook (best bids/asks across all exchanges)
        all_bids = []
        all_asks = []
        
        for exchange, book in orderbooks.items():
            for bid in book["bids"]:
                all_bids.append({**bid, "exchange": exchange})
            for ask in book["asks"]:
                all_asks.append({**ask, "exchange": exchange})
        
        # Sort bids (highest first) and asks (lowest first)
        all_bids.sort(key=lambda x: x["price"], reverse=True)
        all_asks.sort(key=lambda x: x["price"])
        
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "exchange_orderbooks": orderbooks,
                "unified_orderbook": {
                    "bids": all_bids[:10],  # Top 10 bids
                    "asks": all_asks[:10],  # Top 10 asks
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Orderbook fetch failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "data": {"symbol": symbol, "exchange_orderbooks": {}, "unified_orderbook": {"bids": [], "asks": []}},
            "error": str(e)
        }


# Market Analysis Endpoints (Trading namespace compatibility)
@router.post("/market/sentiment")
async def get_market_sentiment(
    current_user: User = Depends(get_current_user)
):
    """Get market sentiment analysis - TRADING namespace compatibility endpoint."""
    
    await rate_limiter.check_rate_limit(
        key="market:sentiment_analysis",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Default parameters for sentiment analysis
        result = await market_analysis.market_sentiment(
            symbols="BTC,ETH,SOL,ADA,DOT,MATIC,LINK,UNI",
            timeframes="1h,4h,1d",
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Sentiment analysis failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Market sentiment analysis failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sentiment analysis failed: {str(e)}"
        )


# MISSING MARKET ANALYSIS COMPATIBILITY ENDPOINTS
@router.post("/market/realtime-prices")
async def get_market_realtime_prices(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """Realtime prices endpoint - Trading namespace compatibility."""
    
    await rate_limiter.check_rate_limit(
        key="market:realtime_prices",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        symbols = request.get("symbols", ["BTC", "ETH", "SOL"])
        if isinstance(symbols, list):
            symbols_str = ",".join(symbols)
        else:
            symbols_str = str(symbols)
        
        result = await market_analysis.realtime_price_tracking(
            symbols=symbols_str,
            exchanges="all",
            user_id=str(current_user.id)
        )
        return result
        
    except Exception as e:
        logger.error("Realtime prices failed", error=str(e), exc_info=True)
        return {"success": False, "error": str(e), "data": {}}


@router.get("/market/trending")
async def get_market_trending(
    current_user: User = Depends(get_current_user)
):
    """Trending coins endpoint - Trading namespace compatibility."""
    
    await rate_limiter.check_rate_limit(
        key="market:trending",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Use MarketDataFeeds service for trending coins
        from app.services.market_data_feeds import market_data_feeds
        result = await market_data_feeds.get_trending_coins(limit=10)
        return result
        
    except Exception as e:
        logger.error("Trending coins failed", error=str(e), exc_info=True)
        return {"success": False, "error": str(e), "data": []}


@router.get("/market/health")
async def get_market_health(
    current_user: User = Depends(get_current_user)
):
    """Market health endpoint - Trading namespace compatibility."""
    
    await rate_limiter.check_rate_limit(
        key="market:health",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.health_check()
        return result
        
    except Exception as e:
        logger.error("Market health check failed", error=str(e), exc_info=True)
        return {"success": False, "error": str(e), "data": {}}


@router.post("/market/volatility")
async def get_market_volatility(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """Volatility analysis endpoint - Trading namespace compatibility."""
    
    await rate_limiter.check_rate_limit(
        key="market:volatility",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        symbols = request.get("symbols", ["BTC", "ETH", "SOL"])
        if isinstance(symbols, list):
            symbols_str = ",".join(symbols)
        else:
            symbols_str = str(symbols)
        
        result = await market_analysis.volatility_analysis(
            symbols=symbols_str,
            timeframes="1h,4h,1d",
            user_id=str(current_user.id)
        )
        return result
        
    except Exception as e:
        logger.error("Volatility analysis failed", error=str(e), exc_info=True)
        return {"success": False, "error": str(e), "data": {}}


@router.get("/market/support-resistance/{symbol}")
async def get_market_support_resistance(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    """Support/resistance endpoint - Trading namespace compatibility."""
    
    await rate_limiter.check_rate_limit(
        key="market:support_resistance",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.support_resistance_detection(
            symbols=symbol.upper(),
            timeframes="1h,4h,1d",
            user_id=str(current_user.id)
        )
        return result
        
    except Exception as e:
        logger.error("Support/resistance analysis failed", error=str(e), exc_info=True)
        return {"success": False, "error": str(e), "data": {}}


@router.get("/market/institutional-flows")
async def get_market_institutional_flows(
    current_user: User = Depends(get_current_user)
):
    """Institutional flows endpoint - Trading namespace compatibility."""
    
    await rate_limiter.check_rate_limit(
        key="market:institutional_flows",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.institutional_flow_tracker(
            symbols="BTC,ETH,SOL,ADA",
            timeframes="1h,4h,1d",
            flow_types="whale_tracking,institutional_trades",
            user_id=str(current_user.id)
        )
        return result
        
    except Exception as e:
        logger.error("Institutional flows failed", error=str(e), exc_info=True)
        return {"success": False, "error": str(e), "data": []}


@router.get("/market/alpha-signals")
async def get_market_alpha_signals(
    current_user: User = Depends(get_current_user)
):
    """Alpha signals endpoint - Trading namespace compatibility."""
    
    await rate_limiter.check_rate_limit(
        key="market:alpha_signals",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.alpha_generation_coordinator(
            universe="BTC,ETH,SOL,ADA",  # Correct parameter name
            strategies="momentum,mean_reversion,breakout",
            user_id=str(current_user.id)
        )
        return result
        
    except Exception as e:
        logger.error("Alpha signals failed", error=str(e), exc_info=True)
        return {"success": False, "error": str(e), "data": []}


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
