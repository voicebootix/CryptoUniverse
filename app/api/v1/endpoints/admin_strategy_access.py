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
from app.core.redis import get_redis_client
from app.services.strategy_marketplace_service import strategy_marketplace_service

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

        # Step 3: Get all available strategies from marketplace
        try:
            marketplace_result = await strategy_marketplace_service.get_marketplace_strategies(
                user_id=target_user_id
            )

            if not marketplace_result.get("success"):
                raise Exception(f"Failed to get marketplace strategies: {marketplace_result.get('error')}")

            all_strategies = marketplace_result.get("strategies", [])

        except Exception as e:
            logger.error(
                "❌ Failed to fetch marketplace strategies",
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

        # Step 5: Grant strategies via Redis (enterprise batch operation)
        redis_key = f"user_strategies:{target_user_id}"
        strategies_granted = []

        try:
            # Use Redis pipeline for atomic batch operation
            async with redis.pipeline(transaction=True) as pipe:
                # Clear existing strategies (admin gets fresh full access)
                pipe.delete(redis_key)

                # Add all strategies
                for strategy_id in strategies_to_grant:
                    pipe.sadd(redis_key, strategy_id)

                # Set expiry (1 year for admin access)
                pipe.expire(redis_key, 86400 * 365)

                # Execute pipeline
                results = await pipe.execute()

            # Verify the operation
            final_strategies = await redis.smembers(redis_key)
            strategies_granted = [
                s.decode() if isinstance(s, bytes) else s
                for s in final_strategies
            ]

            logger.info(
                "✅ Admin strategy grant completed",
                operation_id=operation_id,
                strategies_granted_count=len(strategies_granted),
                verification_count=len(final_strategies)
            )

        except Exception as e:
            logger.error(
                "❌ Redis batch operation failed",
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