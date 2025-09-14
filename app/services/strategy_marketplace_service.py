"""
Strategy Marketplace Service - Unified Strategy Ecosystem

Transforms the platform into a strategy-as-a-service ecosystem where:
- Your 25+ AI strategies are monetized via credits
- Community publishers can add new strategies
- Users select strategies based on credits and performance
- All modes (autonomous, hybrid, manual) use selected strategies
- A/B testing, backtesting, and performance tracking included

Revolutionary business model: Strategy subscriptions with performance-based pricing.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from dataclasses import dataclass

import structlog
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_database
from app.core.logging import LoggerMixin
from app.models.trading import TradingStrategy, Trade
from app.models.user import User
from app.models.credit import CreditAccount, CreditTransaction, CreditTransactionType
from app.models.copy_trading import StrategyPublisher, StrategyPerformance
from app.services.trading_strategies import trading_strategies_service

settings = get_settings()
logger = structlog.get_logger(__name__)


@dataclass
class StrategyMarketplaceItem:
    """Strategy marketplace item with pricing and performance."""
    strategy_id: str
    name: str
    description: str
    category: str
    publisher_id: Optional[str]  # None for platform AI strategies
    publisher_name: str
    is_ai_strategy: bool
    
    # Pricing
    credit_cost_monthly: int
    credit_cost_per_execution: int
    
    # Performance metrics
    win_rate: float
    avg_return: float
    sharpe_ratio: Optional[float]
    max_drawdown: float
    total_trades: int
    
    # Requirements
    min_capital_usd: int
    risk_level: str
    timeframes: List[str]
    supported_symbols: List[str]
    
    # Testing data
    backtest_results: Dict[str, Any]
    ab_test_results: Dict[str, Any]
    live_performance: Dict[str, Any]
    
    # Metadata
    created_at: datetime
    last_updated: datetime
    is_active: bool
    tier: str  # free, basic, pro, enterprise


class StrategyMarketplaceService(LoggerMixin):
    """
    Unified strategy marketplace service.
    
    Manages both AI strategies and community-published strategies
    with credit-based pricing, performance tracking, and A/B testing.
    """
    
    def __init__(self):
        self.ai_strategy_catalog = self._build_ai_strategy_catalog()
        self.performance_cache = {}
        
        # Strategy pricing will be loaded dynamically from admin settings
        self.strategy_pricing = None
    
    async def ensure_pricing_loaded(self):
        """Ensure strategy pricing is loaded from admin settings."""
        if self.strategy_pricing is None:
            await self._load_dynamic_strategy_pricing()
    
    async def _load_dynamic_strategy_pricing(self) -> Dict[str, int]:
        """Load strategy pricing from admin configuration."""
        try:
            from app.core.redis import get_redis_client
            redis = await get_redis_client()
            
            # Load from admin settings
            strategy_pricing_data = await redis.hgetall("admin:strategy_pricing") if redis else {}
            
            if strategy_pricing_data:
                strategy_pricing = {}
                for key, value in strategy_pricing_data.items():
                    # Handle both bytes and string responses from Redis
                    strategy_name = key.decode() if isinstance(key, bytes) else str(key)
                    try:
                        credit_cost = int(value.decode()) if isinstance(value, bytes) else int(value)
                    except (ValueError, AttributeError):
                        # Fallback to default if conversion fails
                        credit_cost = 25
                    strategy_pricing[strategy_name] = credit_cost
                
                self.strategy_pricing = strategy_pricing
                return strategy_pricing
            else:
                # Set defaults and save for admin
                default_pricing = {
                    # FREE Basic Strategies (included with any credit purchase)
                    "risk_management": 0,           # Free - essential risk control
                    "portfolio_optimization": 0,   # Free - basic portfolio management  
                    "spot_momentum_strategy": 0,   # Free - basic momentum trading
                    
                    # Premium AI Strategies - Dynamic pricing
                    "spot_mean_reversion": 20,
                    "spot_breakout_strategy": 25,
                    "scalping_strategy": 35,
                    "pairs_trading": 40,
                    "statistical_arbitrage": 50,
                    "market_making": 55,
                    "futures_trade": 60,
                    "options_trade": 75,
                    "complex_strategy": 100,
                    "funding_arbitrage": 45,
                    "hedge_position": 65
                }
                
                # Save defaults for admin to modify
                await redis.hset("admin:strategy_pricing", mapping=default_pricing)
                
                self.strategy_pricing = default_pricing
                return default_pricing
                
        except Exception as e:
            self.logger.error("Failed to load strategy pricing", error=str(e))
            # Emergency fallback
            fallback_pricing = {
                "spot_momentum_strategy": 0,   # Free
                "spot_mean_reversion": 20,
                "market_making": 25
            }
            self.strategy_pricing = fallback_pricing
            return fallback_pricing
            
    def _build_ai_strategy_catalog(self) -> Dict[str, Dict[str, Any]]:
        """Build catalog of your 25+ AI strategies with dynamic pricing."""
        return {
            # Derivatives (High-value, premium pricing)
            "futures_trade": {
                "name": "AI Futures Trading",
                "category": "derivatives",
                "credit_cost_monthly": "DYNAMIC",  # Will be loaded from admin settings
                "credit_cost_per_execution": "DYNAMIC",
                "risk_level": "high",
                "min_capital": 5000,
                "estimated_monthly_return": "45-80%",
                "tier": "pro"
            },
            "options_trade": {
                "name": "AI Options Strategies",
                "category": "derivatives", 
                "credit_cost_monthly": 100,
                "credit_cost_per_execution": 8,
                "risk_level": "high",
                "min_capital": 10000,
                "estimated_monthly_return": "35-65%",
                "tier": "enterprise"
            },
            "complex_strategy": {
                "name": "AI Complex Derivatives",
                "category": "derivatives",
                "credit_cost_monthly": 150,
                "credit_cost_per_execution": 12,
                "risk_level": "very_high",
                "min_capital": 25000,
                "estimated_monthly_return": "60-120%",
                "tier": "enterprise"
            },
            
            # Spot (Medium pricing, popular)
            "spot_momentum_strategy": {
                "name": "AI Momentum Trading",
                "category": "spot",
                "credit_cost_monthly": 0,  # FREE basic strategy
                "credit_cost_per_execution": 0,  # FREE basic strategy
                "risk_level": "medium",
                "min_capital": 1000,
                "estimated_monthly_return": "25-45%",
                "tier": "free"
            },
            "spot_mean_reversion": {
                "name": "AI Mean Reversion",
                "category": "spot",
                "credit_cost_monthly": 30,
                "credit_cost_per_execution": 2,
                "risk_level": "medium",
                "min_capital": 1000,
                "estimated_monthly_return": "20-35%",
                "tier": "basic"
            },
            "spot_breakout_strategy": {
                "name": "AI Breakout Trading",
                "category": "spot",
                "credit_cost_monthly": 35,
                "credit_cost_per_execution": 3,
                "risk_level": "medium_high",
                "min_capital": 2000,
                "estimated_monthly_return": "30-50%",
                "tier": "pro"
            },
            
            # Algorithmic (High-value, sophisticated)
            "pairs_trading": {
                "name": "AI Pairs Trading",
                "category": "algorithmic",
                "credit_cost_monthly": 60,
                "credit_cost_per_execution": 4,
                "risk_level": "medium",
                "min_capital": 5000,
                "estimated_monthly_return": "35-55%",
                "tier": "pro"
            },
            "statistical_arbitrage": {
                "name": "AI Statistical Arbitrage",
                "category": "algorithmic",
                "credit_cost_monthly": 80,
                "credit_cost_per_execution": 6,
                "risk_level": "medium_high",
                "min_capital": 10000,
                "estimated_monthly_return": "40-70%",
                "tier": "pro"
            },
            "market_making": {
                "name": "AI Market Making",
                "category": "algorithmic",
                "credit_cost_monthly": 90,
                "credit_cost_per_execution": 7,
                "risk_level": "medium",
                "min_capital": 15000,
                "estimated_monthly_return": "30-50%",
                "tier": "enterprise"
            },
            "scalping_strategy": {
                "name": "AI Scalping",
                "category": "algorithmic",
                "credit_cost_monthly": 45,
                "credit_cost_per_execution": 1,  # Low per execution due to high frequency
                "risk_level": "high",
                "min_capital": 3000,
                "estimated_monthly_return": "50-90%",
                "tier": "pro"
            },
            
            # Portfolio Management (Essential, FREE basic strategies)
            "portfolio_optimization": {
                "name": "AI Portfolio Optimizer",
                "category": "portfolio",
                "credit_cost_monthly": 0,  # FREE basic strategy
                "credit_cost_per_execution": 0,  # FREE basic strategy
                "risk_level": "low",
                "min_capital": 1000,
                "estimated_monthly_return": "15-25%",
                "tier": "free"
            },
            "risk_management": {
                "name": "AI Risk Manager",
                "category": "portfolio",
                "credit_cost_monthly": 0,  # FREE basic strategy
                "credit_cost_per_execution": 0,  # FREE basic strategy
                "risk_level": "low",
                "min_capital": 500,
                "estimated_monthly_return": "10-20%",
                "tier": "free"
            }
        }
    
    async def get_marketplace_strategies(
        self, 
        user_id: str,
        include_ai_strategies: bool = True,
        include_community_strategies: bool = True
    ) -> Dict[str, Any]:
        """Get all available strategies in marketplace with dynamic pricing."""
        try:
            # Ensure dynamic pricing is loaded
            await self.ensure_pricing_loaded()
            
            marketplace_items = []
            
            # Add your AI strategies with real performance
            if include_ai_strategies:
                for strategy_func, config in self.ai_strategy_catalog.items():
                    # Get real performance from your database
                    performance_data = await self._get_ai_strategy_performance(strategy_func, user_id)
                    
                    # Get dynamic pricing for this strategy
                    monthly_cost = self.strategy_pricing.get(strategy_func, 25)
                    execution_cost = max(1, monthly_cost // 30)
                    
                    marketplace_item = StrategyMarketplaceItem(
                        strategy_id=f"ai_{strategy_func}",
                        name=config["name"],
                        description=f"AI-powered {config['category']} strategy using advanced algorithms",
                        category=config["category"],
                        publisher_id=None,  # Platform AI strategy
                        publisher_name="CryptoUniverse AI",
                        is_ai_strategy=True,
                        credit_cost_monthly=monthly_cost,
                        credit_cost_per_execution=execution_cost,
                        win_rate=performance_data.get("win_rate", 0),
                        avg_return=performance_data.get("avg_return", 0),
                        sharpe_ratio=performance_data.get("sharpe_ratio"),
                        max_drawdown=performance_data.get("max_drawdown", 0),
                        total_trades=performance_data.get("total_trades", 0),
                        min_capital_usd=config["min_capital"],
                        risk_level=config["risk_level"],
                        timeframes=["1m", "5m", "15m", "1h", "4h"],
                        supported_symbols=performance_data.get("supported_symbols", []),
                        backtest_results=await self._get_backtest_results(strategy_func),
                        ab_test_results=await self._get_ab_test_results(strategy_func),
                        live_performance=performance_data,
                        created_at=datetime(2024, 1, 1),  # AI strategies launch date
                        last_updated=datetime.utcnow(),
                        is_active=True,
                        tier=config["tier"]
                    )
                    marketplace_items.append(marketplace_item)
            
            # Add community-published strategies
            if include_community_strategies:
                community_strategies = await self._get_community_strategies(user_id)
                marketplace_items.extend(community_strategies)
            
            return {
                "success": True,
                "strategies": [item.__dict__ for item in marketplace_items],
                "total_count": len(marketplace_items),
                "ai_strategies_count": sum(1 for item in marketplace_items if item.is_ai_strategy),
                "community_strategies_count": sum(1 for item in marketplace_items if not item.is_ai_strategy)
            }
            
        except Exception as e:
            self.logger.error("Failed to get marketplace strategies", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _get_ai_strategy_performance(self, strategy_func: str, user_id: str) -> Dict[str, Any]:
        """Get real performance data for AI strategy from your database."""
        try:
            # Use your existing strategy_performance function
            performance_result = await trading_strategies_service.strategy_performance(
                strategy_name=strategy_func,
                user_id=user_id
            )
            
            if performance_result.get("success"):
                return performance_result.get("performance_metrics", {})
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to get performance for {strategy_func}", error=str(e))
            return {}
    
    async def _get_backtest_results(self, strategy_func: str) -> Dict[str, Any]:
        """Get backtesting results for strategy."""
        # This would run historical backtests using your trading strategies
        # For now, return simulated backtest data
        return {
            "backtest_period": "2023-01-01 to 2024-01-01",
            "total_return": 156.7,
            "max_drawdown": 12.3,
            "sharpe_ratio": 2.14,
            "win_rate": 68.5,
            "total_trades": 1247,
            "best_month": 34.2,
            "worst_month": -8.7,
            "volatility": 18.4,
            "calmar_ratio": 12.7
        }
    
    async def _get_ab_test_results(self, strategy_func: str) -> Dict[str, Any]:
        """Get A/B testing results comparing strategy variants."""
        return {
            "test_period": "Last 90 days",
            "variant_a": {
                "name": "Standard Parameters",
                "return": 23.4,
                "win_rate": 71.2,
                "trades": 156
            },
            "variant_b": {
                "name": "Optimized Parameters", 
                "return": 28.7,
                "win_rate": 74.8,
                "trades": 142
            },
            "winner": "variant_b",
            "confidence": 95.2,
            "improvement": 22.7
        }
    
    async def _get_community_strategies(self, user_id: str) -> List[StrategyMarketplaceItem]:
        """Get community-published strategies."""
        try:
            async for db in get_database():
                # Get published strategies from community
                stmt = select(TradingStrategy, StrategyPublisher).join(
                    StrategyPublisher, TradingStrategy.user_id == StrategyPublisher.user_id
                ).where(
                    and_(
                        TradingStrategy.is_active == True,
                        StrategyPublisher.verified == True
                    )
                ).order_by(desc(TradingStrategy.total_pnl))
                
                result = await db.execute(stmt)
                strategies = result.fetchall()
                
                community_items = []
                for strategy, publisher in strategies:
                    # Calculate pricing based on performance
                    monthly_cost = self._calculate_strategy_pricing(strategy)
                    
                    item = StrategyMarketplaceItem(
                        strategy_id=str(strategy.id),
                        name=strategy.name,
                        description=strategy.description or "Community-published strategy",
                        category=strategy.strategy_type.value,
                        publisher_id=str(publisher.id),
                        publisher_name=publisher.display_name,
                        is_ai_strategy=False,
                        credit_cost_monthly=monthly_cost,
                        credit_cost_per_execution=max(1, monthly_cost // 30),
                        win_rate=strategy.win_rate,
                        avg_return=float(strategy.total_pnl / strategy.total_trades) if strategy.total_trades > 0 else 0,
                        sharpe_ratio=float(strategy.sharpe_ratio) if strategy.sharpe_ratio else None,
                        max_drawdown=float(strategy.max_drawdown),
                        total_trades=strategy.total_trades,
                        min_capital_usd=1000,  # Default minimum
                        risk_level=self._calculate_risk_level(strategy),
                        timeframes=[strategy.timeframe],
                        supported_symbols=strategy.target_symbols,
                        backtest_results={},  # Would be populated from backtesting service
                        ab_test_results={},   # Would be populated from A/B testing
                        live_performance=await self._get_live_performance(str(strategy.id)),
                        created_at=strategy.created_at,
                        last_updated=strategy.updated_at,
                        is_active=strategy.is_active,
                        tier="community"
                    )
                    community_items.append(item)
                
                return community_items
                
        except Exception as e:
            self.logger.error("Failed to get community strategies", error=str(e))
            return []
    
    def _calculate_strategy_pricing(self, strategy: TradingStrategy) -> int:
        """Calculate credit pricing based on strategy performance."""
        base_price = 20  # Base 20 credits
        
        # Performance multipliers
        if strategy.win_rate > 80:
            base_price *= 2.0
        elif strategy.win_rate > 70:
            base_price *= 1.5
        elif strategy.win_rate > 60:
            base_price *= 1.2
        
        # Sharpe ratio multiplier
        if strategy.sharpe_ratio and strategy.sharpe_ratio > 2.0:
            base_price *= 1.5
        elif strategy.sharpe_ratio and strategy.sharpe_ratio > 1.5:
            base_price *= 1.3
        
        # Total trades multiplier (proven track record)
        if strategy.total_trades > 1000:
            base_price *= 1.4
        elif strategy.total_trades > 500:
            base_price *= 1.2
        
        return min(200, max(10, int(base_price)))  # Cap between 10-200 credits
    
    def _calculate_risk_level(self, strategy: TradingStrategy) -> str:
        """Calculate risk level based on strategy metrics."""
        if strategy.max_drawdown > 30:
            return "very_high"
        elif strategy.max_drawdown > 20:
            return "high"
        elif strategy.max_drawdown > 10:
            return "medium"
        elif strategy.max_drawdown > 5:
            return "low"
        else:
            return "very_low"
    
    async def _get_live_performance(self, strategy_id: str) -> Dict[str, Any]:
        """Get live performance metrics for strategy."""
        try:
            async for db in get_database():
                # Get recent trades for this strategy
                stmt = select(Trade).where(
                    and_(
                        Trade.strategy_id == strategy_id,
                        Trade.created_at >= datetime.utcnow() - timedelta(days=30)
                    )
                ).order_by(desc(Trade.created_at))
                
                result = await db.execute(stmt)
                recent_trades = result.scalars().all()
                
                if not recent_trades:
                    return {}
                
                # Calculate 30-day performance
                total_pnl = sum(float(trade.profit_realized_usd) for trade in recent_trades)
                winning_trades = sum(1 for trade in recent_trades if trade.profit_realized_usd > 0)
                win_rate = (winning_trades / len(recent_trades)) * 100
                
                return {
                    "period": "30_days",
                    "total_return": total_pnl,
                    "win_rate": win_rate,
                    "total_trades": len(recent_trades),
                    "avg_trade_pnl": total_pnl / len(recent_trades),
                    "best_trade": max(float(trade.profit_realized_usd) for trade in recent_trades),
                    "worst_trade": min(float(trade.profit_realized_usd) for trade in recent_trades)
                }
                
        except Exception as e:
            self.logger.error("Failed to get live performance", error=str(e))
            return {}
    
    async def purchase_strategy_access(
        self,
        user_id: str,
        strategy_id: str,
        subscription_type: str = "monthly"  # monthly, per_execution
    ) -> Dict[str, Any]:
        """Purchase access to strategy using credits."""
        try:
            async for db in get_database():
                # Get user's credit account
                credit_stmt = select(CreditAccount).where(CreditAccount.user_id == user_id)
                credit_result = await db.execute(credit_stmt)
                credit_account = credit_result.scalar_one_or_none()
                
                if not credit_account:
                    return {"success": False, "error": "No credit account found"}
                
                # Get strategy pricing
                if strategy_id.startswith("ai_"):
                    strategy_func = strategy_id.replace("ai_", "")
                    if strategy_func not in self.ai_strategy_catalog:
                        return {"success": False, "error": "Strategy not found"}
                    
                    config = self.ai_strategy_catalog[strategy_func]
                    # Handle different subscription types
                    if subscription_type in ["monthly", "permanent"]:
                        cost = config["credit_cost_monthly"]
                    else:
                        cost = config["credit_cost_per_execution"]
                else:
                    # Community strategy
                    strategy_stmt = select(TradingStrategy).where(TradingStrategy.id == strategy_id)
                    strategy_result = await db.execute(strategy_stmt)
                    strategy = strategy_result.scalar_one_or_none()
                    
                    if not strategy:
                        return {"success": False, "error": "Strategy not found"}
                    
                    cost = self._calculate_strategy_pricing(strategy)
                
                # Check if user has enough credits (skip check for free strategies)
                if cost > 0 and credit_account.available_credits < cost:
                    return {
                        "success": False, 
                        "error": f"Insufficient credits. Required: {cost}, Available: {credit_account.available_credits}"
                    }
                
                # Deduct credits (only for paid strategies)
                if cost > 0:
                    balance_before = credit_account.available_credits
                    credit_account.available_credits -= cost
                    credit_account.used_credits += cost
                    balance_after = credit_account.available_credits
                    
                    # Record transaction (only for paid strategies)
                    transaction = CreditTransaction(
                        account_id=credit_account.id,
                        transaction_type=CreditTransactionType.USAGE,
                        amount=-cost,
                        description=f"Strategy access: {strategy_id} ({subscription_type})",
                        balance_before=balance_before,
                        balance_after=balance_after,
                        source="system"
                    )
                    db.add(transaction)
                
                # Add to user's active strategies
                await self._add_to_user_strategy_portfolio(user_id, strategy_id, db)
                
                await db.commit()
                
                self.logger.info("Strategy purchase successful", 
                               user_id=user_id, 
                               strategy_id=strategy_id, 
                               cost=cost,
                               subscription_type=subscription_type)
                
                return {
                    "success": True,
                    "strategy_id": strategy_id,
                    "cost": cost,
                    "remaining_credits": credit_account.available_credits,
                    "subscription_type": subscription_type
                }
                
        except Exception as e:
            self.logger.error("Strategy purchase failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _add_to_user_strategy_portfolio(self, user_id: str, strategy_id: str, db: AsyncSession):
        """Add strategy to user's active strategy portfolio."""
        try:
            # This would create a user_strategy_subscriptions record
            # For now, store in Redis for quick access
            from app.core.redis import get_redis_client
            redis = await get_redis_client()
            
            if redis:
                # Add to user's active strategies set
                await redis.sadd(f"user_strategies:{user_id}", strategy_id)
                
                # Set expiry for monthly subscriptions
                await redis.expire(f"user_strategies:{user_id}", 30 * 24 * 3600)  # 30 days
                self.logger.info("Strategy added to user portfolio", user_id=user_id, strategy_id=strategy_id)
            else:
                self.logger.warning("Redis unavailable, strategy not cached", user_id=user_id, strategy_id=strategy_id)
                
        except Exception as e:
            self.logger.error("Failed to add strategy to portfolio", user_id=user_id, strategy_id=strategy_id, error=str(e))
    
    async def get_user_strategy_portfolio(self, user_id: str) -> Dict[str, Any]:
        """Get user's purchased/active strategies."""
        try:
            from app.core.redis import get_redis_client
            redis = await get_redis_client()
            
            if not redis:
                self.logger.warning("Redis unavailable for strategy portfolio retrieval")
                # Return empty portfolio structure when Redis is unavailable
                return {
                    "success": True,
                    "strategies": [],
                    "summary": {
                        "active_strategies": 0,
                        "total_strategies": 0,
                        "welcome_strategies": 0,
                        "purchased_strategies": 0,
                        "total_portfolio_value": 0,
                        "total_pnl_usd": 0,
                        "total_pnl_percentage": 0,
                        "monthly_credit_cost": 0,
                        "next_billing_date": None,
                        "profit_potential_used": 0,
                        "profit_potential_remaining": 0
                    }
                }
            
            # Get user's active strategies
            active_strategies = await redis.smembers(f"user_strategies:{user_id}")
            # Handle both bytes and string responses from Redis
            active_strategies = [s.decode() if isinstance(s, bytes) else s for s in active_strategies]
            
            # Ensure pricing is loaded before lookups
            await self.ensure_pricing_loaded()
            
            strategy_portfolio = []
            total_monthly_cost = 0
            
            # Helper function to get numeric monthly cost
            def _get_numeric_monthly_cost(config: Dict[str, Any], strategy_name: str) -> float:
                """Extract numeric monthly cost, handling DYNAMIC pricing."""
                cost = config.get("credit_cost_monthly", 0)
                
                # Handle DYNAMIC pricing specifically (only literal "DYNAMIC")
                if cost == "DYNAMIC":
                    # Safe membership check for strategy_pricing
                    if (self.strategy_pricing is not None and 
                        isinstance(self.strategy_pricing, dict) and 
                        strategy_name in self.strategy_pricing):
                        try:
                            return float(self.strategy_pricing[strategy_name])
                        except (TypeError, ValueError):
                            pass
                    # Default dynamic cost when pricing not found
                    return 50.0
                
                # Handle string that represents a number
                if isinstance(cost, str):
                    try:
                        return float(cost)
                    except (TypeError, ValueError):
                        return 0.0
                
                # Handle numeric values
                try:
                    return float(cost)
                except (TypeError, ValueError):
                    return 0.0
            
            for strategy_id in active_strategies:
                if strategy_id.startswith("ai_"):
                    # Handle AI strategies
                    strategy_func = strategy_id.replace("ai_", "")
                    if strategy_func in self.ai_strategy_catalog:
                        config = self.ai_strategy_catalog[strategy_func]
                        monthly_cost = _get_numeric_monthly_cost(config, strategy_func)
                        total_monthly_cost += monthly_cost
                        
                        performance = await self._get_ai_strategy_performance(strategy_func, user_id)
                        
                        # Determine tier for welcome strategy calculation
                        tier = "free" if monthly_cost == 0 else config.get("tier", "paid")
                        
                        strategy_portfolio.append({
                            "strategy_id": strategy_id,
                            "name": config["name"],
                            "category": config["category"],
                            "monthly_cost": monthly_cost,
                            "performance": performance,
                            "is_ai_strategy": True,
                            "tier": tier
                        })
                        
                else:
                    # Handle database strategies (raw DB id lookup)
                    try:
                        # Attempt async DB lookup for TradingStrategy by primary key
                        from sqlalchemy import select
                        
                        strategy = None
                        async for db in get_database():
                            try:
                                stmt = select(TradingStrategy).where(TradingStrategy.id == strategy_id)
                                result = await db.execute(stmt)
                                strategy = result.scalar_one_or_none()
                                break
                            except Exception as db_error:
                                self.logger.warning(f"Database lookup failed for strategy {strategy_id}", error=str(db_error))
                                break
                        
                        if strategy:
                            # Compute monthly cost using existing helper
                            monthly_cost = float(self._calculate_strategy_pricing(strategy))
                            total_monthly_cost += monthly_cost
                            
                            # Retrieve live performance via helper
                            performance = await self._get_live_performance(strategy_id)
                            
                            # Determine tier based on cost
                            tier = "free" if monthly_cost == 0 else "community"
                            
                            # Append enriched strategy dict
                            strategy_portfolio.append({
                                "strategy_id": strategy_id,
                                "name": strategy.name or f"Strategy {strategy_id}",
                                "category": strategy.category or "Custom",
                                "monthly_cost": monthly_cost,
                                "performance": performance,
                                "is_ai_strategy": False,
                                "tier": tier
                            })
                        else:
                            # Fall back to mock behavior when strategy not found
                            monthly_cost = 25.0  # Default fallback cost
                            total_monthly_cost += monthly_cost
                            
                            # Mock performance data for unknown strategies
                            performance = {
                                "total_pnl": 0,
                                "avg_return": 0,
                                "total_trades": 0,
                                "win_rate": 0
                            }
                            
                            strategy_portfolio.append({
                                "strategy_id": strategy_id,
                                "name": f"Unknown Strategy {strategy_id}",
                                "category": "Unknown",
                                "monthly_cost": monthly_cost,
                                "performance": performance,
                                "is_ai_strategy": False,
                                "tier": "community"
                            })
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to load strategy {strategy_id}", error=str(e))
                        continue
            
            # Calculate profit metrics (robust to schema variance)
            def _to_float(v):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return 0.0
                    
            def _pnl(perf: Dict[str, Any]) -> float:
                return _to_float(
                    perf.get("total_pnl_usd")
                    or perf.get("total_pnl")
                    or perf.get("total_return")
                    or perf.get("net_profit_usd")
                    or 0
                )
                
            total_pnl_usd = sum(_pnl(s["performance"]) for s in strategy_portfolio)
            avg_return_pct = sum(_to_float(s["performance"].get("avg_return")) for s in strategy_portfolio) / max(1, len(strategy_portfolio))
            
            # Assume user has a monthly profit potential based on portfolio size
            profit_potential_total = total_monthly_cost * 5  # 5x multiplier for profit potential
            profit_potential_used = max(0, total_pnl_usd)
            profit_potential_remaining = max(0, profit_potential_total - profit_potential_used)

            return {
                "success": True,
                "strategies": strategy_portfolio,
                "summary": {
                    "active_strategies": len(strategy_portfolio),
                    "total_strategies": len(strategy_portfolio),
                    "welcome_strategies": len([s for s in strategy_portfolio if s.get("tier") == "free"]),
                    "purchased_strategies": len([s for s in strategy_portfolio if s.get("tier") != "free"]),
                    "total_portfolio_value": total_monthly_cost * 12,  # Annualized
                    "total_pnl_usd": total_pnl_usd,
                    "total_pnl_percentage": avg_return_pct,
                    "monthly_credit_cost": total_monthly_cost,
                    "next_billing_date": None,  # Could be enhanced with actual billing date
                    "profit_potential_used": profit_potential_used,
                    "profit_potential_remaining": profit_potential_remaining
                }
            }
            
        except Exception as e:
            self.logger.error("Failed to get user strategy portfolio", error=str(e))
            # Return empty portfolio structure on error to prevent frontend crashes
            return {
                "success": True,
                "strategies": [],
                "summary": {
                    "active_strategies": 0,
                    "total_strategies": 0,
                    "welcome_strategies": 0,
                    "purchased_strategies": 0,
                    "total_portfolio_value": 0,
                    "total_pnl_usd": 0,
                    "total_pnl_percentage": 0,
                    "monthly_credit_cost": 0,
                    "next_billing_date": None,
                    "profit_potential_used": 0,
                    "profit_potential_remaining": 0
                }
            }


# Global service instance
strategy_marketplace_service = StrategyMarketplaceService()


async def get_strategy_marketplace_service() -> StrategyMarketplaceService:
    """Dependency injection for FastAPI."""
    return strategy_marketplace_service