"""
Strategy Submission Model for Publisher Dashboard

This model handles strategy submissions from traders/publishers
who want to list their strategies on the marketplace.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, JSON,
    DateTime, ForeignKey, Enum as SQLEnum, DECIMAL
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.mutable import MutableDict
import enum
from uuid import uuid4

from app.core.database import Base


class StrategyStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class PricingModel(str, enum.Enum):
    FREE = "free"
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    PROFIT_SHARE = "profit_share"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ComplexityLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class SupportLevel(str, enum.Enum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


class StrategySubmission(Base):
    __tablename__ = "strategy_submissions"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign key to user (publisher)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Basic Information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    risk_level = Column(SQLEnum(RiskLevel), default=RiskLevel.MEDIUM)

    # Financial Details
    expected_return_min = Column(Float, default=0.0)
    expected_return_max = Column(Float, default=0.0)
    required_capital = Column(DECIMAL(15, 2), default=1000.0)

    # Pricing
    pricing_model = Column(SQLEnum(PricingModel), default=PricingModel.FREE)
    price_amount = Column(DECIMAL(10, 2), nullable=True)
    profit_share_percentage = Column(Float, nullable=True)

    # Status
    status = Column(SQLEnum(StrategyStatus), default=StrategyStatus.DRAFT)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Review Details
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    reviewer_feedback = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Backtest Results (stored as JSON)
    backtest_results = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        default=lambda: {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "profit_factor": 0.0,
            "period_days": 0
        }
    )

    # Validation Results (stored as JSON)
    validation_results = Column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        default=lambda: {
            "is_valid": False,
            "security_score": 0,
            "performance_score": 0,
            "code_quality_score": 0,
            "overall_score": 0
        }
    )

    # Publishing Details
    tags = Column(MutableDict.as_mutable(JSON), nullable=True, default=list)
    target_audience = Column(MutableDict.as_mutable(JSON), nullable=True, default=list)
    complexity_level = Column(SQLEnum(ComplexityLevel), default=ComplexityLevel.INTERMEDIATE)
    documentation_quality = Column(Integer, default=0)
    support_level = Column(SQLEnum(SupportLevel), default=SupportLevel.STANDARD)

    # Strategy Code/Configuration (stored securely)
    strategy_code = Column(Text, nullable=True)  # Encrypted in production
    strategy_config = Column(MutableDict.as_mutable(JSON), nullable=True, default=dict)

    # Statistics
    total_subscribers = Column(Integer, default=0)
    total_revenue = Column(DECIMAL(15, 2), default=0.0)
    average_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="strategy_submissions")
    reviewer = relationship("User", foreign_keys=[reviewer_id], backref="reviewed_strategies")

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "risk_level": self.risk_level.value if self.risk_level else "medium",
            "expected_return_range": [
                float(self.expected_return_min or 0),
                float(self.expected_return_max or 0)
            ],
            "required_capital": float(self.required_capital or 1000),
            "pricing_model": self.pricing_model.value if self.pricing_model else "free",
            "price_amount": float(self.price_amount) if self.price_amount else None,
            "profit_share_percentage": self.profit_share_percentage,
            "status": self.status.value if self.status else "draft",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "reviewer_feedback": self.reviewer_feedback,
            "rejection_reason": self.rejection_reason,
            "backtest_results": self.backtest_results or {},
            "validation_results": self.validation_results or {},
            "tags": self.tags or [],
            "target_audience": self.target_audience or [],
            "complexity_level": self.complexity_level.value if self.complexity_level else "intermediate",
            "documentation_quality": self.documentation_quality or 0,
            "support_level": self.support_level.value if self.support_level else "standard",
            "total_subscribers": self.total_subscribers or 0,
            "total_revenue": float(self.total_revenue or 0),
            "average_rating": self.average_rating or 0,
            "total_reviews": self.total_reviews or 0
        }