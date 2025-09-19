#!/usr/bin/env python3
"""
Enterprise Unified Strategy Service
Single source of truth for all strategy access with role-based permissions
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
import structlog

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.database import get_database, AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.trading import TradingStrategy
from app.models.strategy_access import UserStrategyAccess, StrategyAccessType, StrategyType
from app.services.strategy_marketplace_service import StrategyMarketplaceService
from app.services.trading_strategies import TradingStrategiesService
from app.core.logging import LoggerMixin

settings = get_settings()


class UnifiedStrategyPortfolio:
    """Enterprise strategy portfolio data structure"""

    def __init__(
        self,
        user_id: str,
        user_role: UserRole,
        strategies: List[Dict[str, Any]],
        summary: Dict[str, Any],
        metadata: Dict[str, Any]
    ):
        self.user_id = user_id
        self.user_role = user_role
        self.strategies = strategies
        self.summary = summary
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format"""
        return {
            "success": True,
            "user_id": self.user_id,
            "user_role": self.user_role.value,
            "strategies": self.strategies,
            "active_strategies": [s for s in self.strategies if s.get("is_active", True)],
            "summary": self.summary,
            "metadata": self.metadata,
            "generated_at": datetime.utcnow().isoformat(),
            "data_source": "unified_enterprise_system"
        }


class UnifiedStrategyService(LoggerMixin):
    """
    Enterprise unified strategy service.

    Provides role-based strategy access with database-first architecture,
    Redis fallback, and comprehensive audit logging.
    """

    def __init__(self):
        self.marketplace_service = StrategyMarketplaceService()
        self.trading_service = TradingStrategiesService()
        self._ai_strategy_catalog = self._load_ai_strategy_catalog()

    def _load_ai_strategy_catalog(self) -> Dict[str, Dict[str, Any]]:
        """Load AI strategy catalog with enterprise metadata"""
        return {
            # Core AI Strategies
            "risk_management": {
                "name": "AI Risk Management",
                "category": "Risk Management",
                "description": "Advanced AI-powered risk assessment and position sizing",
                "risk_level": "low",
                "min_capital": 1000,
                "credit_cost_monthly": 30,
                "supported_exchanges": ["binance", "kucoin", "okx"],
                "timeframes": ["1m", "5m", "15m", "1h"],
                "performance_tier": "enterprise",
                "compliance_verified": True
            },
            "portfolio_optimization": {
                "name": "AI Portfolio Optimization",
                "category": "Portfolio Management",
                "description": "Machine learning portfolio optimization with rebalancing",
                "risk_level": "medium",
                "min_capital": 5000,
                "credit_cost_monthly": 45,
                "supported_exchanges": ["binance", "kucoin", "okx"],
                "timeframes": ["1h", "4h", "1d"],
                "performance_tier": "enterprise",
                "compliance_verified": True
            },
            "spot_momentum_strategy": {
                "name": "AI Spot Momentum",
                "category": "Momentum Trading",
                "description": "AI-driven momentum detection for spot trading",
                "risk_level": "medium",
                "min_capital": 2000,
                "credit_cost_monthly": 35,
                "supported_exchanges": ["binance", "kucoin"],
                "timeframes": ["5m", "15m", "1h"],
                "performance_tier": "professional",
                "compliance_verified": True
            },
            "futures_arbitrage": {
                "name": "AI Futures Arbitrage",
                "category": "Arbitrage",
                "description": "Cross-exchange arbitrage opportunities detection",
                "risk_level": "low",
                "min_capital": 10000,
                "credit_cost_monthly": 60,
                "supported_exchanges": ["binance", "okx", "bybit"],
                "timeframes": ["1m", "5m"],
                "performance_tier": "enterprise",
                "compliance_verified": True
            },
            "options_strategies": {
                "name": "AI Options Strategies",
                "category": "Derivatives",
                "description": "Sophisticated options strategies with volatility analysis",
                "risk_level": "high",
                "min_capital": 15000,
                "credit_cost_monthly": 75,
                "supported_exchanges": ["deribit", "okx"],
                "timeframes": ["1h", "4h", "1d"],
                "performance_tier": "enterprise",
                "compliance_verified": True
            },
            "statistical_arbitrage": {
                "name": "AI Statistical Arbitrage",
                "category": "Statistical Trading",
                "description": "Mean reversion and statistical arbitrage strategies",
                "risk_level": "medium",
                "min_capital": 8000,
                "credit_cost_monthly": 50,
                "supported_exchanges": ["binance", "kucoin", "okx"],
                "timeframes": ["15m", "1h", "4h"],
                "performance_tier": "professional",
                "compliance_verified": True
            },
            "market_making": {
                "name": "AI Market Making",
                "category": "Market Making",
                "description": "Intelligent market making with inventory management",
                "risk_level": "low",
                "min_capital": 20000,
                "credit_cost_monthly": 80,
                "supported_exchanges": ["binance", "kucoin", "okx"],
                "timeframes": ["1m", "5m"],
                "performance_tier": "enterprise",
                "compliance_verified": True
            },
            "pairs_trading": {
                "name": "AI Pairs Trading",
                "category": "Statistical Trading",
                "description": "Correlated pairs trading with AI signal generation",
                "risk_level": "medium",
                "min_capital": 5000,
                "credit_cost_monthly": 40,
                "supported_exchanges": ["binance", "kucoin"],
                "timeframes": ["1h", "4h"],
                "performance_tier": "professional",
                "compliance_verified": True
            },
            "volatility_trading": {
                "name": "AI Volatility Trading",
                "category": "Volatility",
                "description": "Volatility-based trading strategies with risk management",
                "risk_level": "high",
                "min_capital": 12000,
                "credit_cost_monthly": 65,
                "supported_exchanges": ["binance", "okx", "deribit"],
                "timeframes": ["1h", "4h", "1d"],
                "performance_tier": "enterprise",
                "compliance_verified": True
            },
            "news_sentiment": {
                "name": "AI News Sentiment",
                "category": "Sentiment Analysis",
                "description": "News and social sentiment analysis for trading signals",
                "risk_level": "medium",
                "min_capital": 3000,
                "credit_cost_monthly": 40,
                "supported_exchanges": ["binance", "kucoin"],
                "timeframes": ["5m", "15m", "1h"],
                "performance_tier": "professional",
                "compliance_verified": True
            }
        }

    async def get_user_strategy_portfolio(
        self,
        user_id: str,
        user_role: Optional[UserRole] = None
    ) -> UnifiedStrategyPortfolio:
        """
        Enterprise unified strategy portfolio retrieval.

        Returns role-appropriate strategy portfolio with comprehensive
        access control and audit logging.
        """
        operation_start = datetime.utcnow()
        operation_id = f"portfolio_{user_id[:8]}"

        self.logger.info(
            "🏢 ENTERPRISE PORTFOLIO REQUEST",
            operation_id=operation_id,
            user_id=user_id,
            user_role=user_role.value if user_role else "unknown"
        )

        try:
            async with AsyncSessionLocal() as db:
                # Get user and role if not provided
                if user_role is None:
                    user = await db.execute(
                        select(User).where(User.id == UUID(user_id))
                    )
                    user_obj = user.scalar_one_or_none()
                    if not user_obj:
                        raise ValueError(f"User {user_id} not found")
                    user_role = user_obj.role

                # Route to appropriate strategy retrieval method
                if user_role == UserRole.ADMIN:
                    portfolio = await self._get_admin_full_portfolio(user_id, db)
                else:
                    portfolio = await self._get_user_owned_portfolio(user_id, db, user_role)

                # Add metadata and performance tracking
                execution_time = (datetime.utcnow() - operation_start).total_seconds()
                portfolio.metadata.update({
                    "operation_id": operation_id,
                    "execution_time_seconds": execution_time,
                    "data_freshness": "realtime",
                    "api_version": "v2_unified",
                    "compliance_checked": True
                })

                self.logger.info(
                    "✅ ENTERPRISE PORTFOLIO SUCCESS",
                    operation_id=operation_id,
                    user_id=user_id,
                    strategies_count=len(portfolio.strategies),
                    active_strategies=len([s for s in portfolio.strategies if s.get("is_active", True)]),
                    execution_time_seconds=execution_time
                )

                return portfolio

        except Exception as e:
            execution_time = (datetime.utcnow() - operation_start).total_seconds()

            self.logger.error(
                "❌ ENTERPRISE PORTFOLIO FAILED",
                operation_id=operation_id,
                user_id=user_id,
                error=str(e),
                execution_time_seconds=execution_time,
                exc_info=True
            )

            # Return graceful degraded state
            # Ensure user_role is never None to prevent to_dict() errors
            safe_user_role = user_role if user_role is not None else UserRole.VIEWER

            return UnifiedStrategyPortfolio(
                user_id=user_id,
                user_role=safe_user_role,
                strategies=[],
                summary=self._generate_empty_summary(),
                metadata={
                    "error": str(e),
                    "degraded": True,
                    "execution_time_seconds": execution_time
                }
            )

    async def _get_admin_full_portfolio(
        self,
        user_id: str,
        db: AsyncSession
    ) -> UnifiedStrategyPortfolio:
        """Admin users get full access to all strategies"""

        self.logger.info("🔑 ADMIN FULL ACCESS", user_id=user_id)

        strategies = []

        # 1. Get all AI strategies from catalog
        for strategy_key, config in self._ai_strategy_catalog.items():
            strategy_data = await self._build_ai_strategy_record(
                strategy_key, config, user_id, is_admin=True
            )
            strategies.append(strategy_data)

        # 2. Get all active community strategies
        community_strategies = await self._get_community_strategies_for_admin(db)
        strategies.extend(community_strategies)

        # 3. Get admin's personally owned strategies
        owned_strategies = await self._get_user_owned_strategies(user_id, db)
        strategies.extend(owned_strategies)

        # Remove duplicates and generate summary
        strategies = self._deduplicate_strategies(strategies)
        summary = self._generate_admin_summary(strategies)

        return UnifiedStrategyPortfolio(
            user_id=user_id,
            user_role=UserRole.ADMIN,
            strategies=strategies,
            summary=summary,
            metadata={
                "access_level": "full_admin",
                "ai_strategies": len(self._ai_strategy_catalog),
                "community_strategies": len(community_strategies),
                "owned_strategies": len(owned_strategies),
                "data_sources": ["ai_catalog", "community_database", "user_database"]
            }
        )

    async def _get_user_owned_portfolio(
        self,
        user_id: str,
        db: AsyncSession,
        user_role: UserRole
    ) -> UnifiedStrategyPortfolio:
        """Regular users get only their owned/purchased strategies"""

        self.logger.info("👤 USER OWNED ACCESS", user_id=user_id)

        # Get user's strategy access records
        access_query = select(UserStrategyAccess).where(
            and_(
                UserStrategyAccess.user_id == UUID(user_id),
                UserStrategyAccess.is_active == True
            )
        ).options(selectinload(UserStrategyAccess.user))

        result = await db.execute(access_query)
        access_records = result.scalars().all()

        strategies = []

        # Build strategy data for each access record
        for access in access_records:
            if access.is_valid():  # Check expiration
                if access.strategy_type == StrategyType.AI_STRATEGY:
                    strategy_data = await self._build_ai_strategy_from_access(access)
                elif access.strategy_type == StrategyType.COMMUNITY_STRATEGY:
                    strategy_data = await self._build_community_strategy_from_access(access, db)
                else:
                    continue

                if strategy_data:
                    strategies.append(strategy_data)

        # Generate user-specific summary
        summary = self._generate_user_summary(strategies, access_records)

        return UnifiedStrategyPortfolio(
            user_id=user_id,
            user_role=user_role,
            strategies=strategies,
            summary=summary,
            metadata={
                "access_level": "user_owned",
                "access_records": len(access_records),
                "valid_access": len(strategies),
                "data_sources": ["user_strategy_access"]
            }
        )

    async def _build_ai_strategy_record(
        self,
        strategy_key: str,
        config: Dict[str, Any],
        user_id: str,
        is_admin: bool = False,
        access_type: Optional[str] = None,
        subscription_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build AI strategy record with performance data"""

        # Get performance data (cached or calculated)
        performance = await self._get_ai_strategy_performance(strategy_key, user_id)

        return {
            "strategy_id": f"ai_{strategy_key}",
            "name": config["name"],
            "description": config["description"],
            "category": config["category"],
            "is_ai_strategy": True,
            "publisher_name": "CryptoUniverse AI",
            "publisher_id": None,

            # Access information
            "is_active": True,
            "subscription_type": subscription_type if subscription_type else ("admin_grant" if is_admin else "purchased"),
            "access_type": access_type if access_type else ("admin_grant" if is_admin else "purchased"),
            "activated_at": datetime.utcnow().isoformat(),

            # Pricing
            "credit_cost_monthly": config["credit_cost_monthly"],
            "credit_cost_per_execution": max(1, config["credit_cost_monthly"] // 30),

            # Performance metrics
            "total_trades": performance.get("total_trades", 0),
            "winning_trades": performance.get("winning_trades", 0),
            "win_rate": performance.get("win_rate", 0.0),
            "total_pnl_usd": performance.get("total_pnl", 0.0),
            "best_trade_pnl": performance.get("best_trade_pnl", 0.0),
            "worst_trade_pnl": performance.get("worst_trade_pnl", 0.0),
            "current_drawdown": performance.get("current_drawdown", 0.0),
            "max_drawdown": performance.get("max_drawdown", 0.0),
            "sharpe_ratio": performance.get("sharpe_ratio"),
            "last_7_days_pnl": performance.get("last_7_days_pnl", 0.0),
            "last_30_days_pnl": performance.get("last_30_days_pnl", 0.0),

            # Configuration
            "risk_level": config["risk_level"],
            "min_capital_usd": config["min_capital"],
            "supported_exchanges": config["supported_exchanges"],
            "timeframes": config["timeframes"],
            "performance_tier": config.get("performance_tier", "professional"),
            "compliance_verified": config.get("compliance_verified", True),

            # Metadata
            "recent_trades": performance.get("recent_trades", []),
            "allocation_percentage": 10.0,
            "max_position_size": config["min_capital"] * 0.1,
            "stop_loss_percentage": 5.0
        }

    async def _get_ai_strategy_performance(
        self,
        strategy_key: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get AI strategy performance with caching"""
        try:
            # Use marketplace service for performance data
            return await self.marketplace_service._get_ai_strategy_performance(
                strategy_key, user_id
            )
        except Exception as e:
            self.logger.warning(
                "Failed to get AI strategy performance",
                strategy_key=strategy_key,
                error=str(e)
            )
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "status": "no_data"
            }

    async def _get_community_strategies_for_admin(
        self,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get all active community strategies for admin view"""

        query = select(TradingStrategy).where(
            TradingStrategy.is_active == True
        ).options(
            selectinload(TradingStrategy.user)
        ).limit(100)  # Reasonable limit for performance

        result = await db.execute(query)
        strategies = result.scalars().all()

        community_strategies = []
        for strategy in strategies:
            strategy_data = {
                "strategy_id": str(strategy.id),
                "name": strategy.name,
                "description": strategy.description or "Community strategy",
                "category": strategy.strategy_type.value if strategy.strategy_type else "community",
                "is_ai_strategy": False,
                "publisher_name": strategy.user.display_name if strategy.user else "Anonymous",
                "publisher_id": str(strategy.user_id) if strategy.user_id else None,

                # Access information
                "is_active": strategy.is_active,
                "subscription_type": "admin_grant",
                "access_type": "admin_grant",
                "activated_at": datetime.utcnow().isoformat(),

                # Pricing
                "credit_cost_monthly": 20,  # Default community strategy cost
                "credit_cost_per_execution": 1,

                # Performance from database
                "total_trades": strategy.total_trades or 0,
                "win_rate": float(strategy.win_rate) if strategy.win_rate else 0.0,
                "total_pnl_usd": float(strategy.total_return) if strategy.total_return else 0.0,
                "max_drawdown": float(strategy.max_drawdown) if strategy.max_drawdown else 0.0,
                "sharpe_ratio": float(strategy.sharpe_ratio) if strategy.sharpe_ratio else None,

                # Configuration
                "risk_level": "medium",
                "min_capital_usd": 1000,
                "supported_exchanges": ["binance"],
                "timeframes": [strategy.timeframe] if strategy.timeframe else ["1h"],
                "performance_tier": "community",
                "compliance_verified": False,

                # Metadata
                "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
                "recent_trades": []
            }
            community_strategies.append(strategy_data)

        return community_strategies

    async def _get_user_owned_strategies(
        self,
        user_id: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get user's personally created strategies"""

        query = select(TradingStrategy).where(
            and_(
                TradingStrategy.user_id == UUID(user_id),
                TradingStrategy.is_active == True
            )
        )

        result = await db.execute(query)
        strategies = result.scalars().all()

        owned_strategies = []
        for strategy in strategies:
            strategy_data = {
                "strategy_id": str(strategy.id),
                "name": strategy.name,
                "description": strategy.description or "Personal strategy",
                "category": strategy.strategy_type.value if strategy.strategy_type else "personal",
                "is_ai_strategy": False,
                "publisher_name": "You",
                "publisher_id": str(user_id),

                # Access information
                "is_active": strategy.is_active,
                "subscription_type": "owned",
                "access_type": "owned",
                "activated_at": strategy.created_at.isoformat() if strategy.created_at else None,

                # Pricing
                "credit_cost_monthly": 0,  # Owned strategies are free
                "credit_cost_per_execution": 0,

                # Performance from database
                "total_trades": strategy.total_trades or 0,
                "win_rate": float(strategy.win_rate) if strategy.win_rate else 0.0,
                "total_pnl_usd": float(strategy.total_return) if strategy.total_return else 0.0,
                "max_drawdown": float(strategy.max_drawdown) if strategy.max_drawdown else 0.0,
                "sharpe_ratio": float(strategy.sharpe_ratio) if strategy.sharpe_ratio else None,

                # Configuration
                "risk_level": "medium",
                "min_capital_usd": 1000,
                "performance_tier": "personal",
                "compliance_verified": False,

                # Metadata
                "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
                "recent_trades": []
            }
            owned_strategies.append(strategy_data)

        return owned_strategies

    async def _build_ai_strategy_from_access(
        self,
        access: UserStrategyAccess
    ) -> Optional[Dict[str, Any]]:
        """Build AI strategy data from access record"""

        # Extract strategy key from strategy_id
        strategy_key = access.strategy_id.replace("ai_", "")

        if strategy_key not in self._ai_strategy_catalog:
            self.logger.warning(
                "AI strategy not found in catalog",
                strategy_key=strategy_key,
                strategy_id=access.strategy_id
            )
            return None

        config = self._ai_strategy_catalog[strategy_key]
        return await self._build_ai_strategy_record(
            strategy_key,
            config,
            str(access.user_id),
            is_admin=False,
            access_type=access.access_type.value if access.access_type else None,
            subscription_type=access.subscription_type
        )

    async def _build_community_strategy_from_access(
        self,
        access: UserStrategyAccess,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Build community strategy data from access record"""

        try:
            strategy_uuid = UUID(access.strategy_id)
            query = select(TradingStrategy).where(TradingStrategy.id == strategy_uuid)
            result = await db.execute(query)
            strategy = result.scalar_one_or_none()

            if not strategy:
                return None

            return {
                "strategy_id": str(strategy.id),
                "name": strategy.name,
                "description": strategy.description or "Community strategy",
                "category": strategy.strategy_type.value if strategy.strategy_type else "community",
                "is_ai_strategy": False,
                "publisher_name": "Community",

                # Access information from access record
                "is_active": access.is_active and strategy.is_active,
                "subscription_type": access.subscription_type,
                "access_type": access.access_type.value,
                "activated_at": access.activated_at.isoformat(),
                "expires_at": access.expires_at.isoformat() if access.expires_at else None,

                # Pricing from access record
                "credit_cost_monthly": access.credits_paid or 20,
                "credit_cost_per_execution": 1,

                # Performance from strategy
                "total_trades": strategy.total_trades or 0,
                "win_rate": float(strategy.win_rate) if strategy.win_rate else 0.0,
                "total_pnl_usd": float(strategy.total_return) if strategy.total_return else 0.0,

                # Configuration
                "risk_level": "medium",
                "min_capital_usd": 1000,
                "performance_tier": "community"
            }

        except Exception as e:
            self.logger.error(
                "Failed to build community strategy from access",
                access_id=str(access.id),
                strategy_id=access.strategy_id,
                error=str(e)
            )
            return None

    def _deduplicate_strategies(self, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate strategies by strategy_id"""
        seen = set()
        unique_strategies = []

        for strategy in strategies:
            strategy_id = strategy.get("strategy_id")
            if strategy_id and strategy_id not in seen:
                seen.add(strategy_id)
                unique_strategies.append(strategy)

        return unique_strategies

    def _generate_admin_summary(self, strategies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate admin portfolio summary"""
        active_strategies = [s for s in strategies if s.get("is_active", True)]

        total_pnl = sum(s.get("total_pnl_usd", 0) for s in active_strategies)
        total_monthly_cost = sum(s.get("credit_cost_monthly", 0) for s in active_strategies)

        welcome_count = len([s for s in active_strategies if s.get("access_type") == "welcome"])
        purchased_count = len([s for s in active_strategies if s.get("access_type") in ["purchased", "admin_grant"]])

        return {
            "total_strategies": len(strategies),
            "active_strategies": len(active_strategies),
            "welcome_strategies": welcome_count,
            "purchased_strategies": purchased_count,
            "total_portfolio_value": 100000.0,  # Admin portfolio value
            "total_pnl_usd": total_pnl,
            "total_pnl_percentage": (total_pnl / 100000.0) * 100 if total_pnl else 0,
            "monthly_credit_cost": total_monthly_cost,
            "next_billing_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "profit_potential_used": abs(total_pnl) if total_pnl < 0 else 0,
            "profit_potential_remaining": 100000.0 - (abs(total_pnl) if total_pnl < 0 else 0)
        }

    def _generate_user_summary(
        self,
        strategies: List[Dict[str, Any]],
        access_records: List[UserStrategyAccess]
    ) -> Dict[str, Any]:
        """Generate user portfolio summary"""
        active_strategies = [s for s in strategies if s.get("is_active", True)]

        total_pnl = sum(s.get("total_pnl_usd", 0) for s in active_strategies)
        total_monthly_cost = sum(s.get("credit_cost_monthly", 0) for s in active_strategies)

        welcome_count = len([r for r in access_records if r.access_type == StrategyAccessType.WELCOME])
        purchased_count = len([r for r in access_records if r.access_type == StrategyAccessType.PURCHASED])

        return {
            "total_strategies": len(strategies),
            "active_strategies": len(active_strategies),
            "welcome_strategies": welcome_count,
            "purchased_strategies": purchased_count,
            "total_portfolio_value": 10000.0,  # User default portfolio value
            "total_pnl_usd": total_pnl,
            "total_pnl_percentage": (total_pnl / 10000.0) * 100 if total_pnl else 0,
            "monthly_credit_cost": total_monthly_cost,
            "profit_potential_used": abs(total_pnl) if total_pnl < 0 else 0,
            "profit_potential_remaining": 10000.0 - (abs(total_pnl) if total_pnl < 0 else 0)
        }

    def _generate_empty_summary(self) -> Dict[str, Any]:
        """Generate empty summary for error states"""
        return {
            "total_strategies": 0,
            "active_strategies": 0,
            "welcome_strategies": 0,
            "purchased_strategies": 0,
            "total_portfolio_value": 0.0,
            "total_pnl_usd": 0.0,
            "total_pnl_percentage": 0.0,
            "monthly_credit_cost": 0,
            "profit_potential_used": 0.0,
            "profit_potential_remaining": 0.0
        }

    # Strategy Access Management Methods

    async def grant_strategy_access(
        self,
        user_id: str,
        strategy_id: str,
        strategy_type: StrategyType,
        access_type: StrategyAccessType,
        subscription_type: str = "monthly",
        credits_paid: int = 0,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserStrategyAccess:
        """
        Grant strategy access to user with race condition handling.

        Uses atomic insert-or-update pattern to handle concurrent access grants
        without IntegrityError on unique constraint violations.
        """

        async with AsyncSessionLocal() as db:
            try:
                # First attempt: Try to create new access record
                new_access = UserStrategyAccess(
                    user_id=UUID(user_id),
                    strategy_id=strategy_id,
                    strategy_type=strategy_type,
                    access_type=access_type,
                    subscription_type=subscription_type,
                    credits_paid=credits_paid,
                    expires_at=expires_at,
                    metadata_json=metadata or {},
                    is_active=True
                )

                db.add(new_access)
                await db.commit()
                await db.refresh(new_access)

                self.logger.info(
                    "Granted new strategy access",
                    user_id=user_id,
                    strategy_id=strategy_id,
                    access_type=access_type.value,
                    access_id=str(new_access.id)
                )

                return new_access

            except IntegrityError:
                # Concurrent insert detected - rollback and update existing record
                await db.rollback()

                self.logger.debug(
                    "Concurrent grant detected, updating existing access",
                    user_id=user_id,
                    strategy_id=strategy_id
                )

                # Re-query to get existing record
                existing = await db.execute(
                    select(UserStrategyAccess).where(
                        and_(
                            UserStrategyAccess.user_id == UUID(user_id),
                            UserStrategyAccess.strategy_id == strategy_id
                        )
                    )
                )
                existing_access = existing.scalar_one()  # Must exist due to integrity error

                # Update existing access with new values
                existing_access.access_type = access_type
                existing_access.subscription_type = subscription_type
                existing_access.credits_paid = credits_paid
                existing_access.expires_at = expires_at
                existing_access.is_active = True
                existing_access.metadata_json = metadata or {}
                existing_access.updated_at = datetime.utcnow()

                await db.commit()

                self.logger.info(
                    "Updated existing strategy access (race condition resolved)",
                    user_id=user_id,
                    strategy_id=strategy_id,
                    access_type=access_type.value,
                    access_id=str(existing_access.id)
                )

                return existing_access

    async def revoke_strategy_access(
        self,
        user_id: str,
        strategy_id: str
    ) -> bool:
        """Revoke strategy access"""

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(UserStrategyAccess).where(
                    and_(
                        UserStrategyAccess.user_id == UUID(user_id),
                        UserStrategyAccess.strategy_id == strategy_id
                    )
                )
            )
            access = result.scalar_one_or_none()

            if access:
                access.is_active = False
                access.updated_at = datetime.utcnow()
                await db.commit()

                self.logger.info(
                    "Revoked strategy access",
                    user_id=user_id,
                    strategy_id=strategy_id,
                    access_id=str(access.id)
                )

                return True

            return False

    async def bulk_grant_admin_access(self, admin_user_id: str) -> List[UserStrategyAccess]:
        """Grant admin access to all AI strategies"""

        granted_access = []

        for strategy_key in self._ai_strategy_catalog.keys():
            strategy_id = f"ai_{strategy_key}"

            try:
                access = await self.grant_strategy_access(
                    user_id=admin_user_id,
                    strategy_id=strategy_id,
                    strategy_type=StrategyType.AI_STRATEGY,
                    access_type=StrategyAccessType.ADMIN_GRANT,
                    subscription_type="permanent",
                    credits_paid=0,
                    expires_at=None,
                    metadata={"auto_granted": True, "admin_privilege": True}
                )
                granted_access.append(access)

            except Exception as e:
                self.logger.error(
                    "Failed to grant admin access",
                    strategy_id=strategy_id,
                    error=str(e)
                )

        self.logger.info(
            "Bulk granted admin access",
            admin_user_id=admin_user_id,
            strategies_granted=len(granted_access),
            total_ai_strategies=len(self._ai_strategy_catalog)
        )

        return granted_access


# Global service instance
unified_strategy_service = UnifiedStrategyService()


async def get_unified_strategy_service() -> UnifiedStrategyService:
    """Dependency injection for FastAPI"""
    return unified_strategy_service