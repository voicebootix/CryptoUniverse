"""
Tenant-related database models for multi-tenancy support.

Handles tenant isolation, settings, and organization management
for the enterprise cryptocurrency trading platform.
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


class TenantType(str, enum.Enum):
    """Tenant type enumeration."""
    INDIVIDUAL = "individual"  # Personal traders
    TEAM = "team"             # Small teams/family offices
    ORGANIZATION = "organization"  # Companies
    ENTERPRISE = "enterprise"     # Large enterprises
    WHITE_LABEL = "white_label"   # White-label partners


class TenantStatus(str, enum.Enum):
    """Tenant status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"


class Tenant(Base):
    """
    Multi-tenant organization model.
    
    Provides complete tenant isolation for enterprise customers,
    white-label partners, and organizational users.
    """
    
    __tablename__ = "tenants"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Basic information
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # URL-friendly identifier
    description = Column(Text, nullable=True)
    
    # Tenant type and status
    tenant_type = Column(Enum(TenantType), default=TenantType.INDIVIDUAL, nullable=False)
    status = Column(Enum(TenantStatus), default=TenantStatus.TRIAL, nullable=False)
    
    # Contact information
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(20), nullable=True)
    website = Column(String(500), nullable=True)
    
    # Business information
    company_name = Column(String(200), nullable=True)
    tax_id = Column(String(50), nullable=True)
    registration_number = Column(String(100), nullable=True)
    
    # Address information
    address = Column(JSON, nullable=True)  # Street, city, state, country, postal_code
    billing_address = Column(JSON, nullable=True)
    
    # Branding (for white-label)
    logo_url = Column(String(500), nullable=True)
    brand_colors = Column(JSON, nullable=True)  # Primary, secondary, accent colors
    custom_domain = Column(String(200), nullable=True, unique=True, index=True)
    
    # Limits and quotas
    max_users = Column(Integer, default=1, nullable=False)
    max_api_calls_per_month = Column(Integer, default=10000, nullable=False)
    max_trading_volume_usd = Column(Integer, default=100000, nullable=False)
    
    # Features and permissions
    features_enabled = Column(JSON, default=list, nullable=False)
    custom_features = Column(JSON, default=dict, nullable=False)
    
    # Trial and subscription
    trial_ends_at = Column(DateTime, nullable=True)
    subscription_started_at = Column(DateTime, nullable=True)
    
    # Compliance and security
    compliance_level = Column(String(20), default="basic", nullable=False)  # basic, enhanced, enterprise
    data_retention_days = Column(Integer, default=2555, nullable=False)  # 7 years default
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    settings = relationship("TenantSettings", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_tenant_slug", "slug"),
        Index("idx_tenant_type_status", "tenant_type", "status"),
        Index("idx_tenant_domain", "custom_domain"),
        Index("idx_tenant_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, type={self.tenant_type})>"
    
    @property
    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.status == TenantStatus.ACTIVE
    
    @property
    def is_trial(self) -> bool:
        """Check if tenant is on trial."""
        return self.status == TenantStatus.TRIAL
    
    @property
    def trial_expired(self) -> bool:
        """Check if trial has expired."""
        if not self.is_trial or not self.trial_ends_at:
            return False
        return datetime.utcnow() > self.trial_ends_at
    
    @property
    def is_enterprise(self) -> bool:
        """Check if tenant is enterprise level."""
        return self.tenant_type == TenantType.ENTERPRISE
    
    @property
    def is_white_label(self) -> bool:
        """Check if tenant is white-label partner."""
        return self.tenant_type == TenantType.WHITE_LABEL
    
    def has_feature(self, feature_name: str) -> bool:
        """Check if tenant has specific feature enabled."""
        return feature_name in self.features_enabled
    
    def get_user_count(self) -> int:
        """Get current number of users in tenant."""
        return len(self.users) if self.users else 0
    
    def can_add_user(self) -> bool:
        """Check if tenant can add more users."""
        return self.get_user_count() < self.max_users


class TenantSettings(Base):
    """
    Tenant-specific settings and configuration.
    
    Stores customizable settings, preferences, and configuration
    options for each tenant.
    """
    
    __tablename__ = "tenant_settings"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    
    # General settings
    timezone = Column(String(50), default="UTC", nullable=False)
    default_currency = Column(String(3), default="USD", nullable=False)
    date_format = Column(String(20), default="YYYY-MM-DD", nullable=False)
    number_format = Column(String(20), default="en-US", nullable=False)
    
    # Trading settings
    default_risk_profile = Column(String(20), default="balanced", nullable=False)
    allowed_exchanges = Column(JSON, default=list, nullable=False)
    default_execution_mode = Column(String(20), default="balanced", nullable=False)
    max_position_size_percent = Column(Integer, default=10, nullable=False)
    
    # Risk management
    global_stop_loss_percent = Column(Integer, default=20, nullable=False)
    daily_loss_limit_percent = Column(Integer, default=5, nullable=False)
    max_open_positions = Column(Integer, default=10, nullable=False)
    risk_monitoring_enabled = Column(Boolean, default=True, nullable=False)
    
    # Notification settings
    email_alerts = Column(Boolean, default=True, nullable=False)
    sms_alerts = Column(Boolean, default=False, nullable=False)
    telegram_alerts = Column(Boolean, default=False, nullable=False)
    webhook_url = Column(String(500), nullable=True)
    
    # API settings
    rate_limit_per_minute = Column(Integer, default=100, nullable=False)
    api_access_enabled = Column(Boolean, default=True, nullable=False)
    webhook_secret = Column(String(64), nullable=True)
    
    # Copy trading settings
    copy_trading_enabled = Column(Boolean, default=False, nullable=False)
    strategy_publishing_enabled = Column(Boolean, default=False, nullable=False)
    min_strategy_performance_days = Column(Integer, default=30, nullable=False)
    max_followers_per_strategy = Column(Integer, default=1000, nullable=False)
    
    # White-label settings
    custom_branding_enabled = Column(Boolean, default=False, nullable=False)
    custom_logo_url = Column(String(500), nullable=True)
    custom_theme = Column(JSON, nullable=True)
    custom_footer = Column(Text, nullable=True)
    
    # Compliance settings
    kyc_required = Column(Boolean, default=False, nullable=False)
    aml_checks_enabled = Column(Boolean, default=False, nullable=False)
    audit_logging_level = Column(String(20), default="standard", nullable=False)
    data_export_enabled = Column(Boolean, default=True, nullable=False)
    
    # Feature toggles
    simulation_mode_default = Column(Boolean, default=True, nullable=False)
    advanced_analytics_enabled = Column(Boolean, default=False, nullable=False)
    social_trading_enabled = Column(Boolean, default=False, nullable=False)
    portfolio_sharing_enabled = Column(Boolean, default=False, nullable=False)
    
    # Integration settings
    external_apis = Column(JSON, default=dict, nullable=False)
    webhook_endpoints = Column(JSON, default=list, nullable=False)
    sso_settings = Column(JSON, nullable=True)
    
    # Custom settings
    custom_settings = Column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="settings")
    
    def __repr__(self) -> str:
        return f"<TenantSettings(tenant_id={self.tenant_id}, timezone={self.timezone})>"
    
    def get_setting(self, key: str, default=None):
        """Get a custom setting value."""
        return self.custom_settings.get(key, default)
    
    def set_setting(self, key: str, value):
        """Set a custom setting value."""
        if not self.custom_settings:
            self.custom_settings = {}
        self.custom_settings[key] = value
    
    def is_exchange_allowed(self, exchange: str) -> bool:
        """Check if exchange is allowed for this tenant."""
        return exchange.lower() in [ex.lower() for ex in self.allowed_exchanges]
    
    def get_risk_limits(self) -> dict:
        """Get all risk limits as a dictionary."""
        return {
            "max_position_size_percent": self.max_position_size_percent,
            "global_stop_loss_percent": self.global_stop_loss_percent,
            "daily_loss_limit_percent": self.daily_loss_limit_percent,
            "max_open_positions": self.max_open_positions,
        }
