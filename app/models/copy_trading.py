"""
Copy trading-related database models.

Contains models for copy trading marketplace, strategy publishing,
performance tracking, and signal distribution.
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
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class StrategyStatus(str, enum.Enum):
    """Strategy status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class SignalStatus(str, enum.Enum):
    """Copy trade signal status enumeration."""
    PENDING = "pending"
    DISTRIBUTED = "distributed"
    EXECUTED = "executed"
    FAILED = "failed"


class StrategyPublisher(Base):
    """Strategy publisher profiles."""
    
    __tablename__ = "strategy_publishers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    verified = Column(Boolean, default=False, nullable=False)
    total_followers = Column(Integer, default=0, nullable=False)
    total_strategies = Column(Integer, default=0, nullable=False)
    revenue_share_percentage = Column(Numeric(5, 2), default=70.0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<StrategyPublisher(name={self.display_name}, followers={self.total_followers})>"


class StrategyFollower(Base):
    """Strategy follower relationships."""
    
    __tablename__ = "strategy_followers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("trading_strategies.id"), nullable=False, index=True)
    allocation_percentage = Column(Numeric(5, 2), nullable=False)
    max_drawdown_percentage = Column(Numeric(5, 2), default=20.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    started_at = Column(DateTime, default=func.now(), nullable=False)
    stopped_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        UniqueConstraint("user_id", "strategy_id", name="unique_user_strategy_follow"),
        Index("idx_follower_user_active", "user_id", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<StrategyFollower(user_id={self.user_id}, strategy_id={self.strategy_id})>"


class StrategyPerformance(Base):
    """Strategy performance tracking."""
    
    __tablename__ = "strategy_performance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("trading_strategies.id"), nullable=False, index=True)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    total_return = Column(Numeric(10, 4), nullable=False)
    sharpe_ratio = Column(Numeric(8, 4), nullable=True)
    max_drawdown = Column(Numeric(8, 4), nullable=False)
    win_rate = Column(Numeric(5, 2), nullable=False)
    total_trades = Column(Integer, nullable=False)
    followers_count = Column(Integer, default=0, nullable=False)
    aum = Column(Numeric(15, 2), default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_performance_strategy_period", "strategy_id", "period_start"),
    )
    
    def __repr__(self) -> str:
        return f"<StrategyPerformance(strategy_id={self.strategy_id}, return={self.total_return})>"


class CopyTradeSignal(Base):
    """Copy trading signal distribution."""
    
    __tablename__ = "copy_trade_signals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("trading_strategies.id"), nullable=False, index=True)
    trade_id = Column(UUID(as_uuid=True), ForeignKey("trades.id"), nullable=False, index=True)
    signal_data = Column(JSON, nullable=False)
    status = Column(Enum(SignalStatus), default=SignalStatus.PENDING, nullable=False, index=True)
    followers_targeted = Column(Integer, default=0, nullable=False)
    followers_executed = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    distributed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("idx_signal_strategy_status", "strategy_id", "status"),
        Index("idx_signal_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<CopyTradeSignal(strategy_id={self.strategy_id}, status={self.status})>"
