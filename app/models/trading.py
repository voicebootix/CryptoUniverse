"""
Trading-related database models.

Handles trades, positions, orders, portfolios, and trading strategies
for the cryptocurrency trading platform.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class TradeAction(str, enum.Enum):
    """Trade action enumeration."""
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, enum.Enum):
    """Trade status enumeration."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    PARTIALLY_FILLED = "partially_filled"


class OrderType(str, enum.Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderStatus(str, enum.Enum):
    """Order status enumeration."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REJECTED = "rejected"


class PositionType(str, enum.Enum):
    """Position type enumeration."""
    LONG = "long"
    SHORT = "short"


class PositionStatus(str, enum.Enum):
    """Position status enumeration."""
    OPEN = "open"
    CLOSED = "closed"
    CLOSING = "closing"


class StrategyType(str, enum.Enum):
    """Trading strategy type enumeration."""
    MANUAL = "manual"
    ALGORITHMIC = "algorithmic"
    AI_CONSENSUS = "ai_consensus"
    COPY_TRADING = "copy_trading"
    ARBITRAGE = "arbitrage"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    SCALPING = "scalping"
    DCA = "dca"  # Dollar Cost Averaging


class TradingStrategy(Base):
    """
    Trading strategy definitions and configurations.
    
    Manages different trading strategies, their parameters,
    and performance tracking for the AI-powered trading system.
    """
    
    __tablename__ = "trading_strategies"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Strategy identification
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    strategy_type = Column(Enum(StrategyType), nullable=False, index=True)
    
    # Strategy configuration
    parameters = Column(JSON, nullable=False)
    risk_parameters = Column(JSON, nullable=False)
    entry_conditions = Column(JSON, nullable=False)
    exit_conditions = Column(JSON, nullable=False)
    
    # Execution settings
    is_active = Column(Boolean, default=False, nullable=False)
    is_simulation = Column(Boolean, default=True, nullable=False)
    max_positions = Column(Integer, default=1, nullable=False)
    max_risk_per_trade = Column(Numeric(5, 2), default=2.0, nullable=False)
    
    # Target settings
    target_symbols = Column(JSON, default=list, nullable=False)
    target_exchanges = Column(JSON, default=list, nullable=False)
    timeframe = Column(String(10), default="1h", nullable=False)
    
    # Performance tracking
    total_trades = Column(Integer, default=0, nullable=False)
    winning_trades = Column(Integer, default=0, nullable=False)
    total_pnl = Column(Numeric(15, 2), default=0, nullable=False)
    max_drawdown = Column(Numeric(15, 2), default=0, nullable=False)
    sharpe_ratio = Column(Numeric(8, 4), nullable=True)
    
    # AI settings (for AI strategies)
    ai_models = Column(JSON, default=list, nullable=False)
    confidence_threshold = Column(Numeric(5, 2), default=70.0, nullable=False)
    consensus_required = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_executed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="trading_strategies")
    trades = relationship("Trade", back_populates="strategy")
    positions = relationship("Position", back_populates="strategy")
    
    def __repr__(self) -> str:
        return f"<TradingStrategy(name={self.name}, type={self.strategy_type}, active={self.is_active})>"
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def average_pnl_per_trade(self) -> Decimal:
        """Calculate average P&L per trade."""
        if self.total_trades == 0:
            return Decimal("0")
        return self.total_pnl / self.total_trades
    
    def can_execute_trade(self) -> bool:
        """Check if strategy can execute new trades."""
        return self.is_active and self.max_positions > 0


class Trade(Base):
    """
    Individual trade execution records.
    
    Tracks all trade executions with complete details for
    performance analysis, compliance, and profit tracking.
    """
    
    __tablename__ = "trades"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    exchange_account_id = Column(UUID(as_uuid=True), ForeignKey("exchange_accounts.id"), nullable=False, index=True)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("trading_strategies.id"), nullable=True, index=True)
    position_id = Column(UUID(as_uuid=True), ForeignKey("positions.id"), nullable=True, index=True)
    
    # Trade basics
    symbol = Column(String(20), nullable=False, index=True)
    action = Column(Enum(TradeAction), nullable=False)
    status = Column(Enum(TradeStatus), default=TradeStatus.PENDING, nullable=False, index=True)
    
    # Execution details
    quantity = Column(Numeric(25, 8), nullable=False)
    price = Column(Numeric(25, 8), nullable=True)  # For limit orders
    executed_quantity = Column(Numeric(25, 8), default=0, nullable=False)
    executed_price = Column(Numeric(25, 8), nullable=True)
    
    # Order details
    order_type = Column(Enum(OrderType), default=OrderType.MARKET, nullable=False)
    external_order_id = Column(String(100), nullable=True, index=True)
    
    # Financial details
    total_value = Column(Numeric(15, 2), nullable=False)
    fees_paid = Column(Numeric(15, 8), default=0, nullable=False)
    fee_currency = Column(String(10), default="USD", nullable=False)
    
    # Stop loss and take profit
    stop_loss_price = Column(Numeric(25, 8), nullable=True)
    take_profit_price = Column(Numeric(25, 8), nullable=True)
    trailing_stop_distance = Column(Numeric(25, 8), nullable=True)
    
    # Execution context
    is_simulation = Column(Boolean, default=True, nullable=False)
    execution_mode = Column(String(20), default="balanced", nullable=False)
    urgency = Column(String(10), default="medium", nullable=False)
    
    # AI context
    ai_confidence = Column(Numeric(5, 2), nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    signal_source = Column(String(50), nullable=True)
    
    # Market context
    market_price_at_execution = Column(Numeric(25, 8), nullable=True)
    slippage_bps = Column(Numeric(8, 2), nullable=True)
    spread_bps = Column(Numeric(8, 2), nullable=True)
    
    # Risk metrics
    risk_score = Column(Integer, default=50, nullable=False)
    position_size_percent = Column(Numeric(5, 2), nullable=True)
    portfolio_impact_percent = Column(Numeric(5, 2), nullable=True)
    
    # Credits and profit tracking
    credits_used = Column(Integer, default=0, nullable=False)
    profit_realized_usd = Column(Numeric(12, 2), default=0, nullable=False)
    credit_transaction_id = Column(UUID(as_uuid=True), ForeignKey("credit_transactions.id"), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    executed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Metadata
    meta_data = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="trades")
    exchange_account = relationship("ExchangeAccount", back_populates="trades")
    strategy = relationship("TradingStrategy", back_populates="trades")
    position = relationship("Position", back_populates="trades")
    orders = relationship("Order", back_populates="trade", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_trade_user_symbol", "user_id", "symbol"),
        Index("idx_trade_status_created", "status", "created_at"),
        Index("idx_trade_executed", "executed_at"),
        Index("idx_trade_external_order", "external_order_id"),
        Index("idx_trade_simulation", "is_simulation"),
    )
    
    def __repr__(self) -> str:
        return f"<Trade(symbol={self.symbol}, action={self.action}, quantity={self.quantity}, status={self.status})>"
    
    @property
    def is_completed(self) -> bool:
        """Check if trade is completed."""
        return self.status == TradeStatus.COMPLETED
    
    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage."""
        if self.quantity == 0:
            return 0.0
        return float((self.executed_quantity / self.quantity) * 100)
    
    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost including fees."""
        base_cost = (self.executed_quantity or 0) * (self.executed_price or 0)
        return base_cost + (self.fees_paid or 0)
    
    def calculate_pnl(self, current_price: Optional[Decimal] = None) -> Decimal:
        """Calculate P&L for the trade."""
        if not self.is_completed or not self.executed_price or not self.executed_quantity:
            return Decimal("0")
        
        price = current_price or self.executed_price
        
        if self.action == TradeAction.BUY:
            return (price - self.executed_price) * self.executed_quantity - self.fees_paid
        else:
            return (self.executed_price - price) * self.executed_quantity - self.fees_paid


class Position(Base):
    """
    Trading position tracking.
    
    Manages open positions, position sizing, P&L calculation,
    and position management across multiple trades.
    """
    
    __tablename__ = "positions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    exchange_account_id = Column(UUID(as_uuid=True), ForeignKey("exchange_accounts.id"), nullable=False, index=True)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("trading_strategies.id"), nullable=True, index=True)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Position basics
    symbol = Column(String(20), nullable=False, index=True)
    position_type = Column(Enum(PositionType), nullable=False)
    status = Column(Enum(PositionStatus), default=PositionStatus.OPEN, nullable=False, index=True)
    
    # Position size
    quantity = Column(Numeric(25, 8), nullable=False)
    average_entry_price = Column(Numeric(25, 8), nullable=False)
    current_price = Column(Numeric(25, 8), nullable=True)
    
    # Position value
    entry_value = Column(Numeric(15, 2), nullable=False)
    current_value = Column(Numeric(15, 2), nullable=True)
    unrealized_pnl = Column(Numeric(15, 2), default=0, nullable=False)
    realized_pnl = Column(Numeric(15, 2), default=0, nullable=False)
    
    # Risk management
    stop_loss_price = Column(Numeric(25, 8), nullable=True)
    take_profit_price = Column(Numeric(25, 8), nullable=True)
    trailing_stop_distance = Column(Numeric(25, 8), nullable=True)
    max_loss_amount = Column(Numeric(15, 2), nullable=True)
    
    # Position tracking
    high_water_mark = Column(Numeric(25, 8), nullable=True)
    low_water_mark = Column(Numeric(25, 8), nullable=True)
    max_unrealized_profit = Column(Numeric(15, 2), default=0, nullable=False)
    max_unrealized_loss = Column(Numeric(15, 2), default=0, nullable=False)
    
    # Management settings
    auto_close_enabled = Column(Boolean, default=False, nullable=False)
    max_hold_duration_hours = Column(Integer, nullable=True)
    partial_close_enabled = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    opened_at = Column(DateTime, default=func.now(), nullable=False)
    closed_at = Column(DateTime, nullable=True)
    last_updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Metadata
    meta_data = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="positions")
    exchange_account = relationship("ExchangeAccount", back_populates="positions")
    strategy = relationship("TradingStrategy", back_populates="positions")
    portfolio = relationship("Portfolio", back_populates="positions")
    trades = relationship("Trade", back_populates="position")
    orders = relationship("Order", back_populates="position", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_position_user_symbol", "user_id", "symbol"),
        Index("idx_position_status", "status"),
        Index("idx_position_opened", "opened_at"),
        Index("idx_position_portfolio", "portfolio_id", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<Position(symbol={self.symbol}, type={self.position_type}, quantity={self.quantity}, status={self.status})>"
    
    @property
    def is_open(self) -> bool:
        """Check if position is open."""
        return self.status == PositionStatus.OPEN
    
    @property
    def hold_duration_hours(self) -> float:
        """Calculate how long position has been held."""
        end_time = self.closed_at or datetime.utcnow()
        duration = end_time - self.opened_at
        return duration.total_seconds() / 3600
    
    @property
    def pnl_percentage(self) -> float:
        """Calculate P&L percentage."""
        if self.entry_value == 0:
            return 0.0
        total_pnl = self.unrealized_pnl + self.realized_pnl
        return float((total_pnl / self.entry_value) * 100)
    
    def update_current_price(self, new_price: Decimal) -> None:
        """Update current price and recalculate unrealized P&L."""
        self.current_price = new_price
        self.current_value = self.quantity * new_price
        
        if self.position_type == PositionType.LONG:
            self.unrealized_pnl = (new_price - self.average_entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.average_entry_price - new_price) * self.quantity
        
        # Update high/low water marks
        if not self.high_water_mark or new_price > self.high_water_mark:
            self.high_water_mark = new_price
            
        if not self.low_water_mark or new_price < self.low_water_mark:
            self.low_water_mark = new_price
        
        # Update max profit/loss
        if self.unrealized_pnl > self.max_unrealized_profit:
            self.max_unrealized_profit = self.unrealized_pnl
            
        if self.unrealized_pnl < self.max_unrealized_loss:
            self.max_unrealized_loss = self.unrealized_pnl
        
        self.last_updated_at = datetime.utcnow()
    
    def should_close_position(self) -> tuple[bool, str]:
        """Check if position should be closed based on rules."""
        if not self.is_open:
            return False, "Position already closed"
        
        # Stop loss check
        if self.stop_loss_price and self.current_price:
            if self.position_type == PositionType.LONG and self.current_price <= self.stop_loss_price:
                return True, "Stop loss triggered"
            elif self.position_type == PositionType.SHORT and self.current_price >= self.stop_loss_price:
                return True, "Stop loss triggered"
        
        # Take profit check
        if self.take_profit_price and self.current_price:
            if self.position_type == PositionType.LONG and self.current_price >= self.take_profit_price:
                return True, "Take profit triggered"
            elif self.position_type == PositionType.SHORT and self.current_price <= self.take_profit_price:
                return True, "Take profit triggered"
        
        # Max hold duration check
        if self.max_hold_duration_hours:
            if self.hold_duration_hours >= self.max_hold_duration_hours:
                return True, "Max hold duration reached"
        
        # Max loss check
        if self.max_loss_amount and self.unrealized_pnl <= -self.max_loss_amount:
            return True, "Max loss amount reached"
        
        return False, ""


class Order(Base):
    """
    Order management and tracking.
    
    Manages individual orders, order status, and order execution
    for comprehensive order lifecycle tracking.
    """
    
    __tablename__ = "orders"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    exchange_account_id = Column(UUID(as_uuid=True), ForeignKey("exchange_accounts.id"), nullable=False, index=True)
    trade_id = Column(UUID(as_uuid=True), ForeignKey("trades.id"), nullable=True, index=True)
    position_id = Column(UUID(as_uuid=True), ForeignKey("positions.id"), nullable=True, index=True)
    
    # Order details
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(TradeAction), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    
    # Order quantities and prices
    quantity = Column(Numeric(25, 8), nullable=False)
    price = Column(Numeric(25, 8), nullable=True)  # For limit orders
    stop_price = Column(Numeric(25, 8), nullable=True)  # For stop orders
    
    # Execution tracking
    filled_quantity = Column(Numeric(25, 8), default=0, nullable=False)
    remaining_quantity = Column(Numeric(25, 8), nullable=False)
    average_fill_price = Column(Numeric(25, 8), nullable=True)
    
    # External references
    external_order_id = Column(String(100), nullable=True, index=True)
    client_order_id = Column(String(100), nullable=True, index=True)
    
    # Order settings
    time_in_force = Column(String(10), default="GTC", nullable=False)  # GTC, IOC, FOK
    reduce_only = Column(Boolean, default=False, nullable=False)
    post_only = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    filled_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    exchange_account = relationship("ExchangeAccount", back_populates="orders")
    trade = relationship("Trade", back_populates="orders")
    position = relationship("Position", back_populates="orders")
    
    # Indexes
    __table_args__ = (
        Index("idx_order_status_created", "status", "created_at"),
        Index("idx_order_external", "external_order_id"),
        Index("idx_order_client", "client_order_id"),
        Index("idx_order_symbol_status", "symbol", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<Order(symbol={self.symbol}, side={self.side}, quantity={self.quantity}, status={self.status})>"
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_active(self) -> bool:
        """Check if order is active (open or partially filled)."""
        return self.status in [OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage."""
        if self.quantity == 0:
            return 0.0
        return float((self.filled_quantity / self.quantity) * 100)


class Portfolio(Base):
    """
    Portfolio management and tracking.
    
    Aggregates positions, tracks portfolio performance,
    and manages portfolio-level risk and allocation.
    """
    
    __tablename__ = "portfolios"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Portfolio details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Portfolio value
    total_value_usd = Column(Numeric(15, 2), default=0, nullable=False)
    cash_balance_usd = Column(Numeric(15, 2), default=0, nullable=False)
    invested_value_usd = Column(Numeric(15, 2), default=0, nullable=False)
    
    # Performance tracking
    total_pnl_usd = Column(Numeric(15, 2), default=0, nullable=False)
    unrealized_pnl_usd = Column(Numeric(15, 2), default=0, nullable=False)
    realized_pnl_usd = Column(Numeric(15, 2), default=0, nullable=False)
    
    # Risk metrics
    max_drawdown_percent = Column(Numeric(8, 4), default=0, nullable=False)
    sharpe_ratio = Column(Numeric(8, 4), nullable=True)
    volatility_percent = Column(Numeric(8, 4), nullable=True)
    
    # Portfolio settings
    risk_level = Column(String(20), default="medium", nullable=False)
    max_position_size_percent = Column(Numeric(5, 2), default=10, nullable=False)
    max_sector_allocation_percent = Column(Numeric(5, 2), default=30, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")
    snapshots = relationship("PortfolioSnapshot", back_populates="portfolio", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Portfolio(name={self.name}, value=${self.total_value_usd}, pnl=${self.total_pnl_usd})>"
    
    @property
    def pnl_percentage(self) -> float:
        """Calculate P&L percentage."""
        if self.invested_value_usd == 0:
            return 0.0
        return float((self.total_pnl_usd / self.invested_value_usd) * 100)
    
    @property
    def position_count(self) -> int:
        """Get number of open positions."""
        return len([p for p in self.positions if p.is_open])


class PortfolioSnapshot(Base):
    """
    Portfolio snapshot for historical tracking.
    
    Stores daily portfolio snapshots for performance analysis
    and historical tracking.
    """
    
    __tablename__ = "portfolio_snapshots"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Snapshot data
    snapshot_date = Column(DateTime, nullable=False, index=True)
    total_value_usd = Column(Numeric(15, 2), nullable=False)
    cash_balance_usd = Column(Numeric(15, 2), nullable=False)
    invested_value_usd = Column(Numeric(15, 2), nullable=False)
    
    # Performance data
    daily_pnl_usd = Column(Numeric(15, 2), nullable=False)
    daily_pnl_percent = Column(Numeric(8, 4), nullable=False)
    total_pnl_usd = Column(Numeric(15, 2), nullable=False)
    total_pnl_percent = Column(Numeric(8, 4), nullable=False)
    
    # Portfolio composition
    positions_data = Column(JSON, nullable=False)
    allocation_data = Column(JSON, nullable=False)
    
    # Risk metrics
    volatility_1d = Column(Numeric(8, 4), nullable=True)
    sharpe_ratio_30d = Column(Numeric(8, 4), nullable=True)
    max_drawdown_30d = Column(Numeric(8, 4), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="snapshots")
    
    # Indexes
    __table_args__ = (
        Index("idx_snapshot_portfolio_date", "portfolio_id", "snapshot_date"),
        Index("idx_snapshot_date", "snapshot_date"),
    )
    
    def __repr__(self) -> str:
        return f"<PortfolioSnapshot(portfolio_id={self.portfolio_id}, date={self.snapshot_date}, value=${self.total_value_usd})>"
