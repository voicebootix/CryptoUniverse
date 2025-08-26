"""
Subscription and billing-related database models.

Handles subscription plans, user subscriptions, billing history,
and payment processing for the enterprise platform.
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


class SubscriptionTier(str, enum.Enum):
    """Subscription tier enumeration."""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"


class BillingInterval(str, enum.Enum):
    """Billing interval enumeration."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class PaymentStatus(str, enum.Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class SubscriptionPlan(Base):
    """
    Subscription plan definitions.
    
    Defines available subscription tiers, pricing, features,
    and limits for the enterprise platform.
    """
    
    __tablename__ = "subscription_plans"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Plan identification
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    tier = Column(Enum(SubscriptionTier), nullable=False, index=True)
    
    # Plan details
    description = Column(Text, nullable=True)
    features = Column(JSON, default=list, nullable=False)
    
    # Pricing
    price_monthly = Column(Numeric(10, 2), default=0, nullable=False)
    price_quarterly = Column(Numeric(10, 2), default=0, nullable=False)
    price_yearly = Column(Numeric(10, 2), default=0, nullable=False)
    
    # Included credits and limits
    monthly_credits_included = Column(Integer, default=0, nullable=False)
    credit_discount_percent = Column(Integer, default=0, nullable=False)
    max_api_calls_per_month = Column(Integer, default=1000, nullable=False)
    max_trades_per_month = Column(Integer, default=100, nullable=False)
    max_exchanges = Column(Integer, default=1, nullable=False)
    max_strategies = Column(Integer, default=1, nullable=False)
    max_portfolio_value_usd = Column(Integer, default=10000, nullable=False)
    
    # Feature flags
    copy_trading_enabled = Column(Boolean, default=False, nullable=False)
    api_access_enabled = Column(Boolean, default=False, nullable=False)
    advanced_analytics = Column(Boolean, default=False, nullable=False)
    priority_support = Column(Boolean, default=False, nullable=False)
    white_label_access = Column(Boolean, default=False, nullable=False)
    custom_integrations = Column(Boolean, default=False, nullable=False)
    
    # Stripe integration
    stripe_price_id_monthly = Column(String(100), nullable=True, index=True)
    stripe_price_id_quarterly = Column(String(100), nullable=True, index=True)
    stripe_price_id_yearly = Column(String(100), nullable=True, index=True)
    
    # Plan metadata
    is_active = Column(Boolean, default=True, nullable=False)
    is_popular = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")
    
    # Indexes
    __table_args__ = (
        Index("idx_plan_tier_active", "tier", "is_active"),
        Index("idx_plan_sort", "sort_order"),
    )
    
    def __repr__(self) -> str:
        return f"<SubscriptionPlan(name={self.name}, tier={self.tier})>"
    
    def get_price(self, billing_interval: BillingInterval) -> Decimal:
        """Get price for specific billing interval."""
        price_map = {
            BillingInterval.MONTHLY: self.price_monthly,
            BillingInterval.QUARTERLY: self.price_quarterly,
            BillingInterval.YEARLY: self.price_yearly,
        }
        return price_map.get(billing_interval, self.price_monthly)
    
    def get_stripe_price_id(self, billing_interval: BillingInterval) -> Optional[str]:
        """Get Stripe price ID for billing interval."""
        price_map = {
            BillingInterval.MONTHLY: self.stripe_price_id_monthly,
            BillingInterval.QUARTERLY: self.stripe_price_id_quarterly,
            BillingInterval.YEARLY: self.stripe_price_id_yearly,
        }
        return price_map.get(billing_interval)
    
    def has_feature(self, feature: str) -> bool:
        """Check if plan includes specific feature."""
        return feature in self.features


class Subscription(Base):
    """
    User subscription tracking.
    
    Manages individual user subscriptions, billing cycles,
    and subscription lifecycle events.
    """
    
    __tablename__ = "subscriptions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False, index=True)
    
    # Subscription details
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.INACTIVE, nullable=False, index=True)
    billing_interval = Column(Enum(BillingInterval), default=BillingInterval.MONTHLY, nullable=False)
    
    # Billing information
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    next_billing_date = Column(DateTime, nullable=True)
    
    # Trial information
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    
    # Stripe integration
    stripe_customer_id = Column(String(100), nullable=True, index=True)
    stripe_subscription_id = Column(String(100), nullable=True, unique=True, index=True)
    stripe_payment_method_id = Column(String(100), nullable=True)
    
    # Usage tracking
    api_calls_this_month = Column(Integer, default=0, nullable=False)
    trades_this_month = Column(Integer, default=0, nullable=False)
    credits_used_this_month = Column(Integer, default=0, nullable=False)
    
    # Subscription modifications
    pending_changes = Column(JSON, nullable=True)  # Scheduled plan changes
    canceled_at = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    cancellation_reason = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    billing_history = relationship("BillingHistory", back_populates="subscription", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_subscription_status", "status"),
        Index("idx_subscription_billing_date", "next_billing_date"),
        Index("idx_subscription_stripe", "stripe_subscription_id"),
    )
    
    def __repr__(self) -> str:
        return f"<Subscription(user_id={self.user_id}, plan={self.plan.name if self.plan else 'None'})>"
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status == SubscriptionStatus.ACTIVE
    
    @property
    def is_trialing(self) -> bool:
        """Check if subscription is in trial period."""
        return (
            self.status == SubscriptionStatus.TRIALING
            and self.trial_end
            and datetime.utcnow() < self.trial_end
        )
    
    @property
    def is_past_due(self) -> bool:
        """Check if subscription is past due."""
        return self.status == SubscriptionStatus.PAST_DUE
    
    @property
    def days_until_renewal(self) -> Optional[int]:
        """Calculate days until next billing."""
        if not self.next_billing_date:
            return None
        delta = self.next_billing_date - datetime.utcnow()
        return delta.days if delta.days >= 0 else 0
    
    def is_usage_limit_exceeded(self, usage_type: str) -> bool:
        """Check if usage limit is exceeded for given type."""
        if not self.plan:
            return True
        
        limits = {
            "api_calls": (self.api_calls_this_month, self.plan.max_api_calls_per_month),
            "trades": (self.trades_this_month, self.plan.max_trades_per_month),
        }
        
        if usage_type in limits:
            current, limit = limits[usage_type]
            return current >= limit
        
        return False
    
    def get_usage_percentage(self, usage_type: str) -> float:
        """Get usage percentage for given type."""
        if not self.plan:
            return 100.0
        
        limits = {
            "api_calls": (self.api_calls_this_month, self.plan.max_api_calls_per_month),
            "trades": (self.trades_this_month, self.plan.max_trades_per_month),
        }
        
        if usage_type in limits:
            current, limit = limits[usage_type]
            return min((current / limit) * 100, 100.0) if limit > 0 else 0.0
        
        return 0.0


class BillingHistory(Base):
    """
    Billing and payment history.
    
    Tracks all billing events, payments, refunds, and financial
    transactions for audit and accounting purposes.
    """
    
    __tablename__ = "billing_history"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)
    
    # Transaction details
    transaction_type = Column(String(50), nullable=False, index=True)  # payment, refund, credit, etc.
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    description = Column(Text, nullable=False)
    
    # Payment status
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    
    # External references
    stripe_payment_intent_id = Column(String(100), nullable=True, index=True)
    stripe_invoice_id = Column(String(100), nullable=True, index=True)
    stripe_charge_id = Column(String(100), nullable=True, index=True)
    
    # Payment method
    payment_method_type = Column(String(50), nullable=True)  # card, bank_transfer, etc.
    payment_method_last4 = Column(String(4), nullable=True)
    payment_method_brand = Column(String(20), nullable=True)
    
    # Billing period
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    
    # Metadata
    meta_data = Column(JSON, nullable=True)
    failure_reason = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    paid_at = Column(DateTime, nullable=True)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="billing_history")
    
    # Indexes
    __table_args__ = (
        Index("idx_billing_type_status", "transaction_type", "status"),
        Index("idx_billing_created", "created_at"),
        Index("idx_billing_stripe_payment", "stripe_payment_intent_id"),
    )
    
    def __repr__(self) -> str:
        return f"<BillingHistory(subscription_id={self.subscription_id}, amount={self.amount}, status={self.status})>"
    
    @property
    def is_successful(self) -> bool:
        """Check if payment was successful."""
        return self.status == PaymentStatus.SUCCEEDED
    
    @property
    def is_failed(self) -> bool:
        """Check if payment failed."""
        return self.status == PaymentStatus.FAILED
    
    @property
    def is_refunded(self) -> bool:
        """Check if payment was refunded."""
        return self.status == PaymentStatus.REFUNDED
