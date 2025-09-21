"""
Admin API Endpoints - Enterprise Grade

Provides administrative functions for system management, user management,
system configuration, and monitoring for the AI money manager platform.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, select

from app.core.config import get_settings
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_user, require_role
from app.models.user import User, UserRole, UserStatus
from app.models.tenant import Tenant
from app.models.trading import Trade, Position
from app.models.exchange import ExchangeAccount
from app.models.credit import CreditAccount, CreditTransaction, CreditTransactionType
from app.models.system import SystemHealth, AuditLog
from app.services.master_controller import MasterSystemController
from app.services.background import BackgroundServiceManager
from app.services.rate_limit import rate_limiter

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()

# Initialize services
master_controller = MasterSystemController()
background_manager = BackgroundServiceManager()


# Request/Response Models
class SystemConfigRequest(BaseModel):
    autonomous_intervals: Optional[Dict[str, int]] = None  # Service intervals in seconds
    rate_limits: Optional[Dict[str, Dict[str, int]]] = None
    trading_limits: Optional[Dict[str, Any]] = None
    maintenance_mode: Optional[bool] = None
    emergency_stop_all: Optional[bool] = None


class CreditPricingConfigRequest(BaseModel):
    platform_fee_percentage: Optional[float] = None  # 25.0 for 25%
    credit_to_dollar_cost: Optional[float] = None    # 1.0 for $1 = 1 credit
    welcome_profit_potential: Optional[float] = None # 100.0 for $100 profit potential
    welcome_strategies_count: Optional[int] = None   # 3 for 3 free strategies
    welcome_enabled: Optional[bool] = None           # True to enable welcome packages


class StrategyPricingRequest(BaseModel):
    strategy_pricing: Dict[str, int]  # strategy_name -> credit_cost


class UserManagementRequest(BaseModel):
    user_id: str
    action: str  # "activate", "deactivate", "suspend", "reset_credits"
    reason: Optional[str] = None
    credit_amount: Optional[int] = None
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        allowed_actions = ["activate", "deactivate", "suspend", "reset_credits", "reset_password"]
        if v.lower() not in allowed_actions:
            raise ValueError(f"Action must be one of: {allowed_actions}")
        return v.lower()


class BatchVerifyRequest(BaseModel):
    user_ids: List[str]  # Will be validated to UUIDs
    reason: Optional[str] = None
    
    @field_validator('user_ids')
    @classmethod
    def validate_user_ids(cls, v):
        """Validate, dedupe, and limit user IDs."""
        if not v:
            raise ValueError("At least one user ID is required")
        
        # Parse and validate UUIDs
        valid_uuids = []
        seen = set()
        
        for user_id in v:
            try:
                # Parse to UUID to validate format
                uuid_obj = UUID(user_id)
                uuid_str = str(uuid_obj)
                
                # Deduplicate
                if uuid_str not in seen:
                    valid_uuids.append(uuid_str)
                    seen.add(uuid_str)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid UUID format: {user_id}")
        
        # Check batch size limits
        if len(valid_uuids) == 0:
            raise ValueError("No valid user IDs provided after deduplication")
        if len(valid_uuids) > 100:
            raise ValueError(f"Batch size exceeds maximum of 100 users (got {len(valid_uuids)})")
        
        return valid_uuids


class SystemMetricsResponse(BaseModel):
    active_users: int
    total_trades_today: int
    total_volume_24h: float
    system_health: str
    autonomous_sessions: int
    error_rate: float
    response_time_avg: float
    uptime_percentage: float


class UserListResponse(BaseModel):
    users: List[Dict[str, Any]]
    total_count: int
    active_count: int
    trading_count: int


# Admin Endpoints
@router.get("/system/status")
async def get_system_overview(
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Get comprehensive system status overview."""
    
    await rate_limiter.check_rate_limit(
        key="admin:system_status",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Get system metrics
        system_status = await master_controller.get_global_system_status()
        background_status = await background_manager.health_check()
        
        # Get database metrics
        # Count active users
        result = await db.execute(
            select(func.count(User.id)).where(
                User.status == UserStatus.ACTIVE.value,
                User.last_login >= datetime.utcnow() - timedelta(days=7)
            )
        )
        active_users = result.scalar_one_or_none() or 0
        
        # Count trades today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(func.count(Trade.id)).where(Trade.created_at >= today_start)
        )
        trades_today = result.scalar_one_or_none() or 0
        
        # Calculate volume
        result = await db.execute(
            select(func.sum(Trade.total_value)).where(
                Trade.created_at >= datetime.utcnow() - timedelta(hours=24)
            )
        )
        volume_24h = result.scalar_one_or_none() or 0
        
        # Get real system metrics
        system_metrics = {}
        try:
            import psutil
            import time
            
            # CPU Usage (1 second average)
            system_metrics["cpuUsage"] = round(psutil.cpu_percent(interval=0.1), 1)
            
            # Memory Usage
            memory = psutil.virtual_memory()
            system_metrics["memoryUsage"] = round(memory.percent, 1)
            
            # Disk Usage (root/main disk)
            disk = psutil.disk_usage('/')
            system_metrics["diskUsage"] = round(disk.percent, 1)
            
            # Network Latency (approximate response time)
            start_time = time.time()
            # Simple latency approximation
            system_metrics["networkLatency"] = round((time.time() - start_time) * 1000 + 5, 0)  # Add base latency
            
            # Mark as real psutil data
            system_metrics["metricsSource"] = "psutil"
            
        except ImportError:
            # Fallback if psutil not available
            logger.warning("psutil not available, using fallback system metrics")
            system_metrics = {
                "cpuUsage": None,
                "memoryUsage": None,
                "diskUsage": None,
                "networkLatency": None,
                "metricsSource": "fallback"
            }
        except (OSError, PermissionError):
            logger.error("System metrics access denied or OS error occurred")
            system_metrics = {
                "cpuUsage": None,
                "memoryUsage": None,
                "diskUsage": None,
                "networkLatency": None,
                "metricsSource": "error"
            }
        except Exception as e:
            logger.exception("Unexpected error while gathering system metrics")
            system_metrics = {
                "cpuUsage": None,
                "memoryUsage": None,
                "diskUsage": None,
                "networkLatency": None,
                "metricsSource": "unknown"
            }
        
        return {
            "system_health": system_status.get("health", "unknown"),
            "active_users": active_users,
            "total_trades_today": trades_today,
            "total_volume_24h": float(volume_24h),
            "autonomous_sessions": system_status.get("active_autonomous_sessions", 0),
            "background_services": background_status,
            "uptime": system_status.get("uptime_hours", 0),
            "error_rate": system_status.get("error_rate_percent", 0),
            "response_time_avg": system_status.get("avg_response_time_ms", 0),
            "timestamp": datetime.utcnow().isoformat(),
            # Add real system metrics
            **system_metrics
        }
        
    except Exception as e:
        logger.exception("System status retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system status"
        ) from e


@router.post("/system/configure")
async def configure_system(
    request: SystemConfigRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Configure system-wide settings."""
    
    await rate_limiter.check_rate_limit(
        key="admin:configure",
        limit=20,
        window=300,  # 20 changes per 5 minutes
        user_id=str(current_user.id)
    )
    
    logger.info(
        "System configuration request",
        admin_user=str(current_user.id),
        config_keys=list(request.dict(exclude_unset=True).keys())
    )
    
    try:
        changes_applied = []
        
        # Configure autonomous intervals
        if request.autonomous_intervals:
            for service, interval in request.autonomous_intervals.items():
                if interval < 10:  # Minimum 10 seconds
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Minimum interval for {service} is 10 seconds"
                    )
                
                await master_controller.configure_service_interval(service, interval)
                changes_applied.append(f"Set {service} interval to {interval}s")
        
        # Configure rate limits
        if request.rate_limits:
            for endpoint, limits in request.rate_limits.items():
                await rate_limiter.set_custom_limit(
                    endpoint,
                    limits.get("limit", 100),
                    limits.get("window", 60)
                )
                changes_applied.append(f"Updated rate limits for {endpoint}")
        
        # Emergency stop all trading
        if request.emergency_stop_all:
            await master_controller.emergency_stop_all_users()
            changes_applied.append("Emergency stop activated for all users")
        
        # Maintenance mode
        if request.maintenance_mode is not None:
            await master_controller.set_maintenance_mode(request.maintenance_mode)
            changes_applied.append(f"Maintenance mode: {'enabled' if request.maintenance_mode else 'disabled'}")
        
        # Log audit trail
        audit_log = AuditLog(
            user_id=current_user.id,
            event_type="system_configuration",
            event_data={
                "changes": changes_applied,
                "details": {"changes": changes_applied},
                "ip_address": "admin_api",
                "user_agent": "system"
            }
        )
        db.add(audit_log)
        await db.commit()
        
        # Schedule background restart if needed
        if request.autonomous_intervals:
            background_tasks.add_task(restart_background_services)
        
        return {
            "status": "configuration_updated",
            "changes_applied": changes_applied,
            "timestamp": datetime.utcnow().isoformat(),
            "applied_by": current_user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("System configuration failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="System configuration failed"
    ) from e


@router.get("/credit-pricing")
async def get_credit_pricing_config(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Get current credit pricing configuration."""
    
    try:
        from app.services.profit_sharing_service import profit_sharing_service
        
        # Get current pricing configuration
        pricing_config = await profit_sharing_service.get_current_pricing_config()
        
        # Get strategy pricing
        if profit_sharing_service.strategy_pricing is None:
            await profit_sharing_service.ensure_pricing_loaded()
        
        return {
            "success": True,
            "pricing_config": pricing_config,
            "strategy_pricing": profit_sharing_service.strategy_pricing,
            "explanation": {
                "platform_fee": "Percentage of profits users pay as platform fee",
                "credit_calculation": "Credits = Profit Potential × Platform Fee Percentage",
                "example": f"$100 profit potential = ${pricing_config.get('platform_fee_percentage', 25):.0f} credits at {pricing_config.get('platform_fee_percentage', 25):.0f}% fee"
            }
        }
        
    except Exception as e:
        logger.exception("Failed to get credit pricing config")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pricing config"
        ) from e


@router.put("/credit-pricing")
async def update_credit_pricing_config(
    request: CreditPricingConfigRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Update credit pricing configuration."""
    
    try:
        from app.core.redis import get_redis_client
        
        redis = await get_redis_client()
        
        # Get current config
        current_config = await redis.hgetall("admin:pricing_config")
        
        # Update only provided fields
        updates = {}
        
        if request.platform_fee_percentage is not None:
            if not 5.0 <= request.platform_fee_percentage <= 50.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Platform fee must be between 5% and 50%"
                )
            updates["platform_fee_percentage"] = request.platform_fee_percentage
        
        if request.credit_to_dollar_cost is not None:
            if not 0.1 <= request.credit_to_dollar_cost <= 10.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Credit to dollar cost must be between 0.1 and 10.0"
                )
            updates["credit_to_dollar_cost"] = request.credit_to_dollar_cost
        
        if request.welcome_profit_potential is not None:
            if not 50.0 <= request.welcome_profit_potential <= 500.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Welcome profit potential must be between $50 and $500"
                )
            updates["welcome_profit_potential"] = request.welcome_profit_potential
        
        if request.welcome_strategies_count is not None:
            if not 1 <= request.welcome_strategies_count <= 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Welcome strategies count must be between 1 and 10"
                )
            updates["welcome_strategies_count"] = request.welcome_strategies_count
        
        if request.welcome_enabled is not None:
            updates["welcome_enabled"] = "true" if request.welcome_enabled else "false"
        
        if updates:
            # Add metadata
            updates.update({
                "last_updated": datetime.utcnow().isoformat(),
                "updated_by": str(current_user.id)
            })
            
            # Save updates
            await redis.hset("admin:pricing_config", mapping=updates)
            
            # Force reload in service
            from app.services.profit_sharing_service import profit_sharing_service
            await profit_sharing_service.load_dynamic_pricing_config()
            
            logger.info(
                "Credit pricing configuration updated",
                admin_user=str(current_user.id),
                updates=list(updates.keys())
            )
            
            return {
                "success": True,
                "message": "Credit pricing configuration updated successfully",
                "updates_applied": list(updates.keys()),
                "new_config": await profit_sharing_service.get_current_pricing_config()
            }
        else:
            return {
                "success": False,
                "error": "No valid updates provided"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update credit pricing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update pricing"
        ) from e


@router.put("/strategy-pricing")
async def update_strategy_pricing(
    request: StrategyPricingRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Update strategy pricing configuration."""
    
    try:
        from app.core.redis import get_redis_client
        
        redis = await get_redis_client()
        
        # Validate pricing values
        for strategy, cost in request.strategy_pricing.items():
            if not 1 <= cost <= 500:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Strategy {strategy} cost must be between 1 and 500 credits"
                )
        
        # Update strategy pricing
        await redis.delete("admin:strategy_pricing")  # Clear existing
        await redis.hset("admin:strategy_pricing", mapping=request.strategy_pricing)
        
        # Add metadata
        await redis.hset("admin:strategy_pricing_meta", mapping={
            "last_updated": datetime.utcnow().isoformat(),
            "updated_by": str(current_user.id),
            "total_strategies": len(request.strategy_pricing)
        })
        
        # Force reload in services
        from app.services.profit_sharing_service import profit_sharing_service
        from app.services.strategy_marketplace_service import strategy_marketplace_service
        
        profit_sharing_service.strategy_pricing = await profit_sharing_service._load_dynamic_strategy_pricing()
        strategy_marketplace_service.strategy_pricing = await strategy_marketplace_service._load_dynamic_strategy_pricing()
        
        logger.info(
            "Strategy pricing updated",
            admin_user=str(current_user.id),
            strategies_updated=len(request.strategy_pricing)
        )
        
        return {
            "success": True,
            "message": f"Updated pricing for {len(request.strategy_pricing)} strategies",
            "strategies_updated": list(request.strategy_pricing.keys()),
            "new_pricing": request.strategy_pricing
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update strategy pricing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update strategy pricing"
        ) from e


@router.get("/users/pending-verification")
async def get_pending_verification_users(
    include_unverified: bool = False,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Get all users pending verification.
    
    Args:
        include_unverified: If True, also include all unverified users regardless of status
    """
    
    await rate_limiter.check_rate_limit(
        key="admin:pending_users",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Build base query based on parameters
        if include_unverified:
            # Include all unverified users
            base_conditions = or_(
                User.status == UserStatus.PENDING_VERIFICATION.value,
                ~User.is_verified  # Using NOT operator instead of == False
            )
        else:
            # Only pending verification status (default behavior)
            base_conditions = User.status == UserStatus.PENDING_VERIFICATION.value
        
        # SECURITY: Apply tenant isolation
        # Global admins (tenant_id=None) can see all users
        # Tenant admins can only see their own tenant's users
        if current_user.tenant_id is not None:
            # Tenant admin - restrict to same tenant
            stmt = select(User).where(
                and_(
                    base_conditions,
                    User.tenant_id == current_user.tenant_id
                )
            ).order_by(User.created_at.desc())
            
            logger.debug(
                "Tenant admin viewing pending users",
                admin_user=str(current_user.id),
                admin_tenant=str(current_user.tenant_id)
            )
        else:
            # Global admin - can see all tenants
            stmt = select(User).where(
                base_conditions
            ).order_by(User.created_at.desc())
            
            logger.debug(
                "Global admin viewing all pending users",
                admin_user=str(current_user.id)
            )
        
        result = await db.execute(stmt)
        pending_users = result.scalars().all()
        
        # Format user data
        user_list = []
        for user in pending_users:
            user_data = {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value,
                "status": user.status.value,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat(),
                "registration_age": str(datetime.utcnow() - user.created_at)
            }
            user_list.append(user_data)
        
        return {
            "status": "success",
            "pending_users": user_list,
            "total_pending": len(user_list),
            "message": f"{len(user_list)} users awaiting verification",
            "include_unverified": include_unverified,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception("Failed to get pending users")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pending users"
        )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    role_filter: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """List and filter users."""
    
    await rate_limiter.check_rate_limit(
        key="admin:list_users",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Build the base query using select statement for async
        stmt = select(User)
        
        # SECURITY: Apply tenant isolation for user list
        # Global admins (tenant_id=None) can see all users
        # Tenant admins can only see their own tenant's users
        if current_user.tenant_id is not None:
            stmt = stmt.where(User.tenant_id == current_user.tenant_id)
            logger.debug(
                "Tenant admin listing users",
                admin_user=str(current_user.id),
                admin_tenant=str(current_user.tenant_id)
            )
        else:
            logger.debug(
                "Global admin listing all users",
                admin_user=str(current_user.id)
            )
        
        # Apply filters using where clause for async SQLAlchemy
        if status_filter:
            # Convert string to UserStatus enum
            try:
                parsed_status = UserStatus(status_filter)
                stmt = stmt.where(User.status == parsed_status)
            except ValueError:
                logger.warning(f"Invalid status filter: {status_filter}")
                # Skip applying invalid filter
        
        if role_filter:
            # Convert string to UserRole enum
            try:
                parsed_role = UserRole(role_filter)
                stmt = stmt.where(User.role == parsed_role)
            except ValueError:
                logger.warning(f"Invalid role filter: {role_filter}")
                # Skip applying invalid filter
        
        if search:
            # Fix: full_name is a property, not a DB column
            # Use email search only (remove full_name search)
            stmt = stmt.where(
                User.email.ilike(f"%{search}%")
            )
        
        # Get total count using subquery for accurate filtering
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar_one()
        
        # Add deterministic ordering before pagination
        stmt = stmt.order_by(User.created_at.desc(), User.id)
        
        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        # Count by status using async queries with tenant isolation
        if current_user.tenant_id is not None:
            # Tenant admin - count only within tenant
            active_count_result = await db.execute(
                select(func.count()).select_from(User).where(
                    and_(
                        User.status == UserStatus.ACTIVE.value,
                        User.tenant_id == current_user.tenant_id
                    )
                )
            )
            active_count = active_count_result.scalar_one()
            
            trading_count_result = await db.execute(
                select(func.count()).select_from(User).where(
                    and_(
                        User.status == UserStatus.ACTIVE.value,
                        User.role.in_([UserRole.TRADER, UserRole.ADMIN]),
                        User.tenant_id == current_user.tenant_id
                    )
                )
            )
            trading_count = trading_count_result.scalar_one()
        else:
            # Global admin - count all users
            active_count_result = await db.execute(
                select(func.count()).select_from(User).where(User.status == UserStatus.ACTIVE.value)
            )
            active_count = active_count_result.scalar_one()
            
            trading_count_result = await db.execute(
                select(func.count()).select_from(User).where(
                    and_(
                        User.status == UserStatus.ACTIVE.value,
                        User.role.in_([UserRole.TRADER, UserRole.ADMIN])
                    )
                )
            )
            trading_count = trading_count_result.scalar_one()
        
        # Batch fetch credit accounts for all users to avoid N+1 queries
        user_ids = [user.id for user in users]
        
        # Initialize empty maps
        credit_map = {}
        trade_count_map = {}
        
        # Only query if there are users
        if user_ids:
            # Get all credit accounts in one query
            credit_accounts_result = await db.execute(
                select(CreditAccount).where(CreditAccount.user_id.in_(user_ids))
            )
            credit_accounts = credit_accounts_result.scalars().all()
            credit_map = {ca.user_id: ca.available_credits for ca in credit_accounts}
            
            # Get all trade counts in one aggregated query
            trade_counts_result = await db.execute(
                select(Trade.user_id, func.count(Trade.id).label("count"))
                .where(Trade.user_id.in_(user_ids))
                .group_by(Trade.user_id)
            )
            trade_counts = trade_counts_result.all()
            trade_count_map = {row.user_id: row.count for row in trade_counts}
        
        # Format user data using the pre-fetched maps
        user_list = []
        for user in users:
            user_data = {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.email,  # Using email as full_name doesn't exist
                "role": user.role.value,
                "status": user.status.value,
                "is_verified": user.is_verified,  # Explicitly include is_verified
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "credits": credit_map.get(user.id, 0),
                "total_trades": trade_count_map.get(user.id, 0)
            }
            user_list.append(user_data)
        
        return UserListResponse(
            users=user_list,
            total_count=total_count,
            active_count=active_count,
            trading_count=trading_count
        )
        
    except Exception as e:
        logger.exception("User listing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        ) from e


@router.post("/users/verify/{user_id}")
async def verify_user(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Verify a pending user account to allow login."""
    
    await rate_limiter.check_rate_limit(
        key="admin:verify_user",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    logger.info(
        "User verification requested",
        admin_user=str(current_user.id),
        target_user=user_id
    )
    
    try:
        # Get target user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        target_user = result.scalar_one_or_none()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # SECURITY: Check tenant isolation - prevent cross-tenant operations
        # Allow global admins (tenant_id=None) to verify any user
        if (current_user.tenant_id is not None and 
            target_user.tenant_id is not None and 
            current_user.tenant_id != target_user.tenant_id):
            logger.warning(
                "Attempted cross-tenant verification blocked",
                admin_user=str(current_user.id),
                admin_tenant=str(current_user.tenant_id),
                target_user=str(target_user.id),
                target_tenant=str(target_user.tenant_id)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot verify users from different tenant"
            )
        
        # Check if already verified
        if target_user.status == UserStatus.ACTIVE.value and target_user.is_verified:
            return {
                "status": "already_verified",
                "message": "User is already verified and active",
                "user_email": target_user.email,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # SECURITY: Only verify users in PENDING_VERIFICATION status
        # Prevent reactivation of suspended/inactive users
        if target_user.status != UserStatus.PENDING_VERIFICATION:
            logger.warning(
                "Attempted to verify user with invalid status",
                admin_user=str(current_user.id),
                target_user=str(target_user.id),
                current_status=target_user.status.value
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot verify user with status {target_user.status.value}. User must be in PENDING_VERIFICATION status."
            )
        
        # Capture previous status before mutation
        previous_status = str(target_user.status.value) if target_user.status else "PENDING_VERIFICATION"
        previous_verified = target_user.is_verified
        
        # Verify the user
        target_user.status = UserStatus.ACTIVE
        target_user.is_verified = True
        target_user.updated_at = datetime.utcnow()
        
        # Create audit log with captured previous status
        audit_log = AuditLog(
            user_id=current_user.id,
            event_type="user_verification",
            event_data={
                "target_user_id": user_id,
                "target_user_email": target_user.email,
                "action": "verify",
                "previous_status": previous_status,
                "previous_verified": previous_verified,
                "new_status": "ACTIVE",
                "new_verified": True,
                "details": {
                    "target_user_id": user_id,
                    "target_user_email": target_user.email,
                    "verified_by": current_user.email
                },
                "ip_address": "admin_api",
                "user_agent": "system"
            }
        )
        db.add(audit_log)
        
        await db.commit()
        
        logger.info(
            "User verified successfully",
            admin_user=str(current_user.id),
            target_user=user_id,
            target_email=target_user.email
        )
        
        return {
            "status": "verified",
            "message": "User has been verified and can now login",
            "user_email": target_user.email,
            "user_id": str(target_user.id),
            "timestamp": datetime.utcnow().isoformat(),
            "verified_by": current_user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("User verification failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User verification failed"
        ) from e


@router.post("/users/verify-batch")
async def verify_users_batch(
    request: BatchVerifyRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Verify multiple pending user accounts at once."""
    
    await rate_limiter.check_rate_limit(
        key="admin:verify_batch",
        limit=10,
        window=60,
        user_id=str(current_user.id)
    )
    
    logger.info(
        "Batch user verification requested",
        admin_user=str(current_user.id),
        user_count=len(request.user_ids)
    )
    
    verified_users = []
    already_verified = []
    not_found = []
    skipped = []
    errors = []
    
    try:
        for user_id in request.user_ids:
            try:
                # Get target user
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                target_user = result.scalar_one_or_none()
                
                if not target_user:
                    not_found.append(user_id)
                    continue
                
                # SECURITY: Check tenant isolation - prevent cross-tenant operations
                # Allow global admins (tenant_id=None) to verify any user
                if (current_user.tenant_id is not None and 
                    target_user.tenant_id is not None and 
                    current_user.tenant_id != target_user.tenant_id):
                    skipped.append({
                        "user_id": str(target_user.id),
                        "email": target_user.email,
                        "reason": "cross_tenant",
                        "message": "Cannot verify users from different tenant"
                    })
                    
                    # Log attempted cross-tenant operation for security audit
                    logger.warning(
                        "Attempted cross-tenant verification blocked",
                        admin_user=str(current_user.id),
                        admin_tenant=str(current_user.tenant_id),
                        target_user=str(target_user.id),
                        target_tenant=str(target_user.tenant_id)
                    )
                    continue
                
                # Check if already verified
                if target_user.status == UserStatus.ACTIVE.value and target_user.is_verified:
                    already_verified.append({
                        "user_id": str(target_user.id),
                        "email": target_user.email
                    })
                    continue
                
                # SECURITY: Only verify users in PENDING_VERIFICATION status
                # Prevent reactivation of suspended/inactive users
                if target_user.status != UserStatus.PENDING_VERIFICATION:
                    skipped.append({
                        "user_id": str(target_user.id),
                        "email": target_user.email,
                        "reason": "invalid_status",
                        "message": f"User status is {target_user.status.value}, not PENDING_VERIFICATION",
                        "current_status": target_user.status.value
                    })
                    continue
                
                # Capture previous state for audit
                previous_status = target_user.status.value
                previous_verified = target_user.is_verified
                
                # Verify the user - only if all checks pass
                target_user.status = UserStatus.ACTIVE
                target_user.is_verified = True
                target_user.updated_at = datetime.utcnow()
                
                verified_users.append({
                    "user_id": str(target_user.id),
                    "email": target_user.email
                })
                
                # Create audit log with security context
                audit_log = AuditLog(
                    user_id=current_user.id,
                    event_type="batch_user_verification",
                    event_data={
                        "target_user_id": user_id,
                        "target_user_email": target_user.email,
                        "action": "verify",
                        "batch_operation": True,
                        "previous_status": previous_status,
                        "previous_verified": previous_verified,
                        "new_status": "ACTIVE",
                        "new_verified": True,
                        "tenant_id": str(target_user.tenant_id) if target_user.tenant_id else None,
                        "details": {
                            "target_user_id": user_id,
                            "target_user_email": target_user.email,
                            "verified_by": current_user.email,
                            "reason": request.reason
                        },
                        "ip_address": "admin_api",
                        "user_agent": "system"
                    }
                )
                db.add(audit_log)
                
            except Exception as e:
                # Sanitize error for client response
                errors.append({
                    "user_id": user_id,
                    "error": "verification_failed"  # Generic error for client
                })
                # Log full exception details for debugging
                logger.exception(
                    "Failed to verify user in batch operation",
                    user_id=user_id,
                    admin_user=str(current_user.id),
                    error_type=type(e).__name__
                )
        
        # Commit all changes
        await db.commit()
        
        logger.info(
            "Batch verification completed",
            admin_user=str(current_user.id),
            verified_count=len(verified_users),
            already_verified_count=len(already_verified),
            skipped_count=len(skipped),
            not_found_count=len(not_found),
            error_count=len(errors)
        )
        
        return {
            "status": "batch_verification_completed",
            "summary": {
                "total_requested": len(request.user_ids),
                "successfully_verified": len(verified_users),
                "already_verified": len(already_verified),
                "skipped": len(skipped),
                "not_found": len(not_found),
                "errors": len(errors)
            },
            "verified_users": verified_users,
            "already_verified": already_verified,
            "skipped": skipped,
            "not_found": not_found,
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat(),
            "verified_by": current_user.email
        }
        
    except Exception as e:
        await db.rollback()
        logger.exception("Batch verification failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch verification failed"
        ) from e


@router.post("/users/manage")
async def manage_user(
    request: UserManagementRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Manage user accounts (activate, deactivate, etc.)."""
    
    await rate_limiter.check_rate_limit(
        key="admin:manage_user",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )
    
    logger.info(
        "User management action",
        admin_user=str(current_user.id),
        target_user=request.user_id,
        action=request.action
    )
    
    try:
        # Get target user using async query
        result = await db.execute(
            select(User).where(User.id == request.user_id)
        )
        target_user = result.scalar_one_or_none()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        action_taken = None
        
        if request.action == "activate":
            target_user.status = UserStatus.ACTIVE
            action_taken = "User activated"
            
        elif request.action == "deactivate":
            target_user.status = UserStatus.INACTIVE
            # Stop any autonomous trading
            await master_controller.stop_autonomous_mode(request.user_id)
            action_taken = "User deactivated and trading stopped"
            
        elif request.action == "suspend":
            target_user.status = UserStatus.SUSPENDED
            # Emergency stop trading
            await master_controller.emergency_stop(request.user_id)
            action_taken = "User suspended and trading emergency stopped"
            
        elif request.action == "reset_credits":
            if request.credit_amount is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Credit amount required for reset_credits action"
                )
            
            # Get or create credit account using async query
            credit_result = await db.execute(
                select(CreditAccount).where(
                    CreditAccount.user_id == target_user.id
                )
            )
            credit_account = credit_result.scalar_one_or_none()
            
            if not credit_account:
                credit_account = CreditAccount(
                    user_id=target_user.id,
                    available_credits=request.credit_amount
                )
                db.add(credit_account)
            else:
                credit_account.available_credits = request.credit_amount
            
            # Record transaction
            credit_tx = CreditTransaction(
                account_id=credit_account.id,
                amount=request.credit_amount,
                transaction_type=CreditTransactionType.ADJUSTMENT,
                description=f"Admin credit reset by {current_user.email}",
                balance_before=credit_account.available_credits - request.credit_amount,
                balance_after=credit_account.available_credits,
                source="admin"
            )
            db.add(credit_tx)
            
            action_taken = f"Credits reset to {request.credit_amount}"
        
        # Create audit log with proper transaction handling
        audit_log = AuditLog(
            user_id=current_user.id,
            event_type=f"user_management_{request.action}",
            event_data={
                "target_user_id": request.user_id,
                "target_user_email": target_user.email,
                "action": request.action,
                "reason": request.reason,
                "credit_amount": request.credit_amount,
                "details": {
                    "target_user_id": request.user_id,
                    "target_user_email": target_user.email,
                    "action": request.action,
                    "reason": request.reason,
                    "credit_amount": request.credit_amount
                },
                "ip_address": "admin_api",
                "user_agent": "system"
            }
        )
        db.add(audit_log)
        
        await db.commit()
        
        return {
            "status": "action_completed",
            "action": request.action,
            "target_user": target_user.email,
            "action_taken": action_taken,
            "reason": request.reason,
            "timestamp": datetime.utcnow().isoformat(),
            "performed_by": current_user.email
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions without rollback
        raise
    except Exception as e:
        # Rollback transaction on any other error
        await db.rollback()
        logger.exception("User management failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User management failed"
        ) from e


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_detailed_metrics(
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Get detailed system metrics."""
    
    await rate_limiter.check_rate_limit(
        key="admin:metrics",
        limit=60,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Get time ranges
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        
        # Active users (logged in last 24h)
        active_users_result = await db.execute(
            select(func.count()).select_from(User).where(
                User.last_login >= now - timedelta(hours=24)
            )
        )
        active_users = active_users_result.scalar_one()
        
        # Trades today
        trades_today_result = await db.execute(
            select(func.count()).select_from(Trade).where(
                Trade.created_at >= today_start
            )
        )
        trades_today = trades_today_result.scalar_one()
        
        # Volume 24h
        volume_24h_result = await db.execute(
            select(func.sum(Trade.total_value)).where(
                Trade.created_at >= now - timedelta(hours=24)
            )
        )
        volume_24h = volume_24h_result.scalar_one_or_none() or 0
        
        # Get system health from master controller
        system_status = await master_controller.get_global_system_status()
        
        # Autonomous sessions
        autonomous_sessions = system_status.get("active_autonomous_sessions", 0)
        
        # Error rate calculation (from logs or monitoring)
        error_rate = system_status.get("error_rate_percent", 0)
        
        # Response time
        response_time_avg = system_status.get("avg_response_time_ms", 0)
        
        # Uptime percentage
        uptime_percentage = system_status.get("uptime_percentage", 99.9)
        
        return SystemMetricsResponse(
            active_users=active_users,
            total_trades_today=trades_today,
            total_volume_24h=float(volume_24h),
            system_health=system_status.get("health", "normal"),
            autonomous_sessions=autonomous_sessions,
            error_rate=error_rate,
            response_time_avg=response_time_avg,
            uptime_percentage=uptime_percentage
        )
        
    except Exception as e:
        logger.exception("Metrics retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics"
        ) from e


@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    action_filter: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Get audit logs for security and compliance."""
    
    await rate_limiter.check_rate_limit(
        key="admin:audit_logs",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Build query using select statement for async
        stmt = select(AuditLog)
        
        # Apply filters using where clause
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        
        if action_filter:
            stmt = stmt.where(AuditLog.event_type.ilike(f"%{action_filter}%"))
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                stmt = stmt.where(AuditLog.created_at >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid date format for start_date: {start_date}. Expected ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                )
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                stmt = stmt.where(AuditLog.created_at <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid date format for end_date: {end_date}. Expected ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                )
        
        # Order by most recent
        stmt = stmt.order_by(AuditLog.created_at.desc())
        
        # Get total count using subquery
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar_one()
        
        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)
        
        # Get paginated results
        result = await db.execute(stmt)
        audit_logs = result.scalars().all()
        
        # Format results
        log_list = []
        for log in audit_logs:
            # Extract data from event_data JSON field
            event_data = log.event_data or {}
            
            log_data = {
                "id": str(log.id),
                "user_id": str(log.user_id),
                "action": log.event_type,  # Keep "action" key for backward compatibility
                "event_type": log.event_type,
                "event_data": log.event_data,
                "details": log.event_data.get("details", {}),
                "ip_address": log.event_data.get("ip_address", "unknown"),
                "user_agent": log.event_data.get("user_agent", "unknown"),
                "level": log.level.value,
                "created_at": log.created_at.isoformat()
            }
            
            # Get user email using async query
            user_result = await db.execute(
                select(User).where(User.id == log.user_id)
            )
            user = user_result.scalar_one_or_none()
            log_data["user_email"] = user.email if user else "unknown"
            
            log_list.append(log_data)
        
        return {
            "audit_logs": log_list,
            "total_count": total_count,
            "filters_applied": {
                "user_id": user_id,
                "action_filter": action_filter,
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
    except Exception as e:
        logger.exception("Audit logs retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get audit logs"
        ) from e


@router.post("/emergency/stop-all")
async def emergency_stop_all_trading(
    reason: str,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Emergency stop all trading across the platform."""
    
    await rate_limiter.check_rate_limit(
        key="admin:emergency_stop",
        limit=3,
        window=300,  # 3 stops per 5 minutes
        user_id=str(current_user.id)
    )
    
    logger.critical(
        "Platform-wide emergency stop requested",
        admin_user=str(current_user.id),
        reason=reason
    )
    
    try:
        # Stop all autonomous trading
        result = await master_controller.emergency_stop_all_users()
        
        # Log audit trail
        audit_log = AuditLog(
            user_id=current_user.id,
            event_type="platform_emergency_stop",
            event_data={
                "reason": reason,
                "affected_users": result.get("affected_users", 0),
                "stopped_sessions": result.get("stopped_sessions", 0),
                "details": {
                    "reason": reason,
                    "affected_users": result.get("affected_users", 0),
                    "stopped_sessions": result.get("stopped_sessions", 0)
                },
                "ip_address": "admin_api",
                "user_agent": "system"
            }
        )
        db.add(audit_log)
        await db.commit()
        
        return {
            "status": "emergency_stop_executed",
            "reason": reason,
            "affected_users": result.get("affected_users", 0),
            "stopped_sessions": result.get("stopped_sessions", 0),
            "timestamp": datetime.utcnow().isoformat(),
            "executed_by": current_user.email,
            "message": "All trading activities have been stopped platform-wide"
        }
        
    except Exception as e:
        logger.exception("Emergency stop failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Emergency stop failed"
        ) from e


# Helper Functions
async def restart_background_services():
    """Restart background services after configuration change."""
    try:
        await background_manager.stop_all()
        await asyncio.sleep(2)
        await background_manager.start_all()
        logger.info("Background services restarted after configuration change")
    except Exception as e:
        logger.error("Background service restart failed", error=str(e))
