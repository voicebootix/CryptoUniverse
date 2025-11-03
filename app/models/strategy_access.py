#!/usr/bin/env python3
"""
Enterprise Strategy Access Model
Unified strategy ownership and access control
"""

import enum
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class StrategyAccessType(enum.Enum):
    """Strategy access types for enterprise control"""
    WELCOME = "welcome"  # Free onboarding strategies
    PURCHASED = "purchased"  # Paid strategies
    TRIAL = "trial"  # Trial access
    ADMIN_GRANT = "admin_grant"  # Admin granted access
    ENTERPRISE_LICENSE = "enterprise_license"  # Enterprise-wide access


class StrategyType(enum.Enum):
    """Strategy source types"""
    AI_STRATEGY = "ai_strategy"  # AI catalog strategies
    COMMUNITY_STRATEGY = "community_strategy"  # User-published strategies
    ENTERPRISE_STRATEGY = "enterprise_strategy"  # Enterprise custom strategies


class UserStrategyAccess(Base):
    """
    Enterprise unified strategy access control.

    This replaces the fragmented Redis-based system with a reliable,
    auditable, and scalable database solution.
    """
    __tablename__ = "user_strategy_access"

    # Primary key
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User relationship
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who has access to the strategy"
    )

    # Strategy identification
    strategy_id = Column(
        String(255),
        nullable=False,
        comment="Strategy identifier - AI catalog key or community strategy UUID"
    )

    strategy_type = Column(
        ENUM(StrategyType, name="strategytype"),
        nullable=False,
        comment="Type of strategy for proper routing"
    )

    # Access control
    access_type = Column(
        ENUM(StrategyAccessType, name="strategyaccesstype"),
        nullable=False,
        comment="How the user gained access to this strategy"
    )

    subscription_type = Column(
        String(50),
        nullable=False,
        default="monthly",
        comment="Subscription model: monthly, permanent, trial"
    )

    credits_paid = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Credits paid for this strategy access"
    )

    # Time-based access control
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Expiration time - NULL for permanent access"
    )

    activated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When access was first activated"
    )

    last_used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time strategy was executed or viewed"
    )

    # Status
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether access is currently active"
    )

    # Strategy-specific configuration
    metadata_json = Column(
        'metadata',  # Keep DB column name as 'metadata'
        JSONB,
        nullable=True,
        comment="Strategy-specific settings, parameters, and configuration"
    )

    # Audit timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="strategy_access")

    # Table constraints and indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'strategy_id', name='uq_user_strategy_access'),
        Index('idx_user_strategy_access_user_id', 'user_id'),
        Index('idx_user_strategy_access_strategy_id', 'strategy_id'),
        Index('idx_user_strategy_access_active', 'user_id', 'is_active'),
        Index('idx_user_strategy_access_active_expires', 'user_id', 'is_active', 'expires_at'),
        Index('idx_user_strategy_access_expires', 'expires_at'),
        {"comment": "Enterprise unified strategy access control"}
    )

    def __repr__(self) -> str:
        return f"<UserStrategyAccess(user_id={self.user_id}, strategy_id={self.strategy_id}, access_type={self.access_type})>"

    def is_expired(self) -> bool:
        """Check if access has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow().replace(tzinfo=None) > self.expires_at.replace(tzinfo=None)

    def is_valid(self) -> bool:
        """Check if access is valid and active"""
        return self.is_active and not self.is_expired()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "strategy_id": self.strategy_id,
            "strategy_type": self.strategy_type.value,
            "access_type": self.access_type.value,
            "subscription_type": self.subscription_type,
            "credits_paid": self.credits_paid,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "activated_at": self.activated_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "is_active": self.is_active,
            "is_valid": self.is_valid(),
            "metadata": self.metadata_json or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }