"""
Database models for A/B Testing Lab functionality.

This module defines SQLAlchemy models for storing A/B test configurations,
variants, results, and performance metrics.
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class ABTest(Base):
    """
    A/B Test model for storing test configurations and results.
    """
    __tablename__ = "ab_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    hypothesis = Column(Text, nullable=False)
    success_metric = Column(String(50), nullable=False, default="total_return")
    status = Column(String(20), nullable=False, default="draft", index=True)

    # Test Configuration
    min_sample_size = Column(Integer, nullable=False, default=1000)
    confidence_level = Column(Integer, nullable=False, default=95)
    test_duration_days = Column(Integer, nullable=False, default=30)
    traffic_allocation = Column(Integer, nullable=False, default=20)

    # Results
    total_participants = Column(Integer, nullable=False, default=0)
    winning_variant_id = Column(UUID(as_uuid=True), ForeignKey("ab_test_variants.id"), nullable=True)
    statistical_power = Column(Float, nullable=False, default=0.0)
    effect_size = Column(Float, nullable=False, default=0.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Foreign Keys
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    creator = relationship("User", back_populates="ab_tests")
    variants = relationship("ABTestVariant", back_populates="test", cascade="all, delete-orphan", foreign_keys="ABTestVariant.test_id")
    winning_variant = relationship("ABTestVariant", foreign_keys=[winning_variant_id], post_update=True)
    results = relationship("ABTestResult", back_populates="test", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ABTest(id={self.id}, name='{self.name}', status='{self.status}')>"


class ABTestVariant(Base):
    """
    A/B Test Variant model for storing individual test variations.
    """
    __tablename__ = "ab_test_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    test_id = Column(UUID(as_uuid=True), ForeignKey("ab_tests.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    strategy_code = Column(Text, nullable=False)
    parameters = Column(JSON, nullable=False, default=dict)
    allocation_percentage = Column(Integer, nullable=False)
    is_control = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="draft", index=True)

    # Performance Metrics
    total_return = Column(Float, nullable=False, default=0.0)
    sharpe_ratio = Column(Float, nullable=False, default=0.0)
    max_drawdown = Column(Float, nullable=False, default=0.0)
    win_rate = Column(Float, nullable=False, default=0.0)
    total_trades = Column(Integer, nullable=False, default=0)
    avg_trade_duration = Column(Float, nullable=False, default=0.0)
    profit_factor = Column(Float, nullable=False, default=0.0)
    volatility = Column(Float, nullable=False, default=0.0)

    # Statistical Significance
    p_value = Column(Float, nullable=False, default=1.0)
    confidence_level = Column(Float, nullable=False, default=95.0)
    statistical_significance = Column(String(20), nullable=False, default="inconclusive")

    # User Metrics
    active_users = Column(Integer, nullable=False, default=0)
    user_satisfaction = Column(Float, nullable=False, default=0.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    test = relationship("ABTest", back_populates="variants", foreign_keys=[test_id])
    results = relationship("ABTestResult", back_populates="variant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ABTestVariant(id={self.id}, name='{self.name}', is_control={self.is_control})>"


class ABTestResult(Base):
    """
    A/B Test Result model for storing daily performance results.
    """
    __tablename__ = "ab_test_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    test_id = Column(UUID(as_uuid=True), ForeignKey("ab_tests.id"), nullable=False)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("ab_test_variants.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Daily Performance Metrics
    daily_return = Column(Float, nullable=False, default=0.0)
    cumulative_return = Column(Float, nullable=False, default=0.0)
    trades_count = Column(Integer, nullable=False, default=0)
    win_count = Column(Integer, nullable=False, default=0)
    loss_count = Column(Integer, nullable=False, default=0)
    total_volume = Column(Float, nullable=False, default=0.0)
    max_drawdown_daily = Column(Float, nullable=False, default=0.0)
    volatility_daily = Column(Float, nullable=False, default=0.0)

    # User Engagement
    active_users_daily = Column(Integer, nullable=False, default=0)
    new_participants = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    test = relationship("ABTest", back_populates="results")
    variant = relationship("ABTestVariant", back_populates="results")

    def __repr__(self):
        return f"<ABTestResult(test_id={self.test_id}, variant_id={self.variant_id}, date={self.date})>"


class ABTestParticipant(Base):
    """
    A/B Test Participant model for tracking user participation in tests.
    """
    __tablename__ = "ab_test_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    test_id = Column(UUID(as_uuid=True), ForeignKey("ab_tests.id"), nullable=False)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("ab_test_variants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Participation Status
    status = Column(String(20), nullable=False, default="active", index=True)  # active, completed, opted_out
    satisfaction_rating = Column(Float, nullable=True)  # 1-5 rating
    feedback = Column(Text, nullable=True)

    # Performance tracking
    total_return = Column(Float, nullable=False, default=0.0)
    total_trades = Column(Integer, nullable=False, default=0)
    win_rate = Column(Float, nullable=False, default=0.0)

    # Timestamps
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    left_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    test = relationship("ABTest")
    variant = relationship("ABTestVariant")
    user = relationship("User")

    def __repr__(self):
        return f"<ABTestParticipant(user_id={self.user_id}, test_id={self.test_id}, variant_id={self.variant_id})>"


class ABTestMetric(Base):
    """
    A/B Test Metrics model for storing calculated statistical metrics.
    """
    __tablename__ = "ab_test_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    test_id = Column(UUID(as_uuid=True), ForeignKey("ab_tests.id"), nullable=False)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("ab_test_variants.id"), nullable=False)
    metric_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Statistical Metrics
    sample_size = Column(Integer, nullable=False, default=0)
    mean_value = Column(Float, nullable=False, default=0.0)
    std_deviation = Column(Float, nullable=False, default=0.0)
    confidence_interval_lower = Column(Float, nullable=False, default=0.0)
    confidence_interval_upper = Column(Float, nullable=False, default=0.0)
    p_value = Column(Float, nullable=False, default=1.0)
    t_statistic = Column(Float, nullable=False, default=0.0)
    effect_size = Column(Float, nullable=False, default=0.0)
    statistical_power = Column(Float, nullable=False, default=0.0)

    # Comparison with control
    control_comparison_p_value = Column(Float, nullable=True)
    control_comparison_effect_size = Column(Float, nullable=True)
    is_significantly_different = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    test = relationship("ABTest")
    variant = relationship("ABTestVariant")

    def __repr__(self):
        return f"<ABTestMetric(test_id={self.test_id}, variant_id={self.variant_id}, date={self.metric_date})>"