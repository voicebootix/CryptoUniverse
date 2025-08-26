"""
Database models for CryptoUniverse Enterprise.

This module contains all SQLAlchemy models for the multi-tenant
cryptocurrency trading platform.
"""

from app.core.database import Base

# Import all models to ensure they are registered with SQLAlchemy
from app.models.user import User, UserProfile, UserSession, UserActivity
from app.models.tenant import Tenant, TenantSettings
from app.models.subscription import Subscription, SubscriptionPlan, BillingHistory
from app.models.credit import CreditAccount, CreditTransaction, CreditPack
from app.models.exchange import ExchangeAccount, ExchangeApiKey, ExchangeBalance
from app.models.trading import (
    TradingStrategy,
    Trade,
    Position,
    Order,
    Portfolio,
    PortfolioSnapshot,
)
from app.models.market import MarketData, Symbol, TechnicalIndicator
from app.models.ai import AIModel, AIConsensus, AISignal
from app.models.copy_trading import (
    StrategyPublisher,
    StrategyFollower,
    StrategyPerformance,
    CopyTradeSignal,
)
from app.models.analytics import (
    PerformanceMetric,
    RiskMetric,
    TradingSession,
    UserAnalytics,
)
from app.models.system import (
    SystemHealth,
    AuditLog,
    SystemConfiguration,
    BackgroundTask,
)

__all__ = [
    "Base",
    # User models
    "User",
    "UserProfile",
    "UserSession",
    "UserActivity",
    # Tenant models
    "Tenant",
    "TenantSettings",
    # Subscription models
    "Subscription",
    "SubscriptionPlan",
    "BillingHistory",
    # Credit models
    "CreditAccount",
    "CreditTransaction",
    "CreditPack",
    # Exchange models
    "ExchangeAccount",
    "ExchangeApiKey",
    "ExchangeBalance",
    # Trading models
    "TradingStrategy",
    "Trade",
    "Position",
    "Order",
    "Portfolio",
    "PortfolioSnapshot",
    # Market models
    "MarketData",
    "Symbol",
    "TechnicalIndicator",
    # AI models
    "AIModel",
    "AIConsensus",
    "AISignal",
    # Copy trading models
    "StrategyPublisher",
    "StrategyFollower",
    "StrategyPerformance",
    "CopyTradeSignal",
    # Analytics models
    "PerformanceMetric",
    "RiskMetric",
    "TradingSession",
    "UserAnalytics",
    # System models
    "SystemHealth",
    "AuditLog",
    "SystemConfiguration",
    "BackgroundTask",
]
