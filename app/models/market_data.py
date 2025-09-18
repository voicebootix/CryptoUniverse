"""
Market Data Models for Historical Storage
Enterprise-grade data persistence for real market data
"""

from datetime import datetime, timezone
from typing import Optional
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Column, String, DateTime, Float, BigInteger, Integer,
    Boolean, JSON, Index, UniqueConstraint, ForeignKey, Text, Numeric,
    CheckConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class TimeFrame(str, Enum):
    """Supported timeframes for market data."""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"


class MarketDataOHLCV(Base):
    """
    Historical OHLCV (candlestick) data storage.

    Stores real market data fetched from exchanges for backtesting
    and strategy analysis.
    """
    __tablename__ = "market_data_ohlcv"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Market identifiers
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)

    # OHLCV data
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)

    # Additional metrics
    trade_count = Column(Integer, default=0)
    vwap = Column(Numeric(20, 8))  # Volume-weighted average price

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String(50), default="ccxt")  # Data source
    is_validated = Column(Boolean, default=False)

    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint('symbol', 'exchange', 'timeframe', 'timestamp',
                        name='unique_candle'),
        Index('idx_ohlcv_lookup', 'symbol', 'exchange', 'timeframe', 'timestamp'),
        Index('idx_ohlcv_timestamp', 'timestamp'),
    )


class MarketTicker(Base):
    """
    Real-time ticker data storage.

    Stores snapshot ticker data for real-time price tracking.
    """
    __tablename__ = "market_tickers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Market identifiers
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, index=True)

    # Price data
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    last_price = Column(Numeric(20, 8), nullable=False)
    bid = Column(Numeric(20, 8))
    ask = Column(Numeric(20, 8))
    bid_size = Column(Numeric(20, 8))
    ask_size = Column(Numeric(20, 8))

    # 24h stats
    open_24h = Column(Numeric(20, 8))
    high_24h = Column(Numeric(20, 8))
    low_24h = Column(Numeric(20, 8))
    volume_24h = Column(Numeric(20, 8))
    quote_volume_24h = Column(Numeric(20, 8))
    change_24h = Column(Numeric(10, 4))  # Percentage

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_ticker_lookup', 'symbol', 'exchange', 'timestamp'),
    )


class OrderBookSnapshot(Base):
    """
    Order book depth snapshots for accurate simulation.

    Stores periodic snapshots of order book depth.
    """
    __tablename__ = "orderbook_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Market identifiers
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Order book data (stored as JSON for flexibility)
    bids = Column(JSON, nullable=False)  # [[price, amount], ...]
    asks = Column(JSON, nullable=False)  # [[price, amount], ...]

    # Summary metrics
    best_bid = Column(Numeric(20, 8))
    best_ask = Column(Numeric(20, 8))
    spread = Column(Numeric(20, 8))
    spread_pct = Column(Numeric(10, 4))

    # Liquidity metrics
    bid_depth_10 = Column(Numeric(20, 8))  # Total bid volume in top 10 levels
    ask_depth_10 = Column(Numeric(20, 8))  # Total ask volume in top 10 levels

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    levels_count = Column(Integer, default=20)

    __table_args__ = (
        Index('idx_orderbook_lookup', 'symbol', 'exchange', 'timestamp'),
    )


class StrategyPerformanceHistory(Base):
    """
    Historical performance tracking for strategies.

    Records actual strategy performance over time with real data.
    """
    __tablename__ = "strategy_performance_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Strategy identification
    strategy_id = Column(String(100), nullable=False, index=True)
    strategy_name = Column(String(200), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)

    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False)
    timeframe = Column(String(20), nullable=False)  # daily, weekly, monthly

    # Performance metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Numeric(5, 2), CheckConstraint('win_rate >= 0 AND win_rate <= 100', name='check_strategy_win_rate_range'))

    # Financial metrics
    starting_balance = Column(Numeric(20, 8), nullable=False)
    ending_balance = Column(Numeric(20, 8), nullable=False)
    total_pnl = Column(Numeric(20, 8), nullable=False)
    total_pnl_pct = Column(Numeric(10, 4))

    # Risk metrics
    max_drawdown = Column(Numeric(10, 4))
    sharpe_ratio = Column(Numeric(10, 4))
    sortino_ratio = Column(Numeric(10, 4))
    calmar_ratio = Column(Numeric(10, 4))

    # Trade details
    best_trade_pnl = Column(Numeric(20, 8))
    worst_trade_pnl = Column(Numeric(20, 8))
    avg_trade_pnl = Column(Numeric(20, 8))
    avg_win_pnl = Column(Numeric(20, 8))
    avg_loss_pnl = Column(Numeric(20, 8))

    # Execution metrics
    total_fees = Column(Numeric(20, 8), default=0)
    total_slippage = Column(Numeric(20, 8), default=0)
    avg_execution_time = Column(Float)  # seconds

    # Additional data
    traded_symbols = Column(JSON)  # List of symbols traded
    trade_distribution = Column(JSON)  # Distribution by hour/day

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_live = Column(Boolean, default=False)  # Live vs backtest
    data_source = Column(String(50), default="real_market_data")

    # Relationships
    user = relationship("User", back_populates="strategy_performance_history")

    __table_args__ = (
        Index('idx_perf_history_lookup', 'strategy_id', 'user_id', 'period_start'),
        Index('idx_perf_history_user', 'user_id', 'period_start'),
    )


class BacktestResult(Base):
    """
    Backtest results storage with real market data.

    Stores comprehensive backtest results for strategies.
    """
    __tablename__ = "backtest_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Backtest identification
    strategy_id = Column(String(100), nullable=False, index=True)
    strategy_name = Column(String(200), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Test parameters
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    initial_capital = Column(Numeric(20, 8), nullable=False)
    symbols = Column(JSON, nullable=False)  # List of symbols tested

    # Configuration
    strategy_params = Column(JSON)  # Strategy-specific parameters
    risk_params = Column(JSON)  # Risk management settings
    execution_params = Column(JSON)  # Execution settings

    # Results summary
    final_capital = Column(Numeric(20, 8), nullable=False)
    total_return = Column(Numeric(10, 4))
    total_return_pct = Column(Numeric(10, 4))

    # Trade statistics
    total_trades = Column(Integer, default=0)
    win_rate = Column(Numeric(5, 2), CheckConstraint('win_rate >= 0 AND win_rate <= 100', name='check_backtest_win_rate_range'))
    profit_factor = Column(Numeric(10, 4))
    expectancy = Column(Numeric(20, 8))

    # Risk metrics
    max_drawdown = Column(Numeric(10, 4))
    max_drawdown_duration = Column(Integer)  # days
    sharpe_ratio = Column(Numeric(10, 4))
    sortino_ratio = Column(Numeric(10, 4))
    calmar_ratio = Column(Numeric(10, 4))

    # Detailed results
    equity_curve = Column(JSON)  # Time series of portfolio value
    trade_log = Column(JSON)  # Detailed trade history
    monthly_returns = Column(JSON)  # Monthly return breakdown

    # Validation
    data_quality_score = Column(Numeric(5, 2))  # 0-100
    data_gaps_count = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    execution_time = Column(Float)  # seconds
    data_source = Column(String(50), default="real_market_data")
    engine_version = Column(String(20), default="2.0.0")

    # Relationships
    user = relationship("User", back_populates="backtest_results")

    __table_args__ = (
        Index('idx_backtest_lookup', 'strategy_id', 'created_at'),
        Index('idx_backtest_user', 'user_id', 'created_at'),
    )