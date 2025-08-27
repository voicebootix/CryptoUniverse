"""
Credit system database models.

Handles credit-based profit limits, credit transactions, credit packs,
and the tokenomics foundation for the enterprise platform.
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


class CreditTransactionType(str, enum.Enum):
    """Credit transaction type enumeration."""
    PURCHASE = "purchase"           # Credit pack purchase
    USAGE = "usage"                # Credits used for profit realization
    REFUND = "refund"              # Credit refund
    BONUS = "bonus"                # Bonus credits (referral, loyalty, etc.)
    EXPIRY = "expiry"              # Credit expiration
    TRANSFER = "transfer"          # Credit transfer between users
    ADJUSTMENT = "adjustment"      # Admin adjustment


class CreditStatus(str, enum.Enum):
    """Credit status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    USED = "used"
    REFUNDED = "refunded"


class CreditPackType(str, enum.Enum):
    """Credit pack type enumeration."""
    STARTER = "starter"
    PREMIUM = "premium" 
    PRO = "pro"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class CreditAccount(Base):
    """
    User credit account tracking.
    
    Manages user credit balances, profit limits, and credit usage
    for the credit-based profit system ($0.10 per credit = $1 profit potential).
    """
    
    __tablename__ = "credit_accounts"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Credit balances
    total_credits = Column(Integer, default=0, nullable=False)
    available_credits = Column(Integer, default=0, nullable=False)
    used_credits = Column(Integer, default=0, nullable=False)
    expired_credits = Column(Integer, default=0, nullable=False)
    
    # Profit tracking
    total_profit_realized_usd = Column(Numeric(15, 2), default=0, nullable=False)
    total_profit_potential_usd = Column(Numeric(15, 2), default=0, nullable=False)
    current_profit_limit_usd = Column(Numeric(15, 2), default=0, nullable=False)
    
    # Credit value settings (configurable per user for VIP customers)
    credit_to_usd_ratio = Column(Numeric(5, 2), default=10.0, nullable=False)  # 10 credits = $1 profit
    
    # VIP and bonus settings
    is_vip = Column(Boolean, default=False, nullable=False)
    vip_bonus_percentage = Column(Integer, default=0, nullable=False)
    referral_bonus_credits = Column(Integer, default=0, nullable=False)
    loyalty_bonus_credits = Column(Integer, default=0, nullable=False)
    
    # Usage statistics
    monthly_credits_used = Column(Integer, default=0, nullable=False)
    monthly_profit_realized_usd = Column(Numeric(12, 2), default=0, nullable=False)
    last_usage_reset = Column(DateTime, default=func.now(), nullable=False)
    
    # Account settings
    auto_purchase_enabled = Column(Boolean, default=False, nullable=False)
    auto_purchase_threshold = Column(Integer, default=100, nullable=False)
    auto_purchase_amount = Column(Integer, default=1000, nullable=False)
    
    # Notifications
    low_balance_alert_threshold = Column(Integer, default=100, nullable=False)
    profit_limit_warning_threshold = Column(Integer, default=90, nullable=False)  # % of limit
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_purchase_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="credit_account")
    transactions = relationship("CreditTransaction", back_populates="account", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<CreditAccount(user_id={self.user_id}, balance={self.available_credits})>"
    
    @property
    def credit_balance_percentage(self) -> float:
        """Calculate credit balance as percentage of total purchased."""
        if self.total_credits == 0:
            return 0.0
        return (self.available_credits / self.total_credits) * 100
    
    @property
    def profit_limit_used_percentage(self) -> float:
        """Calculate how much of profit limit has been used."""
        if self.current_profit_limit_usd == 0:
            return 0.0
        return (self.total_profit_realized_usd / self.current_profit_limit_usd) * 100
    
    @property
    def is_low_balance(self) -> bool:
        """Check if credit balance is below alert threshold."""
        return self.available_credits <= self.low_balance_alert_threshold
    
    @property
    def is_profit_limit_warning(self) -> bool:
        """Check if approaching profit limit."""
        return self.profit_limit_used_percentage >= self.profit_limit_warning_threshold
    
    @property
    def is_profit_limit_exceeded(self) -> bool:
        """Check if profit limit is exceeded."""
        return self.total_profit_realized_usd >= self.current_profit_limit_usd
    
    def calculate_profit_potential(self) -> Decimal:
        """Calculate remaining profit potential in USD."""
        return Decimal(self.available_credits) / self.credit_to_usd_ratio
    
    def can_realize_profit(self, profit_amount_usd: Decimal) -> tuple[bool, str]:
        """
        Check if user can realize specific profit amount.
        
        Returns:
            tuple: (can_realize, reason)
        """
        if self.is_profit_limit_exceeded:
            return False, "Profit limit already exceeded"
        
        remaining_limit = self.current_profit_limit_usd - self.total_profit_realized_usd
        if profit_amount_usd > remaining_limit:
            return False, f"Profit amount exceeds remaining limit (${remaining_limit})"
        
        required_credits = int(profit_amount_usd * self.credit_to_usd_ratio)
        if required_credits > self.available_credits:
            return False, f"Insufficient credits (need {required_credits}, have {self.available_credits})"
        
        return True, "OK"
    
    def deduct_credits_for_profit(self, profit_amount_usd: Decimal) -> int:
        """Calculate credits to deduct for realized profit."""
        return int(profit_amount_usd * self.credit_to_usd_ratio)


class CreditTransaction(Base):
    """
    Credit transaction history.
    
    Tracks all credit movements, purchases, usage, and adjustments
    for complete audit trail and financial reconciliation.
    """
    
    __tablename__ = "credit_transactions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("credit_accounts.id"), nullable=False, index=True)
    
    # Transaction details
    transaction_type = Column(Enum(CreditTransactionType), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # Can be negative for deductions
    description = Column(Text, nullable=False)
    
    # Balances after transaction
    balance_before = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    
    # Related entities
    trade_id = Column(UUID(as_uuid=True), ForeignKey("trades.id"), nullable=True, index=True)  # If related to trade
    credit_pack_id = Column(UUID(as_uuid=True), ForeignKey("credit_packs.id"), nullable=True, index=True)  # If from pack purchase
    
    # Financial information
    usd_value = Column(Numeric(12, 2), nullable=True)  # USD value of transaction
    profit_amount_usd = Column(Numeric(12, 2), nullable=True)  # Profit that triggered usage
    
    # External references
    stripe_payment_intent_id = Column(String(100), nullable=True, index=True)
    billing_history_id = Column(UUID(as_uuid=True), ForeignKey("billing_history.id"), nullable=True, index=True)
    
    # Transaction metadata
    meta_data = Column(JSON, nullable=True)
    source = Column(String(50), nullable=False)  # web, api, mobile, system
    ip_address = Column(String(45), nullable=True)
    
    # Expiry tracking
    expires_at = Column(DateTime, nullable=True)
    expired_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(Enum(CreditStatus), default=CreditStatus.ACTIVE, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    processed_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    account = relationship("CreditAccount", back_populates="transactions")
    credit_pack = relationship("CreditPack", back_populates="transactions")
    
    # Indexes
    __table_args__ = (
        Index("idx_transaction_type_created", "transaction_type", "created_at"),
        Index("idx_transaction_account_type", "account_id", "transaction_type"),
        Index("idx_transaction_trade", "trade_id"),
        Index("idx_transaction_expires", "expires_at"),
    )
    
    def __repr__(self) -> str:
        return f"<CreditTransaction(account_id={self.account_id}, type={self.transaction_type}, amount={self.amount})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if transaction/credits are expired."""
        return (
            self.expires_at is not None
            and datetime.utcnow() > self.expires_at
            and self.status == CreditStatus.ACTIVE
        )
    
    @property
    def is_credit(self) -> bool:
        """Check if transaction adds credits."""
        return self.amount > 0
    
    @property
    def is_debit(self) -> bool:
        """Check if transaction deducts credits."""
        return self.amount < 0


class CreditPack(Base):
    """
    Credit pack definitions and purchases.
    
    Manages credit pack offerings, pricing, and purchase tracking
    with volume discounts and promotional features.
    """
    
    __tablename__ = "credit_packs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Pack identification
    name = Column(String(100), nullable=False)
    pack_type = Column(Enum(CreditPackType), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Pack contents
    credits_amount = Column(Integer, nullable=False)
    usd_price = Column(Numeric(10, 2), nullable=False)
    profit_potential_usd = Column(Numeric(12, 2), nullable=False)
    
    # Discounts and bonuses
    discount_percentage = Column(Integer, default=0, nullable=False)
    bonus_credits = Column(Integer, default=0, nullable=False)
    bulk_discount_threshold = Column(Integer, nullable=True)  # Min quantity for bulk discount
    bulk_discount_percentage = Column(Integer, default=0, nullable=False)
    
    # Pack features
    features = Column(JSON, default=list, nullable=False)
    is_popular = Column(Boolean, default=False, nullable=False)
    is_limited_time = Column(Boolean, default=False, nullable=False)
    valid_until = Column(DateTime, nullable=True)
    
    # Credit settings
    credits_expire_days = Column(Integer, default=365, nullable=False)  # Credit validity period
    
    # Stripe integration
    stripe_price_id = Column(String(100), nullable=True, index=True)
    stripe_product_id = Column(String(100), nullable=True, index=True)
    
    # Availability
    is_active = Column(Boolean, default=True, nullable=False)
    max_purchases_per_user = Column(Integer, nullable=True)
    min_user_level = Column(String(20), nullable=True)  # Minimum user level required
    
    # Analytics
    total_purchases = Column(Integer, default=0, nullable=False)
    total_revenue = Column(Numeric(15, 2), default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    transactions = relationship("CreditTransaction", back_populates="credit_pack")
    
    # Indexes
    __table_args__ = (
        Index("idx_pack_type_active", "pack_type", "is_active"),
        Index("idx_pack_popular", "is_popular"),
        Index("idx_pack_stripe", "stripe_price_id"),
    )
    
    def __repr__(self) -> str:
        return f"<CreditPack(name={self.name}, credits={self.credits_amount}, price=${self.usd_price})>"
    
    @property
    def credits_per_dollar(self) -> float:
        """Calculate credits per dollar value."""
        if self.usd_price == 0:
            return 0.0
        return float(self.credits_amount / self.usd_price)
    
    @property
    def effective_credits(self) -> int:
        """Calculate effective credits including bonuses."""
        return self.credits_amount + self.bonus_credits
    
    @property
    def is_available(self) -> bool:
        """Check if pack is currently available for purchase."""
        if not self.is_active:
            return False
        
        if self.is_limited_time and self.valid_until:
            return datetime.utcnow() < self.valid_until
        
        return True
    
    def calculate_bulk_price(self, quantity: int) -> Decimal:
        """Calculate price with bulk discount if applicable."""
        base_price = self.usd_price * quantity
        
        if (self.bulk_discount_threshold and 
            quantity >= self.bulk_discount_threshold and 
            self.bulk_discount_percentage > 0):
            
            discount = base_price * (self.bulk_discount_percentage / 100)
            return base_price - discount
        
        return base_price
    
    def get_total_credits(self, quantity: int) -> int:
        """Get total credits for given quantity including bonuses."""
        return (self.credits_amount + self.bonus_credits) * quantity
    
    @classmethod
    def get_recommended_packs(cls):
        """Get recommended credit packs for display."""
        # This would typically be implemented as a class method
        # that returns the most popular or best value packs
        pass
