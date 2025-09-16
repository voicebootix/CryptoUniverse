"""
Profit Sharing Service - Revolutionary Revenue Model

Implements profit-based revenue sharing where users pay 25% of profits
and receive credits equal to platform fees for purchasing additional strategies.

This replaces traditional subscriptions with performance-based revenue sharing.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

import structlog
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_database
from app.core.logging import LoggerMixin
from app.models.user import User
from app.models.trading import Trade, TradingStrategy
from app.models.credit import CreditAccount, CreditTransaction, CreditTransactionType
from app.models.subscription import Subscription

settings = get_settings()
logger = structlog.get_logger(__name__)


class ProfitSharingService(LoggerMixin):
    """
    Revolutionary credit-based profit potential system.
    
    Users pay for profit potential in credits, get strategies to earn that potential.
    More strategies = faster profit generation.
    """
    
    def __init__(self):
        # Dynamic pricing configuration (loaded from admin settings)
        self.credit_to_profit_ratio = None   # Will be loaded dynamically
        self.credit_to_dollar_cost = None    # Will be loaded dynamically
        self.platform_fee_percentage = None # Will be loaded dynamically
        
        # Base package strategies (included free)
        self.base_package_strategies = [
            "risk_management",           # Essential risk control
            "portfolio_optimization",    # Basic portfolio management
            "spot_momentum_strategy"     # Basic momentum trading
        ]
        
        # Strategy pricing will be loaded dynamically
        self.strategy_pricing = None
    
    async def load_dynamic_pricing_config(self) -> Dict[str, Any]:
        """Load dynamic pricing configuration from admin settings."""
        try:
            from app.core.redis import get_redis_client
            redis = await get_redis_client()
            
            # Load admin pricing configuration
            pricing_config = await redis.hgetall("admin:pricing_config") if redis else {}
            
            if pricing_config:
                # Use admin-configured values
                self.platform_fee_percentage = float(pricing_config.get(b"platform_fee_percentage", 25)) / 100  # Default 25%
                self.credit_to_dollar_cost = float(pricing_config.get(b"credit_to_dollar_cost", 1.0))  # Default $1 = 1 credit
                
                # Calculate profit ratio: If fee is 25%, then $1 credit gives $4 profit potential
                self.credit_to_profit_ratio = 1.0 / self.platform_fee_percentage if self.platform_fee_percentage > 0 else 4.0
                
                # Load welcome package settings
                welcome_config = {
                    "welcome_profit_potential": float(pricing_config.get(b"welcome_profit_potential", 100)),  # $100 default
                    "welcome_strategies_count": int(pricing_config.get(b"welcome_strategies_count", 3)),  # 3 strategies
                    "welcome_enabled": pricing_config.get(b"welcome_enabled", b"true").decode() == "true"
                }
                
                self.logger.info(
                    "Dynamic pricing loaded from admin settings",
                    platform_fee=f"{self.platform_fee_percentage*100:.1f}%",
                    credit_to_profit_ratio=f"1:{self.credit_to_profit_ratio:.1f}",
                    welcome_profit_potential=f"${welcome_config['welcome_profit_potential']:.0f}"
                )
                
                return {
                    "success": True,
                    "pricing_config": {
                        "platform_fee_percentage": self.platform_fee_percentage,
                        "credit_to_profit_ratio": self.credit_to_profit_ratio,
                        "credit_to_dollar_cost": self.credit_to_dollar_cost
                    },
                    "welcome_config": welcome_config
                }
            else:
                # Set default values if no admin config
                self.platform_fee_percentage = 0.25  # 25% fee
                self.credit_to_profit_ratio = 4.0     # $1 credit = $4 profit potential  
                self.credit_to_dollar_cost = 1.0      # $1 = 1 credit
                
                # Save defaults to Redis for admin to modify
                await self._save_default_pricing_config(redis)
                
                self.logger.warning("No admin pricing config found, using defaults")
                
                return {
                    "success": True,
                    "pricing_config": {
                        "platform_fee_percentage": self.platform_fee_percentage,
                        "credit_to_profit_ratio": self.credit_to_profit_ratio,
                        "credit_to_dollar_cost": self.credit_to_dollar_cost
                    },
                    "welcome_config": {
                        "welcome_profit_potential": 100,
                        "welcome_strategies_count": 3,
                        "welcome_enabled": True
                    },
                    "using_defaults": True
                }
                
        except Exception as e:
            self.logger.error("Failed to load dynamic pricing config", error=str(e))
            
            # Emergency fallback
            self.platform_fee_percentage = 0.25
            self.credit_to_profit_ratio = 4.0
            self.credit_to_dollar_cost = 1.0
            
            return {"success": False, "error": str(e)}
    
    async def _save_default_pricing_config(self, redis):
        """Save default pricing configuration for admin to modify."""
        await redis.hset("admin:pricing_config", mapping={
            "platform_fee_percentage": 25,      # 25%
            "credit_to_dollar_cost": 1.0,       # $1 = 1 credit
            "welcome_profit_potential": 100,    # $100 profit potential for new users
            "welcome_strategies_count": 3,      # 3 free strategies
            "welcome_enabled": "true",          # Welcome package enabled
            "last_updated": datetime.utcnow().isoformat(),
            "updated_by": "system_default"
        })
    
    async def get_current_pricing_config(self) -> Dict[str, Any]:
        """Get current pricing configuration."""
        if self.credit_to_profit_ratio is None:
            await self.load_dynamic_pricing_config()
        
        return {
            "platform_fee_percentage": self.platform_fee_percentage * 100,  # Return as percentage
            "credit_to_profit_ratio": self.credit_to_profit_ratio,
            "credit_to_dollar_cost": self.credit_to_dollar_cost,
            "profit_potential_per_dollar": self.credit_to_profit_ratio,
            "example": {
                "pay_25_dollars": {
                    "credits_received": 25,
                    "profit_potential": 25 * self.credit_to_profit_ratio
                }
            }
        }
    
    async def _load_dynamic_strategy_pricing(self) -> Dict[str, int]:
        """Load strategy pricing from admin configuration."""
        try:
            from app.core.redis import get_redis_client
            redis = await get_redis_client()
            
            # Load strategy pricing from admin settings
            strategy_pricing_data = await redis.hgetall("admin:strategy_pricing") if redis else {}
            
            if strategy_pricing_data:
                # Convert bytes to proper format
                strategy_pricing = {}
                for key, value in strategy_pricing_data.items():
                    strategy_name = key.decode() if isinstance(key, bytes) else key
                    credit_cost = int(value.decode()) if isinstance(value, bytes) else int(value)
                    strategy_pricing[strategy_name] = credit_cost
                
                return strategy_pricing
            else:
                # Set default strategy pricing and save to Redis
                default_pricing = {
                    # AI Strategies (Your 25+ functions) - Dynamic pricing based on performance
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
                
                return default_pricing
                
        except Exception as e:
            self.logger.error("Failed to load strategy pricing", error=str(e))
            # Emergency fallback
            return {
                "spot_momentum_strategy": 15,
                "spot_mean_reversion": 20,
                "market_making": 25
            }
    
    async def ensure_pricing_loaded(self):
        """Ensure pricing configuration is loaded."""
        if self.credit_to_profit_ratio is None:
            await self.load_dynamic_pricing_config()
        
        if self.strategy_pricing is None:
            self.strategy_pricing = await self._load_dynamic_strategy_pricing()
    
    async def calculate_profit_potential_usage(
        self, 
        user_id: str, 
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Calculate how much profit potential user has used and remaining."""
        try:
            # Ensure pricing is loaded
            await self.ensure_pricing_loaded()
            
            async for db in get_database():
                # Get all completed trades in period
                stmt = select(Trade).where(
                    and_(
                        Trade.user_id == user_id,
                        Trade.status == "completed",
                        Trade.is_simulation == False,  # Only real trades
                        Trade.completed_at >= period_start,
                        Trade.completed_at <= period_end
                    )
                )
                
                result = await db.execute(stmt)
                trades = result.scalars().all()
                
                if not trades:
                    return {
                        "success": True,
                        "total_profit": 0,
                        "platform_fee": 0,
                        "user_keeps": 0,
                        "credits_earned": 0,
                        "message": "No profitable trades in period"
                    }
                
                # Calculate total profit earned
                total_profit_earned = sum(
                    float(trade.profit_realized_usd) 
                    for trade in trades 
                    if trade.profit_realized_usd > 0
                )
                
                # Get user's current credit account
                credit_stmt = select(CreditAccount).where(CreditAccount.user_id == user_id)
                credit_result = await db.execute(credit_stmt)
                credit_account = credit_result.scalar_one_or_none()
                
                if not credit_account:
                    return {"success": False, "error": "No credit account found"}
                
                # Calculate profit potential purchased
                total_credits_purchased = credit_account.total_purchased_credits
                profit_potential = total_credits_purchased * self.credit_to_profit_ratio
                
                # Calculate remaining profit potential
                remaining_potential = profit_potential - total_profit_earned
                
                # Check if user needs to buy more credits
                needs_more_credits = remaining_potential <= 0
                
                return {
                    "success": True,
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "total_profit_earned": total_profit_earned,
                    "total_credits_purchased": total_credits_purchased,
                    "profit_potential": profit_potential,
                    "remaining_potential": remaining_potential,
                    "needs_more_credits": needs_more_credits,
                    "utilization_percentage": (total_profit_earned / profit_potential * 100) if profit_potential > 0 else 0,
                    "trades_analyzed": len(trades),
                    "message": "Credits consumed as profits are earned" if not needs_more_credits else "Buy more credits to continue earning"
                }
                
        except Exception as e:
            self.logger.error("Profit sharing calculation failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def process_profit_sharing_payment(
        self,
        user_id: str,
        profit_sharing_data: Dict[str, Any],
        payment_method: str = "crypto"
    ) -> Dict[str, Any]:
        """Process profit sharing payment and credit allocation."""
        try:
            # Ensure pricing is loaded before using credit_to_profit_ratio
            await self.ensure_pricing_loaded()
            
            platform_fee = profit_sharing_data["platform_fee"]
            credits_earned = profit_sharing_data["credits_earned"]
            
            if platform_fee <= 0:
                return {"success": False, "error": "No platform fee to process"}
            
            async for db in get_database():
                # Get user's credit account
                credit_stmt = select(CreditAccount).where(CreditAccount.user_id == user_id)
                credit_result = await db.execute(credit_stmt)
                credit_account = credit_result.scalar_one_or_none()
                
                if not credit_account:
                    # Create credit account if doesn't exist
                    credit_account = CreditAccount(
                        user_id=user_id,
                        available_credits=0,
                        total_purchased_credits=0,
                        total_used_credits=0
                    )
                    db.add(credit_account)
                    await db.flush()
                
                # Process payment (this would integrate with crypto payment gateway)
                payment_result = await self._process_crypto_payment(
                    user_id=user_id,
                    amount_usd=platform_fee,
                    payment_method=payment_method
                )
                
                if not payment_result.get("success"):
                    return {
                        "success": False,
                        "error": f"Payment processing failed: {payment_result.get('error')}"
                    }
                
                # Add credits to user account
                credit_account.available_credits += credits_earned
                credit_account.total_purchased_credits += credits_earned
                
                # Record transaction
                transaction = CreditTransaction(
                    account_id=credit_account.id,
                    amount=credits_earned,
                    transaction_type=CreditTransactionType.PURCHASE,
                    description=f"Profit sharing purchase: Paid ${platform_fee:.2f}, earned {credits_earned} credits",
                    balance_before=credit_account.available_credits - credits_earned,
                    balance_after=credit_account.available_credits,
                    source="system"
                )
                db.add(transaction)
                
                await db.commit()
                
                self.logger.info(
                    "Profit sharing processed",
                    user_id=user_id,
                    platform_fee=platform_fee,
                    credits_earned=credits_earned,
                    payment_method=payment_method
                )
                
                return {
                    "success": True,
                    "payment_processed": platform_fee,
                    "credits_earned": credits_earned,
                    "new_credit_balance": credit_account.available_credits,
                    "payment_id": payment_result.get("payment_id"),
                    "earning_potential": credits_earned * self.credit_to_profit_ratio
                }
                
        except Exception as e:
            self.logger.error("Profit sharing payment failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _process_crypto_payment(
        self,
        user_id: str,
        amount_usd: float,
        payment_method: str
    ) -> Dict[str, Any]:
        """Process cryptocurrency payment for profit sharing."""
        try:
            # This would integrate with crypto payment processors:
            # - Bitcoin Lightning Network
            # - Ethereum/USDC payments
            # - Binance Pay
            # - Coinbase Commerce
            
            # For now, simulate successful payment
            payment_id = f"crypto_{int(datetime.utcnow().timestamp())}_{user_id[:8]}"
            
            return {
                "success": True,
                "payment_id": payment_id,
                "amount_usd": amount_usd,
                "payment_method": payment_method,
                "transaction_hash": f"0x{payment_id}",
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Crypto payment processing failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def get_user_strategy_budget(self, user_id: str) -> Dict[str, Any]:
        """Get user's strategy purchasing budget and recommendations."""
        try:
            async for db in get_database():
                # Get credit account
                credit_stmt = select(CreditAccount).where(CreditAccount.user_id == user_id)
                credit_result = await db.execute(credit_stmt)
                credit_account = credit_result.scalar_one_or_none()
                
                available_credits = credit_account.available_credits if credit_account else 0
                
                # Get currently active strategies
                from app.core.redis import get_redis_client
                redis = await get_redis_client()
                active_strategies = await redis.smembers(f"user_strategies:{user_id}")
                active_strategies = [s.decode() for s in active_strategies]
                
                # Calculate current monthly cost
                current_monthly_cost = 0
                for strategy_id in active_strategies:
                    if strategy_id.startswith("ai_"):
                        strategy_func = strategy_id.replace("ai_", "")
                        current_monthly_cost += self.strategy_pricing.get(strategy_func, 20)
                
                # Calculate budget recommendations
                budget_recommendations = self._generate_budget_recommendations(
                    available_credits, 
                    current_monthly_cost,
                    active_strategies
                )
                
                return {
                    "success": True,
                    "available_credits": available_credits,
                    "earning_potential": available_credits * self.credit_to_dollar_ratio,
                    "active_strategies": len(active_strategies),
                    "current_monthly_cost": current_monthly_cost,
                    "remaining_budget": available_credits - current_monthly_cost,
                    "base_package_strategies": self.base_package_strategies,
                    "recommendations": budget_recommendations
                }
                
        except Exception as e:
            self.logger.error("Failed to get strategy budget", error=str(e))
            return {"success": False, "error": str(e)}
    
    def _generate_budget_recommendations(
        self, 
        available_credits: int,
        current_cost: int,
        active_strategies: List[str]
    ) -> Dict[str, Any]:
        """Generate strategy purchase recommendations based on budget."""
        
        remaining_budget = available_credits - current_cost
        
        if remaining_budget < 20:
            return {
                "recommendation": "earn_more_profit",
                "message": "Generate more profits to unlock additional strategies",
                "suggested_target": "$100 profit to earn 25 more credits"
            }
        
        # Recommend strategies based on budget
        affordable_strategies = []
        for strategy, cost in self.strategy_pricing.items():
            if cost <= remaining_budget and f"ai_{strategy}" not in active_strategies:
                affordable_strategies.append({
                    "strategy": strategy,
                    "cost": cost,
                    "value_score": self._calculate_strategy_value_score(strategy)
                })
        
        # Sort by value score
        affordable_strategies.sort(key=lambda x: x["value_score"], reverse=True)
        
        return {
            "recommendation": "expand_portfolio",
            "remaining_budget": remaining_budget,
            "affordable_strategies": affordable_strategies[:5],
            "optimization_tip": "Higher performing strategies cost more but generate higher returns"
        }
    
    def _calculate_strategy_value_score(self, strategy: str) -> float:
        """Calculate value score for strategy recommendation."""
        # This would use real performance data
        # For now, return based on strategy type
        value_scores = {
            "scalping_strategy": 9.5,      # High frequency, high returns
            "arbitrage_execution": 9.0,    # Low risk, consistent profits
            "futures_trade": 8.5,          # High returns, higher risk
            "spot_momentum_strategy": 8.0, # Reliable, medium returns
            "options_trade": 7.5,          # Complex, high potential
            "pairs_trading": 7.0,          # Sophisticated, steady
            "market_making": 6.5,          # Conservative, steady income
        }
        return value_scores.get(strategy, 6.0)
    
    async def setup_new_user_welcome_package(self, user_id: str) -> Dict[str, Any]:
        """
        SETUP $100 FREE CREDIT WELCOME PACKAGE FOR NEW USERS
        
        Give new users $100 profit potential + 3 basic strategies for free!
        This is our customer acquisition strategy.
        """
        try:
            # Load dynamic pricing configuration
            pricing_result = await self.load_dynamic_pricing_config()
            
            if not pricing_result.get("success"):
                return {"success": False, "error": "Failed to load pricing configuration"}
            
            welcome_config = pricing_result.get("welcome_config", {})
            
            # Check if welcome package is enabled
            if not welcome_config.get("welcome_enabled", True):
                return {
                    "success": False,
                    "error": "Welcome package is currently disabled",
                    "disabled": True
                }
            
            from app.core.database import get_async_session
            from app.models.user import User
            from app.models.credit import CreditTransaction
            from app.services.strategy_marketplace_service import strategy_marketplace_service
            from sqlalchemy import select
            
            async with get_async_session() as db:
                # Check if user already received welcome package
                existing_welcome = await db.execute(
                    select(CreditTransaction).join(
                        CreditAccount, CreditTransaction.account_id == CreditAccount.id
                    ).where(
                        CreditAccount.user_id == user_id,
                        CreditTransaction.transaction_type == "welcome_bonus"
                    )
                )
                
                if existing_welcome.first():
                    return {
                        "success": False,
                        "error": "User already received welcome package",
                        "already_claimed": True
                    }
                
                # Get or create user's credit account
                credit_stmt = select(CreditAccount).where(CreditAccount.user_id == user_id)
                credit_result = await db.execute(credit_stmt)
                credit_account = credit_result.scalar_one_or_none()
                
                if not credit_account:
                    # Create new credit account for user
                    credit_account = CreditAccount(
                        user_id=user_id,
                        available_credits=0,
                        total_credits=0,
                        used_credits=0
                    )
                    db.add(credit_account)
                    await db.flush()  # Get the ID
                
                # Calculate welcome credits based on admin configuration
                welcome_profit_potential = welcome_config.get("welcome_profit_potential", 100)
                welcome_credits = int(welcome_profit_potential * self.platform_fee_percentage)  # 25% of profit potential
                
                # Update credit account balances
                balance_before = credit_account.available_credits
                credit_account.available_credits += welcome_credits
                credit_account.total_credits += welcome_credits
                balance_after = credit_account.available_credits
                
                # Create welcome credit transaction
                welcome_transaction = CreditTransaction(
                    account_id=credit_account.id,
                    amount=welcome_credits,  # Dynamic credit amount
                    transaction_type=CreditTransactionType.BONUS,
                    description=f"Welcome Package: ${welcome_profit_potential:.0f} Free Profit Potential ({welcome_credits} credits)",
                    balance_before=balance_before,
                    balance_after=balance_after,
                    source="system"
                )
                
                db.add(welcome_transaction)
                await db.commit()
                
                # Add strategies based on admin configuration
                strategies_count = welcome_config.get("welcome_strategies_count", 3)
                basic_strategies = self.base_package_strategies[:strategies_count]
                
                strategy_results = []
                for strategy in basic_strategies:
                    # Add strategy to user's portfolio (free)
                    purchase_result = await strategy_marketplace_service.purchase_strategy(
                        user_id=user_id,
                        strategy_id=f"ai_{strategy}",
                        payment_amount=0,  # Free for welcome package
                        payment_method="welcome_bonus"
                    )
                    strategy_results.append({
                        "strategy": strategy,
                        "success": purchase_result.get("success", False)
                    })
                
                # Update user's credit balance with dynamic amount
                await self._update_user_credit_balance(user_id, welcome_credits, "welcome_bonus")
                
                self.logger.info(
                    f"🎁 Welcome package setup complete for {user_id}",
                    free_credits=welcome_credits,
                    profit_potential=welcome_profit_potential,
                    free_strategies=len(basic_strategies),
                    strategies_added=len([r for r in strategy_results if r["success"]])
                )
                
                return {
                    "success": True,
                    "welcome_package": {
                        "free_credits": welcome_credits,
                        "profit_potential_usd": welcome_profit_potential,
                        "free_strategies": basic_strategies,
                        "strategies_activated": len([r for r in strategy_results if r["success"]]),
                        "message": f"Welcome! Start earning up to ${welcome_profit_potential:.0f} with {len(basic_strategies)} free strategies!"
                    },
                    "strategy_results": strategy_results
                }
                
        except Exception as e:
            self.logger.error("Welcome package setup failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _update_user_credit_balance(self, user_id: str, amount: int, transaction_type: str):
        """Update user's credit balance in Redis."""
        try:
            from app.core.redis import get_redis_client
            redis = await get_redis_client()
            
            # Get current balance
            current_balance_key = f"user_credits:{user_id}"
            current_balance = await redis.get(current_balance_key)
            current_balance = int(current_balance) if current_balance else 0
            
            # Add credits
            new_balance = current_balance + amount
            
            # Update balance
            await redis.set(current_balance_key, new_balance, ex=365 * 24 * 3600)  # 1 year expiry
            
            # Log transaction
            transaction_key = f"credit_transactions:{user_id}"
            transaction_data = {
                "amount": amount,
                "type": transaction_type,
                "timestamp": datetime.utcnow().isoformat(),
                "new_balance": new_balance
            }
            
            await redis.lpush(transaction_key, json.dumps(transaction_data))
            await redis.ltrim(transaction_key, 0, 99)  # Keep last 100 transactions
            await redis.expire(transaction_key, 365 * 24 * 3600)  # 1 year
            
        except Exception as e:
            self.logger.error("Credit balance update failed", error=str(e))


# Global service instance
profit_sharing_service = ProfitSharingService()


async def get_profit_sharing_service() -> ProfitSharingService:
    """Dependency injection for FastAPI."""
    return profit_sharing_service