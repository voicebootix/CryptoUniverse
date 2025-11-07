"""
Exchange-related database models.

Handles exchange accounts, API key management, balances,
and exchange integrations for the cryptocurrency trading platform.
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


class ExchangeType(str, enum.Enum):
    """Exchange type enumeration."""
    SPOT = "spot"
    FUTURES = "futures"
    MARGIN = "margin"
    OPTIONS = "options"


class ExchangeStatus(str, enum.Enum):
    """Exchange status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    SUSPENDED = "suspended"


class ApiKeyStatus(str, enum.Enum):
    """API key status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    INVALID = "invalid"
    SUSPENDED = "suspended"


class ExchangeAccount(Base):
    """
    User exchange account management.
    
    Manages user connections to various cryptocurrency exchanges
    with support for multiple account types and trading modes.
    """
    
    __tablename__ = "exchange_accounts"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Exchange details
    exchange_name = Column(String(50), nullable=False, index=True)  # binance, kraken, kucoin, etc.
    exchange_type = Column(Enum(ExchangeType), default=ExchangeType.SPOT, nullable=False)
    account_type = Column(String(20), default="trading", nullable=False)  # trading, margin, futures
    
    # Account identification
    account_name = Column(String(100), nullable=False)  # User-defined name
    exchange_account_id = Column(String(100), nullable=True)  # Exchange's account ID
    
    # Status and health
    status = Column(Enum(ExchangeStatus), default=ExchangeStatus.INACTIVE, nullable=False, index=True)
    is_default = Column(Boolean, default=False, nullable=False)
    is_simulation = Column(Boolean, default=True, nullable=False)  # Testnet/paper trading
    
    # Trading settings
    trading_enabled = Column(Boolean, default=True, nullable=False)
    max_daily_trades = Column(Integer, default=100, nullable=False)
    max_position_size_usd = Column(Numeric(15, 2), default=1000, nullable=False)
    allowed_symbols = Column(JSON, default=list, nullable=False)  # Empty = all allowed
    
    # Risk settings
    daily_loss_limit_usd = Column(Numeric(12, 2), default=500, nullable=False)
    max_open_positions = Column(Integer, default=10, nullable=False)
    stop_loss_required = Column(Boolean, default=True, nullable=False)
    
    # Connection settings
    rate_limit_per_minute = Column(Integer, default=100, nullable=False)
    timeout_seconds = Column(Integer, default=30, nullable=False)
    retry_attempts = Column(Integer, default=3, nullable=False)
    
    # Health monitoring
    last_connection_test = Column(DateTime, nullable=True)
    last_successful_request = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    total_requests = Column(Integer, default=0, nullable=False)
    successful_requests = Column(Integer, default=0, nullable=False)
    
    # Usage statistics
    trades_today = Column(Integer, default=0, nullable=False)
    daily_loss_usd = Column(Numeric(12, 2), default=0, nullable=False)
    last_trade_at = Column(DateTime, nullable=True)
    last_reset_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="exchange_accounts")
    api_keys = relationship("ExchangeApiKey", back_populates="account", cascade="all, delete-orphan")
    balances = relationship("ExchangeBalance", back_populates="account", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="exchange_account")
    orders = relationship("Order", back_populates="exchange_account")
    positions = relationship("Position", back_populates="exchange_account")
    
    # Composite indexes and constraints for performance optimization
    __table_args__ = (
        # Unique constraint for user + exchange + account name
        UniqueConstraint("user_id", "exchange_name", "account_name", name="unique_user_exchange_account"),
        # Performance indexes for common query patterns
        Index("idx_exchange_user_status", "user_id", "status"),
        Index('idx_exchange_accounts_user_exchange_status', 'user_id', 'exchange_name', 'status'),
        Index('idx_exchange_accounts_status_trading', 'status', 'trading_enabled'),
        Index('idx_exchange_accounts_user_trading', 'user_id', 'trading_enabled'),
        Index('idx_exchange_accounts_status_trading_user', 'status', 'trading_enabled', 'user_id'),
        Index('idx_exchange_accounts_user_default', 'user_id', 'is_default', 'status'),
        Index("idx_exchange_name_status", "exchange_name", "status"),
        Index("idx_exchange_default", "is_default"),
    )
    
    def __repr__(self) -> str:
        return f"<ExchangeAccount(user_id={self.user_id}, exchange={self.exchange_name}, name={self.account_name})>"
    
    @property
    def is_healthy(self) -> bool:
        """Check if exchange account is healthy."""
        return (
            self.status == ExchangeStatus.ACTIVE
            and self.consecutive_failures < 3
            and self.trading_enabled
        )
    
    @property
    def success_rate(self) -> float:
        """Calculate API request success rate."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def can_trade_today(self) -> bool:
        """Check if can still trade today."""
        return (
            self.trades_today < self.max_daily_trades
            and self.daily_loss_usd < self.daily_loss_limit_usd
            and self.is_healthy
        )
    
    def reset_daily_limits(self) -> None:
        """Reset daily trading limits."""
        self.trades_today = 0
        self.daily_loss_usd = Decimal("0")
        self.last_reset_at = datetime.utcnow()
    
    def is_symbol_allowed(self, symbol: str) -> bool:
        """Check if symbol is allowed for trading."""
        if not self.allowed_symbols:
            return True  # Empty list means all symbols allowed
        return symbol.upper() in [s.upper() for s in self.allowed_symbols]


class ExchangeApiKey(Base):
    """
    Encrypted API key storage for exchange accounts.
    
    Securely stores and manages API keys with AES-256 encryption,
    permission tracking, and automatic rotation support.
    """
    
    __tablename__ = "exchange_api_keys"
    
    # Primary key (EXACTLY matching your Supabase schema)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("exchange_accounts.id"), nullable=False, index=True)
    
    # Key identification 
    key_name = Column(String(100), nullable=False)
    key_type = Column(String(20), default="trading", nullable=False)
    
    # Encrypted key data (AES-256 encrypted)
    encrypted_api_key = Column(Text, nullable=False)
    encrypted_secret_key = Column(Text, nullable=False)
    encrypted_passphrase = Column(Text, nullable=True)  # For exchanges that require it (KuCoin)
    
    # Key metadata
    key_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash for duplicate detection
    permissions = Column(JSON, default=list, nullable=False)  # spot, futures, margin, etc.
    ip_restrictions = Column(JSON, default=list, nullable=False)  # Allowed IP addresses
    
    # Status and validation
    status = Column(Enum(ApiKeyStatus), default=ApiKeyStatus.INACTIVE, nullable=False, index=True)
    is_validated = Column(Boolean, default=False, nullable=False)
    validation_error = Column(Text, nullable=True)
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0, nullable=False)
    failed_requests = Column(Integer, default=0, nullable=False)
    
    # Security settings
    expires_at = Column(DateTime, nullable=True)
    rotation_required = Column(Boolean, default=False, nullable=False)
    last_rotation_at = Column(DateTime, nullable=True)
    
    # Audit trail
    created_by_ip = Column(String(45), nullable=True)
    last_modified_ip = Column(String(45), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    validated_at = Column(DateTime, nullable=True)
    
    # Relationships
    account = relationship("ExchangeAccount", back_populates="api_keys")
    
    # Indexes
    __table_args__ = (
        Index("idx_api_key_account_status", "account_id", "status"),
        Index("idx_api_key_hash", "key_hash"),
        Index("idx_api_key_expires", "expires_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ExchangeApiKey(account_id={self.account_id}, name={self.key_name}, status={self.status})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if API key is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_active(self) -> bool:
        """Check if API key is active and usable."""
        return (
            self.status == ApiKeyStatus.ACTIVE
            and self.is_validated
            and not self.is_expired
        )
    
    @property
    def success_rate(self) -> float:
        """Calculate API key success rate."""
        if self.total_requests == 0:
            return 100.0
        return ((self.total_requests - self.failed_requests) / self.total_requests) * 100
    
    def has_permission(self, permission: str) -> bool:
        """Check if API key has specific permission."""
        return permission.lower() in [p.lower() for p in self.permissions]
    
    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed for this key."""
        if not self.ip_restrictions:
            return True  # No restrictions means all IPs allowed
        return ip_address in self.ip_restrictions


class ExchangeBalance(Base):
    """
    Real-time balance tracking for exchange accounts.
    
    Tracks balances, locked amounts, and balance history
    across different cryptocurrencies and fiat currencies.
    """
    
    __tablename__ = "exchange_balances"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("exchange_accounts.id"), nullable=False, index=True)
    
    # Asset information
    symbol = Column(String(20), nullable=False, index=True)  # BTC, ETH, USDT, etc.
    asset_type = Column(String(20), default="crypto", nullable=False)  # crypto, fiat
    
    # Balance amounts
    total_balance = Column(Numeric(25, 8), default=0, nullable=False)
    available_balance = Column(Numeric(25, 8), default=0, nullable=False)
    locked_balance = Column(Numeric(25, 8), default=0, nullable=False)
    
    # USD values (for reporting and limits)
    usd_value = Column(Numeric(15, 2), default=0, nullable=False)
    avg_cost_basis = Column(Numeric(15, 8), nullable=True)
    
    # Balance tracking
    last_sync_balance = Column(Numeric(25, 8), nullable=True)
    balance_change_24h = Column(Numeric(25, 8), default=0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    sync_enabled = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    
    # Relationships
    account = relationship("ExchangeAccount", back_populates="balances")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("account_id", "symbol", name="unique_account_symbol_balance"),
        Index("idx_balance_account_symbol", "account_id", "symbol"),
        Index("idx_balance_account_active", "account_id", "is_active", "symbol"),
        Index("idx_balance_symbol_usd", "symbol", "usd_value"),
        Index("idx_balance_updated", "updated_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ExchangeBalance(account_id={self.account_id}, symbol={self.symbol}, balance={self.total_balance})>"
    
    @property
    def balance_utilization(self) -> float:
        """Calculate balance utilization percentage."""
        if self.total_balance == 0:
            return 0.0
        return float((self.locked_balance / self.total_balance) * 100)
    
    @property
    def has_sufficient_balance(self) -> bool:
        """Check if has sufficient available balance."""
        return self.available_balance > 0
    
    def can_trade_amount(self, amount: Decimal) -> bool:
        """Check if can trade specified amount."""
        return self.available_balance >= amount
    
    def calculate_pnl(self, current_price: Decimal) -> Optional[Decimal]:
        """Calculate unrealized P&L if cost basis is available."""
        if not self.avg_cost_basis or self.total_balance == 0:
            return None
        
        current_value = self.total_balance * current_price
        cost_value = self.total_balance * self.avg_cost_basis
        return current_value - cost_value
    
    def update_balance(self, new_total: Decimal, new_locked: Decimal) -> None:
        """Update balance amounts."""
        self.last_sync_balance = self.total_balance
        self.total_balance = new_total
        self.locked_balance = new_locked
        self.available_balance = new_total - new_locked
        self.last_sync_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
