"""
Analytics-related database models.

Contains models for performance metrics, risk analysis,
trading sessions, and user analytics.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class MetricType(str, enum.Enum):
    """Performance metric type enumeration."""
    RETURN = "return"
    VOLATILITY = "volatility"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"


class RiskLevel(str, enum.Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class SessionStatus(str, enum.Enum):
    """Trading session status enumeration."""
    ACTIVE = "active"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


class PerformanceMetric(Base):
    """Performance metrics tracking."""
    
    __tablename__ = "performance_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=True, index=True)
    metric_type = Column(Enum(MetricType), nullable=False, index=True)
    value = Column(Numeric(15, 8), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_metric_user_type_period", "user_id", "metric_type", "period_start"),
    )
    
    def __repr__(self) -> str:
        return f"<PerformanceMetric(user_id={self.user_id}, type={self.metric_type}, value={self.value})>"


class RiskMetric(Base):
    """Risk metrics and analysis."""
    
    __tablename__ = "risk_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=True, index=True)
    risk_level = Column(Enum(RiskLevel), nullable=False, index=True)
    var_95 = Column(Numeric(15, 2), nullable=True)
    var_99 = Column(Numeric(15, 2), nullable=True)
    expected_shortfall = Column(Numeric(15, 2), nullable=True)
    beta = Column(Numeric(8, 4), nullable=True)
    correlation_metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_risk_user_level", "user_id", "risk_level"),
    )
    
    def __repr__(self) -> str:
        return f"<RiskMetric(user_id={self.user_id}, level={self.risk_level})>"


class TradingSession(Base):
    """Trading session tracking."""
    
    __tablename__ = "trading_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False, index=True)
    trades_count = Column(Integer, default=0, nullable=False)
    total_volume = Column(Numeric(15, 2), default=0, nullable=False)
    pnl = Column(Numeric(15, 2), default=0, nullable=False)
    started_at = Column(DateTime, default=func.now(), nullable=False)
    ended_at = Column(DateTime, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index("idx_session_user_status", "user_id", "status"),
        Index("idx_session_started", "started_at"),
    )
    
    def __repr__(self) -> str:
        return f"<TradingSession(user_id={self.user_id}, status={self.status}, trades={self.trades_count})>"


class UserAnalytics(Base):
    """User behavior and performance analytics."""
    
    __tablename__ = "user_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    total_trades = Column(Integer, default=0, nullable=False)
    total_volume_usd = Column(Numeric(20, 2), default=0, nullable=False)
    total_pnl_usd = Column(Numeric(15, 2), default=0, nullable=False)
    avg_trade_size_usd = Column(Numeric(15, 2), default=0, nullable=False)
    favorite_symbols = Column(JSON, nullable=True)
    trading_patterns = Column(JSON, nullable=True)
    last_active = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<UserAnalytics(user_id={self.user_id}, trades={self.total_trades}, pnl=${self.total_pnl_usd})>"
