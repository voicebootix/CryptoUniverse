"""
Admin Strategy Access Management - Enterprise CTO Solution

Provides admin users with full access to all marketplace strategies.
This is an enterprise privilege allowing admins to test and demonstrate
all platform capabilities without credit restrictions.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import structlog

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.trading import TradingStrategy
from app.core.redis import get_redis_client
from app.services.strategy_marketplace_service import strategy_marketplace_service
from app.services.unified_strategy_service import UnifiedStrategyService
from app.models.strategy_access import StrategyType, StrategyAccessType

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin-strategy-access", tags=["Admin Strategy Management"])

class AdminStrategyGrantRequest(BaseModel):
    target_user_id: Optional[str] = Field(None, description="User ID to grant access to (if None, grants to current admin)")
    strategy_type: str = Field("all", description="Type of access: 'all', 'ai_only', 'community_only'")
    grant_reason: str = Field("admin_privilege", description="Reason for granting access")

class AdminStrategyGrantResponse(BaseModel):
    success: bool
    user_id: str
    strategies_granted: List[str]
    total_strategies: int
    grant_type: str
    execution_time_seconds: float
    message: str

@router.post("/grant-full-access", response_model=AdminStrategyGrantResponse)
async def grant_admin_full_strategy_access(
    request: AdminStrategyGrantRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """
    Grant admin users full access to all marketplace strategies.

    This is an enterprise admin privilege that bypasses normal credit restrictions
    and provides access to all platform strategies for testing and demonstration.
    """
    start_time = datetime.utcnow()
    operation_id = str(uuid.uuid4())[:8]

    # Determine target user (self or specified user)
    target_user_id = request.target_user_id or str(current_user.id)

    logger.info(
        "🔐 ADMIN STRATEGY GRANT: Initiating full strategy access",
        operation_id=operation_id,
        admin_user_id=str(current_user.id),
        target_user_id=target_user_id,
        strategy_type=request.strategy_type,
        reason=request.grant_reason
    )

    try:
        # Step 1: Validate target user (if different from current admin)
        if target_user_id != str(current_user.id):
            target_user = await db.execute(
                select(User).where(User.id == target_user_id)
            )
            target_user = target_user.scalar_one_or_none()

            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target user {target_user_id} not found"
                )

        # Step 2: Get Redis connection with timeout
        try:
            redis = await asyncio.wait_for(get_redis_client(), timeout=3.0)
            if not redis:
                raise Exception("Redis connection failed")
            await redis.ping()
        except Exception as e:
            logger.error(
                "❌ Redis connection failed during admin grant",
                operation_id=operation_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Redis service unavailable: {str(e)}"
            )

        # Step 3: Get all available strategies efficiently (admin bypass)
        try:
            # Admin fast path - get strategies directly from catalog without expensive operations
            all_strategies = []

            # Get AI strategies from catalog (fast, no performance calculations)
            ai_catalog = strategy_marketplace_service.ai_strategy_catalog
            for strategy_func, config in ai_catalog.items():
                all_strategies.append({
                    "strategy_id": f"ai_{strategy_func}",
                    "name": config["name"],
                    "category": config["category"],
                    "monthly_cost": config.get("credit_cost_monthly", 25)
                })

            # Get community strategies from database (fast query)
            community_strategies_query = select(
                TradingStrategy.id,
                TradingStrategy.name,
                TradingStrategy.strategy_type
            ).where(
                TradingStrategy.is_active == True
            ).limit(50)  # Reasonable limit for admin

            community_result = await db.execute(community_strategies_query)
            community_strategies = community_result.fetchall()

            for strategy in community_strategies:
                all_strategies.append({
                    "strategy_id": str(strategy.id),
                    "name": strategy.name,
                    "category": str(strategy.strategy_type) if strategy.strategy_type else "community",
                    "monthly_cost": 0  # Community strategies are typically free
                })

            logger.info(
                "📊 Fast admin strategy list generated successfully",
                operation_id=operation_id,
                ai_strategies=len(ai_catalog),
                community_strategies=len(community_strategies),
                total_strategies=len(all_strategies)
            )

        except Exception as e:
            logger.error(
                "❌ Failed to fetch strategies efficiently",
                operation_id=operation_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not fetch strategies: {str(e)}"
            )

        # Step 4: Filter strategies based on request type
        strategies_to_grant = []

        if request.strategy_type == "all":
            strategies_to_grant = [s["strategy_id"] for s in all_strategies]
        elif request.strategy_type == "ai_only":
            strategies_to_grant = [s["strategy_id"] for s in all_strategies if s["strategy_id"].startswith("ai_")]
        elif request.strategy_type == "community_only":
            strategies_to_grant = [s["strategy_id"] for s in all_strategies if not s["strategy_id"].startswith("ai_")]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy_type: {request.strategy_type}"
            )

        logger.info(
            "📊 Strategy grant plan prepared",
            operation_id=operation_id,
            total_available=len(all_strategies),
            strategies_to_grant=len(strategies_to_grant),
            strategy_type=request.strategy_type
        )

        # Step 5: Grant strategies using the proven working service method
        strategies_granted = []

        try:
            logger.info(
                "🔄 Using working marketplace service to grant strategies",
                operation_id=operation_id,
                strategies_to_grant=len(strategies_to_grant)
            )

            # Use the unified strategy service for admin grants (no credit consumption)
            unified_service = UnifiedStrategyService()

            for strategy_id in strategies_to_grant:
                try:
                    # Use UnifiedStrategyService.grant_strategy_access with ADMIN_GRANT
                    strategy_type = StrategyType.AI_STRATEGY if strategy_id.startswith("ai_") else StrategyType.COMMUNITY_STRATEGY

                    await unified_service.grant_strategy_access(
                        user_id=target_user_id,
                        strategy_id=strategy_id,
                        strategy_type=strategy_type,
                        access_type=StrategyAccessType.ADMIN_GRANT,
                        subscription_type="admin_grant",
                        credits_paid=0,  # No credits consumed for admin grants
                        expires_at=None,  # Permanent access
                        metadata={
                            "granted_by_admin": current_user.email,
                            "grant_reason": "admin_privilege",
                            "operation_id": operation_id
                        }
                    )

                    # grant_strategy_access returns the access object, not a dict with "success"
                    strategies_granted.append(strategy_id)
                    logger.debug(
                        "✅ Strategy granted successfully via UnifiedStrategyService",
                        strategy_id=strategy_id,
                        user_id=target_user_id,
                        access_type="ADMIN_GRANT"
                    )

                except Exception as e:
                    logger.warning(
                        "Exception granting strategy",
                        operation_id=operation_id,
                        strategy_id=strategy_id,
                        error=str(e)
                    )

            logger.info(
                "✅ Admin strategy grant completed via UnifiedStrategyService (no credits consumed)",
                operation_id=operation_id,
                strategies_granted_count=len(strategies_granted),
                total_attempted=len(strategies_to_grant)
            )

        except Exception as e:
            logger.error(
                "❌ Strategy grant via service failed",
                operation_id=operation_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to grant strategies: {str(e)}"
            )

        # Step 6: Log the admin action for audit
        background_tasks.add_task(
            log_admin_strategy_grant,
            operation_id=operation_id,
            admin_user_id=str(current_user.id),
            target_user_id=target_user_id,
            strategies_granted=strategies_granted,
            grant_type=request.strategy_type,
            reason=request.grant_reason
        )

        # Step 7: Calculate execution time and prepare response
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        success_message = f"Admin granted {len(strategies_granted)} strategies ({request.strategy_type})"

        logger.info(
            "🎉 ADMIN STRATEGY GRANT COMPLETED",
            operation_id=operation_id,
            admin_user=current_user.email,
            target_user_id=target_user_id,
            execution_time_seconds=execution_time,
            strategies_count=len(strategies_granted)
        )

        return AdminStrategyGrantResponse(
            success=True,
            user_id=target_user_id,
            strategies_granted=strategies_granted,
            total_strategies=len(strategies_granted),
            grant_type=request.strategy_type,
            execution_time_seconds=execution_time,
            message=success_message
        )

    except HTTPException:
        raise
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        logger.error(
            "💥 Admin strategy grant failed",
            operation_id=operation_id,
            error=str(e),
            execution_time_seconds=execution_time,
            exc_info=True
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strategy grant failed: {str(e)}"
        )

@router.get("/admin-portfolio-status")
async def get_admin_portfolio_status(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Get current admin user's strategy portfolio status."""

    try:
        # Get portfolio via marketplace service
        portfolio_result = await strategy_marketplace_service.get_user_strategy_portfolio(
            str(current_user.id)
        )

        # Get total available strategies for comparison
        marketplace_result = await strategy_marketplace_service.get_marketplace_strategies(
            user_id=str(current_user.id)
        )
        total_available = len(marketplace_result.get("strategies", [])) if marketplace_result.get("success") else 0

        current_strategies = len(portfolio_result.get("active_strategies", []))

        return {
            "success": True,
            "user_id": str(current_user.id),
            "user_email": current_user.email,
            "current_strategies": current_strategies,
            "total_available_strategies": total_available,
            "has_full_access": current_strategies == total_available,
            "portfolio_status": "healthy" if portfolio_result.get("success") else "degraded",
            "portfolio_error": portfolio_result.get("error") if not portfolio_result.get("success") else None
        }

    except Exception as e:
        logger.error("Failed to get admin portfolio status", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "user_id": str(current_user.id)
        }

@router.delete("/revoke-strategy-access")
async def revoke_admin_strategy_access(
    target_user_id: Optional[str] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Revoke all strategy access for a user (admin only)."""

    target_id = target_user_id or str(current_user.id)

    try:
        redis = await get_redis_client()
        if not redis:
            raise HTTPException(status_code=503, detail="Redis unavailable")

        redis_key = f"user_strategies:{target_id}"
        await redis.delete(redis_key)

        logger.info(
            "🗑️ Strategy access revoked",
            admin_user_id=str(current_user.id),
            target_user_id=target_id
        )

        return {
            "success": True,
            "message": f"Strategy access revoked for user {target_id}",
            "revoked_by": str(current_user.id)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke access: {str(e)}"
        )

async def log_admin_strategy_grant(
    operation_id: str,
    admin_user_id: str,
    target_user_id: str,
    strategies_granted: List[str],
    grant_type: str,
    reason: str
):
    """Log admin strategy grant for compliance and audit."""

    try:
        logger.info(
            "📝 AUDIT LOG: Admin strategy grant executed",
            operation_id=operation_id,
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            strategies_count=len(strategies_granted),
            grant_type=grant_type,
            reason=reason,
            timestamp=datetime.utcnow().isoformat(),
            audit_category="admin_privilege_grant"
        )
    except Exception as e:
        logger.error("Failed to log admin strategy grant", error=str(e))