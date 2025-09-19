"""
User-related database models.

Contains models for user management, profiles, sessions, and activity tracking
in the multi-tenant cryptocurrency trading platform.
"""

import uuid
from datetime import datetime
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


class UserRole(str, enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"
    API_ONLY = "api_only"


class UserStatus(str, enum.Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class KYCStatus(str, enum.Enum):
    """KYC verification status."""
    NOT_STARTED = "not_started"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class User(Base):
    """
    Core user model for multi-tenant authentication and authorization.
    
    This model handles user authentication, basic profile information,
    and tenant association for the enterprise platform.
    """
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Authentication fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Role and permissions
    role = Column(Enum(UserRole), default=UserRole.TRADER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING_VERIFICATION, nullable=False)
    
    # Multi-tenant association
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
    
    # Security fields
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(32), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    
    # KYC fields
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.NOT_STARTED, nullable=False)
    kyc_verified_at = Column(DateTime, nullable=True)
    kyc_data = Column(JSON, nullable=True)
    
    # Trading preferences
    simulation_mode = Column(Boolean, default=True, nullable=False)  # Default to simulation for safety
    simulation_balance = Column(Numeric(20, 2), default=10000.00, nullable=False)  # Virtual balance in USD
    last_simulation_reset = Column(DateTime, nullable=True)

    # Referral system
    referral_code = Column(String(20), unique=True, nullable=True, index=True)
    referred_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    login_history = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    oauth_connections = relationship("UserOAuthConnection", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    tenant = relationship("Tenant", back_populates="users")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    credit_account = relationship("CreditAccount", back_populates="user", uselist=False, cascade="all, delete-orphan")
    exchange_accounts = relationship("ExchangeAccount", back_populates="user", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    strategy_access = relationship("UserStrategyAccess", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    trading_strategies = relationship("TradingStrategy", back_populates="user", cascade="all, delete-orphan")
    telegram_connections = relationship("UserTelegramConnection", back_populates="user", cascade="all, delete-orphan")
    ab_tests = relationship("ABTest", back_populates="creator", cascade="all, delete-orphan")
    strategy_performance_history = relationship("StrategyPerformanceHistory", back_populates="user", cascade="all, delete-orphan")
    backtest_results = relationship("BacktestResult", back_populates="user", cascade="all, delete-orphan")
    
    # Self-referential relationship for referrals
    referred_users = relationship("User", backref="referrer", remote_side=[id])
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_user_email_active", "email", "is_active"),
        Index("idx_user_tenant_role", "tenant_id", "role"),
        Index("idx_user_status", "status"),
        Index("idx_user_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        return self.locked_until is not None and self.locked_until > datetime.utcnow()
    
    @property
    def is_kyc_verified(self) -> bool:
        """Check if user has completed KYC verification."""
        return self.kyc_status == KYCStatus.APPROVED
    
    def can_trade(self) -> bool:
        """Check if user can perform trading operations."""
        return (
            self.is_active
            and not self.is_locked
            and self.status == UserStatus.ACTIVE
            and self.role in [UserRole.ADMIN, UserRole.TRADER]
        )
    
    @property
    def full_name(self) -> str:
        """Get user's full name from profile or email."""
        if self.profile:
            return self.profile.full_name
        return self.email.split('@')[0]
    

    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role}, status={self.status})>"


class UserProfile(Base):
    """
    Extended user profile information.
    
    Contains additional user information, preferences, and personalization
    settings for the trading platform.
    """
    
    __tablename__ = "user_profiles"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Personal information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    country = Column(String(2), nullable=True)  # ISO country code
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(5), default="en", nullable=False)  # ISO language code
    
    # Profile preferences
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    
    # Trading preferences
    default_risk_level = Column(String(20), default="medium", nullable=False)
    preferred_exchanges = Column(JSON, default=list, nullable=False)
    favorite_symbols = Column(JSON, default=list, nullable=False)
    trading_personality = Column(JSON, nullable=True)  # AI-learned personality traits
    
    # Notification preferences
    email_notifications = Column(Boolean, default=True, nullable=False)
    sms_notifications = Column(Boolean, default=False, nullable=False)
    telegram_notifications = Column(Boolean, default=False, nullable=False)
    push_notifications = Column(Boolean, default=True, nullable=False)
    
    # Privacy settings
    public_profile = Column(Boolean, default=False, nullable=False)
    show_performance = Column(Boolean, default=False, nullable=False)
    allow_copy_trading = Column(Boolean, default=False, nullable=False)
    
    # Personalization data
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    onboarding_step = Column(Integer, default=0, nullable=False)
    ui_preferences = Column(JSON, default=dict, nullable=False)
    dashboard_layout = Column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    def __repr__(self) -> str:
        return f"<UserProfile(user_id={self.user_id}, name={self.first_name} {self.last_name})>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(part for part in parts if part)
    
    @property
    def display_name(self) -> str:
        """Get display name for user."""
        if self.first_name:
            return self.first_name
        return self.user.email.split("@")[0] if hasattr(self, "user") else "User"



class UserActivity(Base):
    """
    User activity logging for audit trails and analytics.
    
    Tracks all user actions for security auditing, compliance,
    and user behavior analysis.
    """
    
    __tablename__ = "user_activities"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Activity data
    activity_type = Column(String(50), nullable=False, index=True)  # login, trade, profile_update, etc.
    activity_category = Column(String(20), nullable=False, index=True)  # auth, trading, admin, etc.
    description = Column(Text, nullable=False)
    
    # Context information
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("user_sessions.id"), nullable=True, index=True)
    
    # Activity metadata
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    meta_data = Column(JSON, nullable=True)
    
    # Risk and security
    risk_score = Column(Integer, default=0, nullable=False)  # 0-100 risk score
    flagged = Column(Boolean, default=False, nullable=False)
    
    # Timestamp
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="activities")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_activity_user_type", "user_id", "activity_type"),
        Index("idx_activity_category", "activity_category"),
        Index("idx_activity_created", "created_at"),
        Index("idx_activity_flagged", "flagged"),
        Index("idx_activity_risk", "risk_score"),
    )
    
    def __repr__(self) -> str:
        return f"<UserActivity(user_id={self.user_id}, type={self.activity_type}, success={self.success})>"
