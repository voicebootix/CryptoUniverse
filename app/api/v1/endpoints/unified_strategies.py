#!/usr/bin/env python3
"""
Enterprise Unified Strategy API Endpoints
Single source of truth for all strategy access with role-based permissions
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_database, AsyncSessionLocal
from app.core.async_session_manager import with_managed_db_session
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User, UserRole
from app.models.strategy_access import StrategyAccessType, StrategyType
from app.services.unified_strategy_service import unified_strategy_service, UnifiedStrategyPortfolio
import structlog

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/unified-strategies", tags=["Enterprise Strategy Management"])


class StrategyAccessGrantRequest(BaseModel):
    """Request model for granting strategy access"""
    strategy_id: str = Field(..., description="Strategy ID to grant access to")
    strategy_type: StrategyType = Field(..., description="Type of strategy")
    access_type: StrategyAccessType = Field(default=StrategyAccessType.PURCHASED, description="Access type")
    subscription_type: str = Field(default="monthly", description="Subscription model")
    credits_paid: int = Field(default=0, description="Credits paid for access")
    expires_at: Optional[datetime] = Field(None, description="Access expiration (None for permanent)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class StrategyAccessResponse(BaseModel):
    """Response model for strategy access operations"""
    success: bool
    message: str
    access_id: Optional[str] = None
    user_id: str
    strategy_id: str
    access_type: str
    expires_at: Optional[datetime] = None


class BulkAccessGrantRequest(BaseModel):
    """Request model for bulk access granting"""
    target_user_id: Optional[str] = Field(None, description="User ID to grant access to (None for current user)")
    access_type: StrategyAccessType = Field(default=StrategyAccessType.ADMIN_GRANT, description="Access type")
    strategy_filter: str = Field(default="all", description="Which strategies to grant: all, ai_only, community_only")
    grant_reason: str = Field("bulk_admin_grant", description="Reason for granting access")


class BulkAccessResponse(BaseModel):
    """Response model for bulk access operations"""
    success: bool
    message: str
    user_id: str
    strategies_granted: List[str]
    total_granted: int
    execution_time_seconds: float
    grant_type: str


@router.get("/portfolio", response_model=Dict[str, Any])
@with_managed_db_session
async def get_unified_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """
    Get unified strategy portfolio for current user.

    This endpoint replaces the fragmented Redis-based portfolio system
    with enterprise-grade database-first architecture.

    Features:
    - Role-based access (Admin sees all strategies, users see owned)
    - Database-first with Redis fallback
    - Comprehensive audit logging
    - Sub-second response times
    - Graceful degradation
    """

    try:
        portfolio = await unified_strategy_service.get_user_strategy_portfolio(
            user_id=str(current_user.id),
            user_role=current_user.role,
            db=db
        )

        return portfolio.to_dict()

    except Exception as e:
        logger.error(
            "Unified portfolio request failed",
            user_id=str(current_user.id),
            user_role=current_user.role.value,
            error=str(e),
            exc_info=True
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve strategy portfolio: {str(e)}"
        )


@router.get("/portfolio/admin-status")
async def get_admin_portfolio_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get detailed admin portfolio status and diagnostics"""

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        # Get portfolio data
        portfolio = await unified_strategy_service.get_user_strategy_portfolio(
            user_id=str(current_user.id),
            user_role=current_user.role,
            db=db
        )

        # Additional admin diagnostics
        from sqlalchemy import select, func
        from app.models.strategy_access import UserStrategyAccess

        # Get access record counts
        access_count = await db.execute(
            select(func.count(UserStrategyAccess.id)).where(
                UserStrategyAccess.user_id == current_user.id
            )
        )
        total_access_records = access_count.scalar()

        return {
            "success": True,
            "user_id": str(current_user.id),
            "user_email": current_user.email,
            "user_role": current_user.role.value,
            "portfolio_status": "healthy",
            "strategies_available": len(portfolio.strategies),
            "active_strategies": len([s for s in portfolio.strategies if s.get("is_active", True)]),
            "access_records_count": total_access_records,
            "data_source": portfolio.metadata.get("data_sources", []),
            "execution_time": portfolio.metadata.get("execution_time_seconds", 0),
            "api_version": "unified_enterprise_v2",
            "last_updated": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("Admin status check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/access/grant", response_model=StrategyAccessResponse)
async def grant_strategy_access(
    request: StrategyAccessGrantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """
    Grant strategy access to current user.

    For regular users purchasing strategies.
    Admins can use bulk endpoints for broader access.
    """

    try:
        access = await unified_strategy_service.grant_strategy_access(
            user_id=str(current_user.id),
            strategy_id=request.strategy_id,
            strategy_type=request.strategy_type,
            access_type=request.access_type,
            subscription_type=request.subscription_type,
            credits_paid=request.credits_paid,
            expires_at=request.expires_at,
            metadata=request.metadata
        )

        return StrategyAccessResponse(
            success=True,
            message="Strategy access granted successfully",
            access_id=str(access.id),
            user_id=str(current_user.id),
            strategy_id=request.strategy_id,
            access_type=request.access_type.value,
            expires_at=request.expires_at
        )

    except Exception as e:
        logger.error("Strategy access grant failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant strategy access: {str(e)}"
        )


@router.post("/access/bulk-grant", response_model=BulkAccessResponse)
async def bulk_grant_strategy_access(
    request: BulkAccessGrantRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Bulk grant strategy access (Admin only).

    Grants access to multiple strategies based on filter criteria.
    Perfect for admin users who need full platform access.
    """

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for bulk operations"
        )

    operation_start = datetime.utcnow()
    target_user_id = request.target_user_id or str(current_user.id)

    try:
        logger.info(
            "[emoji] BULK STRATEGY GRANT INITIATED",
            admin_user_id=str(current_user.id),
            target_user_id=target_user_id,
            strategy_filter=request.strategy_filter,
            reason=request.grant_reason
        )

        strategies_granted = []

        if request.strategy_filter in ["all", "ai_only"]:
            # Grant all AI strategies
            ai_access_records = await unified_strategy_service.bulk_grant_admin_access(
                target_user_id
            )
            strategies_granted.extend([access.strategy_id for access in ai_access_records])

        if request.strategy_filter in ["all", "community_only"]:
            # Grant community strategies (if any exist)
            # This would be implemented based on community strategy requirements
            pass

        execution_time = (datetime.utcnow() - operation_start).total_seconds()

        # Log operation for audit
        background_tasks.add_task(
            log_bulk_grant_operation,
            admin_user_id=str(current_user.id),
            target_user_id=target_user_id,
            strategies_granted=strategies_granted,
            grant_reason=request.grant_reason,
            execution_time=execution_time
        )

        logger.info(
            "[OK] BULK STRATEGY GRANT COMPLETED",
            admin_user_id=str(current_user.id),
            target_user_id=target_user_id,
            strategies_granted=len(strategies_granted),
            execution_time_seconds=execution_time
        )

        return BulkAccessResponse(
            success=True,
            message=f"Bulk granted access to {len(strategies_granted)} strategies",
            user_id=target_user_id,
            strategies_granted=strategies_granted,
            total_granted=len(strategies_granted),
            execution_time_seconds=execution_time,
            grant_type=request.strategy_filter
        )

    except Exception as e:
        execution_time = (datetime.utcnow() - operation_start).total_seconds()

        logger.error(
            "[X] BULK STRATEGY GRANT FAILED",
            admin_user_id=str(current_user.id),
            target_user_id=target_user_id,
            error=str(e),
            execution_time_seconds=execution_time,
            exc_info=True
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk grant failed: {str(e)}"
        )


@router.delete("/access/revoke")
async def revoke_strategy_access(
    strategy_id: str = Query(..., description="Strategy ID to revoke access from"),
    current_user: User = Depends(get_current_user)
):
    """Revoke strategy access for current user"""

    try:
        success = await unified_strategy_service.revoke_strategy_access(
            user_id=str(current_user.id),
            strategy_id=strategy_id
        )

        if success:
            return {
                "success": True,
                "message": "Strategy access revoked successfully",
                "user_id": str(current_user.id),
                "strategy_id": strategy_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy access not found or already revoked"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Strategy access revocation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke strategy access: {str(e)}"
        )


@router.get("/health")
async def unified_strategy_health(
    db: AsyncSession = Depends(get_database)
):
    """Health check for unified strategy system"""

    try:
        # Test database connectivity
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))

        # Test service availability
        ai_catalog_size = len(unified_strategy_service._ai_strategy_catalog)

        return {
            "status": "healthy",
            "service": "unified_strategy_service",
            "version": "2.0.0",
            "database": "connected",
            "ai_strategies_available": ai_catalog_size,
            "timestamp": datetime.utcnow().isoformat(),
            "features": [
                "role_based_access",
                "database_first",
                "redis_fallback",
                "audit_logging",
                "enterprise_grade"
            ]
        }

    except Exception as e:
        logger.error("Unified strategy health check failed", error=str(e))
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def log_bulk_grant_operation(
    admin_user_id: str,
    target_user_id: str,
    strategies_granted: List[str],
    grant_reason: str,
    execution_time: float
):
    """Background task for audit logging"""

    try:
        logger.info(
            "[NOTE] AUDIT: Bulk strategy grant executed",
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            strategies_count=len(strategies_granted),
            grant_reason=grant_reason,
            execution_time_seconds=execution_time,
            timestamp=datetime.utcnow().isoformat(),
            audit_category="bulk_admin_grant",
            compliance_logged=True
        )

        # Additional audit logging could be added here:
        # - Write to audit database table
        # - Send to external audit system
        # - Generate compliance reports

    except Exception as e:
        logger.error("Audit logging failed", error=str(e))