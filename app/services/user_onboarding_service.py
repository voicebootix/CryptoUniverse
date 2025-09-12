"""
ENTERPRISE USER ONBOARDING SERVICE

Auto-provisions new users with:
- 3 Free AI Trading Strategies (risk_management, portfolio_optimization, spot_momentum_strategy)
- Credit account initialization
- Default strategy portfolio setup
- Integration with strategy marketplace

This ensures every new user can immediately discover opportunities through chat.

NO MOCK DATA - PRODUCTION READY

Author: CTO Assistant  
Date: 2025-09-12
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import get_settings
from app.core.database import get_database
from app.core.logging import LoggerMixin
from app.models.user import User
from app.models.credit import CreditAccount, CreditTransaction, CreditTransactionType
from app.services.strategy_marketplace_service import strategy_marketplace_service
from app.core.redis import get_redis_client
import json

settings = get_settings()


class UserOnboardingService(LoggerMixin):
    """
    ENTERPRISE USER ONBOARDING SERVICE
    
    Handles complete new user setup including:
    - Auto-provisioning 3 free AI strategies
    - Credit account initialization  
    - Strategy portfolio setup
    - Welcome bonus credits
    """
    
    def __init__(self):
        super().__init__()
        
        # 3 FREE STRATEGIES for all new users
        self.free_strategies = [
            {
                "strategy_id": "ai_risk_management",
                "name": "AI Risk Management", 
                "description": "Essential portfolio protection and risk assessment",
                "category": "portfolio",
                "cost": 0
            },
            {
                "strategy_id": "ai_portfolio_optimization",
                "name": "AI Portfolio Optimization",
                "description": "Smart portfolio rebalancing and allocation optimization", 
                "category": "portfolio",
                "cost": 0
            },
            {
                "strategy_id": "ai_spot_momentum_strategy", 
                "name": "AI Spot Momentum Trading",
                "description": "Catch trending moves in spot markets",
                "category": "spot",
                "cost": 0
            }
        ]
        
        # Welcome bonus configuration
        self.welcome_bonus_credits = 100  # New users get 100 welcome credits
        self.referral_bonus_credits = 50   # Additional credits for referred users
    
    async def onboard_new_user(
        self,
        user_id: str,
        referral_code: Optional[str] = None,
        welcome_package: str = "standard"  # standard, premium
    ) -> Dict[str, Any]:
        """
        Complete new user onboarding process.
        
        Args:
            user_id: User's UUID
            referral_code: Optional referral code
            welcome_package: Onboarding package type
            
        Returns:
            Comprehensive onboarding result
        """
        
        onboarding_start = datetime.utcnow()
        onboarding_id = f"onboard_{user_id}_{int(onboarding_start.timestamp())}"
        
        self.logger.info("🚀 ENTERPRISE User Onboarding Starting",
                        onboarding_id=onboarding_id,
                        user_id=user_id,
                        package=welcome_package)
        
        try:
            async for db in get_database():
                # Verify user exists
                user_stmt = select(User).where(User.id == user_id)
                user_result = await db.execute(user_stmt)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return {
                        "success": False,
                        "error": "User not found",
                        "onboarding_id": onboarding_id
                    }
                
                # Check if user is already onboarded
                existing_credit_stmt = select(CreditAccount).where(CreditAccount.user_id == user_id)
                existing_credit_result = await db.execute(existing_credit_stmt)
                existing_credit_account = existing_credit_result.scalar_one_or_none()
                
                if existing_credit_account and existing_credit_account.total_earned_credits > 0:
                    self.logger.info("User already onboarded, skipping",
                                   onboarding_id=onboarding_id, 
                                   user_id=user_id)
                    return {
                        "success": True,
                        "message": "User already onboarded",
                        "onboarding_id": onboarding_id,
                        "skipped": True
                    }
                
                onboarding_results = {}
                
                # STEP 1: Initialize or update credit account
                credit_result = await self._initialize_credit_account(
                    user_id, db, referral_code, onboarding_id
                )
                onboarding_results["credit_account"] = credit_result
                
                # STEP 2: Provision free strategies
                strategies_result = await self._provision_free_strategies(
                    user_id, onboarding_id
                )
                onboarding_results["free_strategies"] = strategies_result
                
                # STEP 3: Setup strategy portfolio tracking
                portfolio_result = await self._setup_strategy_portfolio(
                    user_id, onboarding_id
                )
                onboarding_results["strategy_portfolio"] = portfolio_result
                
                # STEP 4: Welcome package extras
                if welcome_package == "premium":
                    premium_result = await self._apply_premium_welcome_package(
                        user_id, db, onboarding_id
                    )
                    onboarding_results["premium_package"] = premium_result
                
                # STEP 5: Process referral bonuses
                if referral_code:
                    referral_result = await self._process_referral_bonuses(
                        user_id, referral_code, db, onboarding_id
                    )
                    onboarding_results["referral_bonus"] = referral_result
                
                await db.commit()
                
                # STEP 6: Cache user onboarding status
                await self._cache_onboarding_status(user_id, onboarding_results)
                
                execution_time = (datetime.utcnow() - onboarding_start).total_seconds() * 1000
                
                self.logger.info("✅ ENTERPRISE User Onboarding Completed",
                               onboarding_id=onboarding_id,
                               user_id=user_id,
                               execution_time_ms=execution_time,
                               strategies_provisioned=len(self.free_strategies))
                
                return {
                    "success": True,
                    "onboarding_id": onboarding_id,
                    "user_id": user_id,
                    "results": onboarding_results,
                    "execution_time_ms": execution_time,
                    "onboarded_at": onboarding_start.isoformat(),
                    "next_steps": [
                        "Start chatting to discover your first opportunities",
                        "Connect your exchange accounts for live trading",
                        "Explore premium strategies in the marketplace"
                    ]
                }
                
        except Exception as e:
            execution_time = (datetime.utcnow() - onboarding_start).total_seconds() * 1000
            self.logger.error("💥 ENTERPRISE User Onboarding Failed",
                            onboarding_id=onboarding_id,
                            user_id=user_id,
                            execution_time_ms=execution_time,
                            error=str(e),
                            exc_info=True)
            
            return {
                "success": False,
                "error": f"Onboarding failed: {str(e)}",
                "onboarding_id": onboarding_id,
                "user_id": user_id
            }
    
    async def _initialize_credit_account(
        self,
        user_id: str,
        db: AsyncSession,
        referral_code: Optional[str],
        onboarding_id: str
    ) -> Dict[str, Any]:
        """Initialize credit account with welcome bonus."""
        
        try:
            # Check if credit account already exists
            credit_stmt = select(CreditAccount).where(CreditAccount.user_id == user_id)
            credit_result = await db.execute(credit_stmt)
            credit_account = credit_result.scalar_one_or_none()
            
            welcome_credits = self.welcome_bonus_credits
            if referral_code:
                welcome_credits += self.referral_bonus_credits
            
            if not credit_account:
                # Create new credit account
                credit_account = CreditAccount(
                    user_id=user_id,
                    available_credits=welcome_credits,
                    total_earned_credits=welcome_credits,
                    total_used_credits=0,
                    credit_limit=1000,  # Default credit limit
                    last_updated=datetime.utcnow()
                )
                db.add(credit_account)
                await db.flush()  # Get ID
                
                # Create welcome bonus transaction
                welcome_transaction = CreditTransaction(
                    user_id=user_id,
                    amount=welcome_credits,
                    transaction_type=CreditTransactionType.BONUS,
                    description=f"Welcome bonus credits - {self.welcome_bonus_credits} + {self.referral_bonus_credits if referral_code else 0} referral",
                    reference_id=onboarding_id,
                    status="completed",
                    created_at=datetime.utcnow()
                )
                db.add(welcome_transaction)
                
                self.logger.info("💰 Credit account created",
                               onboarding_id=onboarding_id,
                               user_id=user_id,
                               welcome_credits=welcome_credits)
                
                return {
                    "success": True,
                    "action": "created",
                    "credits_granted": welcome_credits,
                    "account_id": str(credit_account.id) if hasattr(credit_account, 'id') else None
                }
                
            else:
                # Update existing account with welcome bonus if not already given
                if credit_account.total_earned_credits == 0:
                    credit_account.available_credits += welcome_credits
                    credit_account.total_earned_credits += welcome_credits
                    credit_account.last_updated = datetime.utcnow()
                    
                    # Create transaction
                    welcome_transaction = CreditTransaction(
                        user_id=user_id,
                        amount=welcome_credits,
                        transaction_type=CreditTransactionType.BONUS,
                        description=f"Welcome bonus credits - onboarding completion",
                        reference_id=onboarding_id,
                        status="completed",
                        created_at=datetime.utcnow()
                    )
                    db.add(welcome_transaction)
                    
                    self.logger.info("💰 Credit account updated with welcome bonus",
                                   onboarding_id=onboarding_id,
                                   user_id=user_id,
                                   welcome_credits=welcome_credits)
                    
                    return {
                        "success": True,
                        "action": "updated",
                        "credits_granted": welcome_credits,
                        "total_available": credit_account.available_credits
                    }
                else:
                    return {
                        "success": True,
                        "action": "already_initialized",
                        "credits_granted": 0,
                        "total_available": credit_account.available_credits
                    }
                    
        except Exception as e:
            self.logger.error("Credit account initialization failed",
                            onboarding_id=onboarding_id,
                            user_id=user_id,
                            error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _provision_free_strategies(
        self,
        user_id: str,
        onboarding_id: str
    ) -> Dict[str, Any]:
        """Provision 3 free AI strategies for new user."""
        
        try:
            provisioned_strategies = []
            failed_strategies = []
            
            for strategy in self.free_strategies:
                try:
                    # Use strategy marketplace service to grant access
                    purchase_result = await strategy_marketplace_service.purchase_strategy_access(
                        user_id=user_id,
                        strategy_id=strategy["strategy_id"],
                        subscription_type="permanent"  # Free strategies are permanent
                    )
                    
                    if purchase_result.get("success"):
                        provisioned_strategies.append({
                            "strategy_id": strategy["strategy_id"],
                            "name": strategy["name"],
                            "description": strategy["description"],
                            "category": strategy["category"],
                            "cost": 0,
                            "provisioned_at": datetime.utcnow().isoformat()
                        })
                        
                        self.logger.info("🎯 Free strategy provisioned",
                                       onboarding_id=onboarding_id,
                                       user_id=user_id,
                                       strategy=strategy["name"])
                    else:
                        failed_strategies.append({
                            "strategy_id": strategy["strategy_id"],
                            "error": purchase_result.get("error", "Unknown error")
                        })
                        
                except Exception as strategy_error:
                    failed_strategies.append({
                        "strategy_id": strategy["strategy_id"],
                        "error": str(strategy_error)
                    })
                    
                    self.logger.warning("Free strategy provisioning failed",
                                      onboarding_id=onboarding_id,
                                      user_id=user_id,
                                      strategy=strategy["strategy_id"],
                                      error=str(strategy_error))
            
            if provisioned_strategies:
                self.logger.info("✅ Free strategies provisioned successfully",
                               onboarding_id=onboarding_id,
                               user_id=user_id,
                               count=len(provisioned_strategies))
                
                return {
                    "success": True,
                    "provisioned_strategies": provisioned_strategies,
                    "failed_strategies": failed_strategies,
                    "total_provisioned": len(provisioned_strategies)
                }
            else:
                return {
                    "success": False,
                    "error": "No strategies could be provisioned",
                    "failed_strategies": failed_strategies
                }
                
        except Exception as e:
            self.logger.error("Free strategies provisioning failed",
                            onboarding_id=onboarding_id,
                            user_id=user_id,
                            error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _setup_strategy_portfolio(
        self,
        user_id: str, 
        onboarding_id: str
    ) -> Dict[str, Any]:
        """Setup strategy portfolio tracking for the user."""
        
        try:
            redis = await get_redis_client()
            if not redis:
                return {"success": False, "error": "Redis not available"}
            
            # Initialize user strategy portfolio metadata
            portfolio_metadata = {
                "user_id": user_id,
                "onboarded_at": datetime.utcnow().isoformat(),
                "free_strategies_count": len(self.free_strategies),
                "tier": "basic",
                "last_opportunity_scan": None,
                "total_opportunities_discovered": 0
            }
            
            # Store portfolio metadata
            portfolio_key = f"user_portfolio_metadata:{user_id}"
            await redis.hset(portfolio_key, mapping={
                k: str(v) if v is not None else "" for k, v in portfolio_metadata.items()
            })
            await redis.expire(portfolio_key, 86400 * 365)  # 1 year expiry
            
            # Initialize opportunity discovery cache
            opportunity_cache_key = f"user_opportunities_cache:{user_id}"
            await redis.set(opportunity_cache_key, "{}", ex=3600)  # 1 hour initial cache
            
            self.logger.info("📊 Strategy portfolio setup completed",
                           onboarding_id=onboarding_id,
                           user_id=user_id)
            
            return {
                "success": True,
                "portfolio_metadata": portfolio_metadata,
                "cache_initialized": True
            }
            
        except Exception as e:
            self.logger.error("Strategy portfolio setup failed",
                            onboarding_id=onboarding_id,
                            user_id=user_id,
                            error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _apply_premium_welcome_package(
        self,
        user_id: str,
        db: AsyncSession,
        onboarding_id: str
    ) -> Dict[str, Any]:
        """Apply premium welcome package bonuses."""
        
        try:
            premium_bonus_credits = 200  # Premium users get extra credits
            premium_strategies = ["ai_spot_breakout_strategy"]  # One premium strategy free
            
            # Add premium credits
            credit_stmt = select(CreditAccount).where(CreditAccount.user_id == user_id)
            credit_result = await db.execute(credit_stmt)
            credit_account = credit_result.scalar_one_or_none()
            
            if credit_account:
                credit_account.available_credits += premium_bonus_credits
                credit_account.total_earned_credits += premium_bonus_credits
                
                # Create premium bonus transaction
                premium_transaction = CreditTransaction(
                    user_id=user_id,
                    amount=premium_bonus_credits,
                    transaction_type=CreditTransactionType.BONUS,
                    description="Premium welcome package bonus",
                    reference_id=onboarding_id,
                    status="completed"
                )
                db.add(premium_transaction)
            
            # Provision premium strategy
            premium_strategy_results = []
            for strategy_id in premium_strategies:
                purchase_result = await strategy_marketplace_service.purchase_strategy_access(
                    user_id=user_id,
                    strategy_id=strategy_id,
                    subscription_type="monthly"  # 1 month free premium strategy
                )
                
                if purchase_result.get("success"):
                    premium_strategy_results.append(strategy_id)
            
            return {
                "success": True,
                "bonus_credits": premium_bonus_credits,
                "premium_strategies": premium_strategy_results,
                "package_type": "premium"
            }
            
        except Exception as e:
            self.logger.error("Premium package application failed",
                            onboarding_id=onboarding_id,
                            error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _process_referral_bonuses(
        self,
        user_id: str,
        referral_code: str,
        db: AsyncSession,
        onboarding_id: str
    ) -> Dict[str, Any]:
        """Process referral bonuses for both referrer and referee."""
        
        try:
            # Decode referral code to get referrer user ID
            # Simplified: assume referral code is base64 encoded user ID
            import base64
            
            try:
                referrer_id = base64.b64decode(referral_code.encode()).decode()
            except:
                return {"success": False, "error": "Invalid referral code"}
            
            # Verify referrer exists
            referrer_stmt = select(User).where(User.id == referrer_id)
            referrer_result = await db.execute(referrer_stmt)
            referrer = referrer_result.scalar_one_or_none()
            
            if not referrer:
                return {"success": False, "error": "Referrer not found"}
            
            # Give bonus to referrer
            referrer_credit_stmt = select(CreditAccount).where(CreditAccount.user_id == referrer_id)
            referrer_credit_result = await db.execute(referrer_credit_stmt)
            referrer_credit_account = referrer_credit_result.scalar_one_or_none()
            
            referrer_bonus = 75  # Referrer gets 75 credits
            
            if referrer_credit_account:
                referrer_credit_account.available_credits += referrer_bonus
                referrer_credit_account.total_earned_credits += referrer_bonus
                
                # Create referrer bonus transaction
                referrer_transaction = CreditTransaction(
                    user_id=referrer_id,
                    amount=referrer_bonus,
                    transaction_type=CreditTransactionType.BONUS,
                    description=f"Referral bonus - new user {user_id[:8]}...",
                    reference_id=f"referral_{onboarding_id}",
                    status="completed"
                )
                db.add(referrer_transaction)
            
            # Referee (new user) already got their referral bonus in _initialize_credit_account
            
            self.logger.info("🎁 Referral bonuses processed",
                           onboarding_id=onboarding_id,
                           referrer_id=referrer_id,
                           referee_id=user_id,
                           referrer_bonus=referrer_bonus)
            
            return {
                "success": True,
                "referrer_id": referrer_id,
                "referrer_bonus": referrer_bonus,
                "referee_bonus": self.referral_bonus_credits
            }
            
        except Exception as e:
            self.logger.error("Referral processing failed",
                            onboarding_id=onboarding_id,
                            error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _cache_onboarding_status(
        self,
        user_id: str,
        onboarding_results: Dict[str, Any]
    ):
        """Cache user onboarding status for quick access."""
        
        try:
            redis = await get_redis_client()
            if not redis:
                return
            
            onboarding_status = {
                "onboarded": True,
                "onboarded_at": datetime.utcnow().isoformat(),
                "free_strategies_count": len(self.free_strategies),
                "welcome_bonus_applied": onboarding_results.get("credit_account", {}).get("success", False),
                "results": onboarding_results
            }
            
            # Cache onboarding status
            status_key = f"user_onboarding_status:{user_id}"
            await redis.set(status_key, json.dumps(onboarding_status), ex=86400 * 30)  # 30 days
            
        except Exception as e:
            self.logger.debug("Onboarding status caching failed", error=str(e))
    
    async def check_user_onboarding_status(self, user_id: str) -> Dict[str, Any]:
        """Check if user has been onboarded and get status."""
        
        try:
            redis = await get_redis_client()
            if redis:
                # Check cache first
                status_key = f"user_onboarding_status:{user_id}"
                cached_status = await redis.get(status_key)
                
                if cached_status:
                    import json
                    return json.loads(cached_status)
            
            # Check database
            async for db in get_database():
                # Check if user has credit account with earned credits (sign of onboarding)
                credit_stmt = select(CreditAccount).where(CreditAccount.user_id == user_id)
                credit_result = await db.execute(credit_stmt)
                credit_account = credit_result.scalar_one_or_none()
                
                if credit_account and credit_account.total_earned_credits > 0:
                    # Check if user has free strategies
                    portfolio_result = await strategy_marketplace_service.get_user_strategy_portfolio(user_id)
                    
                    return {
                        "onboarded": True,
                        "has_credit_account": True,
                        "total_earned_credits": float(credit_account.total_earned_credits),
                        "active_strategies": portfolio_result.get("total_strategies", 0) if portfolio_result.get("success") else 0,
                        "needs_onboarding": False
                    }
                else:
                    return {
                        "onboarded": False,
                        "has_credit_account": credit_account is not None,
                        "needs_onboarding": True
                    }
                    
        except Exception as e:
            self.logger.error("Onboarding status check failed", error=str(e))
            return {
                "onboarded": False,
                "error": str(e),
                "needs_onboarding": True
            }
    
    async def trigger_onboarding_if_needed(self, user_id: str) -> Dict[str, Any]:
        """Check and trigger onboarding if user needs it."""
        
        status = await self.check_user_onboarding_status(user_id)
        
        if status.get("needs_onboarding", True):
            self.logger.info("Triggering automatic onboarding", user_id=user_id)
            return await self.onboard_new_user(user_id)
        else:
            return {
                "success": True,
                "message": "User already onboarded",
                "status": status
            }


# Global service instance
user_onboarding_service = UserOnboardingService()


async def get_user_onboarding_service() -> UserOnboardingService:
    """Dependency injection for FastAPI."""
    return user_onboarding_service