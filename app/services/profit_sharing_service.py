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
from app.models.credit import CreditAccount, CreditTransaction
from app.models.subscription import Subscription

settings = get_settings()
logger = structlog.get_logger(__name__)


class ProfitSharingService(LoggerMixin):
    """
    Revolutionary profit-sharing service.
    
    Users pay 25% of profits, get credits equal to fees paid,
    can use credits to purchase additional strategies.
    """
    
    def __init__(self):
        self.profit_share_percentage = 25.0  # 25% of profits
        self.credit_to_dollar_ratio = 1.0    # 1 credit = $1 earning potential
        
        # Base package strategies (included free)
        self.base_package_strategies = [
            "risk_management",           # Essential risk control
            "portfolio_optimization",    # Basic portfolio management
            "spot_momentum_strategy"     # Basic momentum trading
        ]
        
        # Strategy pricing in credits (based on performance and sophistication)
        self.strategy_pricing = {
            # AI Strategies (Your 25+ functions)
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
            "hedge_position": 65,
            
            # Community strategies will be priced dynamically based on performance
        }
    
    async def calculate_profit_sharing(
        self, 
        user_id: str, 
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Calculate profit sharing and credit allocation for user."""
        try:
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
                
                # Calculate total profit (only positive P&L)
                total_profit = sum(
                    float(trade.profit_realized_usd) 
                    for trade in trades 
                    if trade.profit_realized_usd > 0
                )
                
                # Calculate total losses (for net calculation)
                total_losses = sum(
                    abs(float(trade.profit_realized_usd))
                    for trade in trades
                    if trade.profit_realized_usd < 0
                )
                
                # Net profit calculation
                net_profit = total_profit - total_losses
                
                if net_profit <= 0:
                    return {
                        "success": True,
                        "total_profit": 0,
                        "platform_fee": 0,
                        "user_keeps": 0,
                        "credits_earned": 0,
                        "message": "No net profit in period"
                    }
                
                # Calculate platform fee (25% of NET profit)
                platform_fee = net_profit * (self.profit_share_percentage / 100)
                user_keeps = net_profit - platform_fee
                
                # Credits earned = platform fee paid (1:1 ratio)
                credits_earned = int(platform_fee * self.credit_to_dollar_ratio)
                
                return {
                    "success": True,
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "total_profit": total_profit,
                    "total_losses": total_losses,
                    "net_profit": net_profit,
                    "platform_fee": platform_fee,
                    "user_keeps": user_keeps,
                    "credits_earned": credits_earned,
                    "profit_share_percentage": self.profit_share_percentage,
                    "trades_analyzed": len(trades)
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
                    user_id=user_id,
                    amount=credits_earned,
                    transaction_type="profit_sharing_payment",
                    description=f"Profit sharing: Paid ${platform_fee:.2f}, earned {credits_earned} credits",
                    reference_id=payment_result.get("payment_id"),
                    status="completed"
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
                    "earning_potential": credits_earned * self.credit_to_dollar_ratio
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


# Global service instance
profit_sharing_service = ProfitSharingService()


async def get_profit_sharing_service() -> ProfitSharingService:
    """Dependency injection for FastAPI."""
    return profit_sharing_service