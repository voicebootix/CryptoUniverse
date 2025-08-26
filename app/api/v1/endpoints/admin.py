"""
Admin API Endpoints - Enterprise Grade

Provides administrative functions for system management, user management,
system configuration, and monitoring for the AI money manager platform.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.core.config import get_settings
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_user, require_role
from app.models.user import User, UserRole, UserStatus
from app.models.tenant import Tenant
from app.models.trading import Trade, Position
from app.models.exchange import ExchangeAccount
from app.models.credit import CreditAccount, CreditTransaction
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


class UserManagementRequest(BaseModel):
    user_id: str
    action: str  # "activate", "deactivate", "suspend", "reset_credits"
    reason: Optional[str] = None
    credit_amount: Optional[int] = None
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ["activate", "deactivate", "suspend", "reset_credits", "reset_password"]
        if v.lower() not in allowed_actions:
            raise ValueError(f"Action must be one of: {allowed_actions}")
        return v.lower()


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
    current_user: User = Depends(require_role([UserRole.ADMIN]))
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
        db: Session = next(get_database())
        
        # Count active users
        active_users = db.query(User).filter(
            User.status == UserStatus.ACTIVE,
            User.last_login >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        # Count trades today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        trades_today = db.query(Trade).filter(
            Trade.created_at >= today_start
        ).count()
        
        # Calculate volume
        volume_24h = db.query(func.sum(Trade.amount)).filter(
            Trade.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).scalar() or 0
        
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
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("System status retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system status: {str(e)}"
        )


@router.post("/system/configure")
async def configure_system(
    request: SystemConfigRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
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
            action="system_configuration",
            details={"changes": changes_applied},
            ip_address="admin_api",
            user_agent="system"
        )
        
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
        logger.error("System configuration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System configuration failed: {str(e)}"
        )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    role_filter: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_database)
):
    """List and filter users."""
    
    await rate_limiter.check_rate_limit(
        key="admin:list_users",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        query = db.query(User)
        
        # Apply filters
        if status_filter:
            query = query.filter(User.status == status_filter)
        
        if role_filter:
            query = query.filter(User.role == role_filter)
        
        if search:
            query = query.filter(
                or_(
                    User.email.ilike(f"%{search}%"),
                    User.full_name.ilike(f"%{search}%")
                )
            )
        
        # Get total count
        total_count = query.count()
        
        # Get paginated results
        users = query.offset(skip).limit(limit).all()
        
        # Count by status
        active_count = db.query(User).filter(User.status == UserStatus.ACTIVE).count()
        trading_count = db.query(User).filter(
            and_(
                User.status == UserStatus.ACTIVE,
                User.role.in_([UserRole.TRADER, UserRole.ADMIN])
            )
        ).count()
        
        # Format user data
        user_list = []
        for user in users:
            user_data = {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "status": user.status.value,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None
            }
            
            # Get credit balance
            credit_account = db.query(CreditAccount).filter(
                CreditAccount.user_id == user.id
            ).first()
            user_data["credits"] = credit_account.available_credits if credit_account else 0
            
            # Get trading stats
            trade_count = db.query(Trade).filter(Trade.user_id == user.id).count()
            user_data["total_trades"] = trade_count
            
            user_list.append(user_data)
        
        return UserListResponse(
            users=user_list,
            total_count=total_count,
            active_count=active_count,
            trading_count=trading_count
        )
        
    except Exception as e:
        logger.error("User listing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


@router.post("/users/manage")
async def manage_user(
    request: UserManagementRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_database)
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
        # Get target user
        target_user = db.query(User).filter(User.id == request.user_id).first()
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
            
            # Get or create credit account
            credit_account = db.query(CreditAccount).filter(
                CreditAccount.user_id == target_user.id
            ).first()
            
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
                user_id=target_user.id,
                amount=request.credit_amount,
                transaction_type="admin_adjustment",
                description=f"Admin credit reset by {current_user.email}",
                reference_id=str(current_user.id)
            )
            db.add(credit_tx)
            
            action_taken = f"Credits reset to {request.credit_amount}"
        
        # Create audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action=f"user_management_{request.action}",
            details={
                "target_user_id": request.user_id,
                "target_user_email": target_user.email,
                "action": request.action,
                "reason": request.reason,
                "credit_amount": request.credit_amount
            },
            ip_address="admin_api",
            user_agent="system"
        )
        db.add(audit_log)
        
        db.commit()
        
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
        raise
    except Exception as e:
        logger.error("User management failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User management failed: {str(e)}"
        )


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_detailed_metrics(
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_database)
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
        active_users = db.query(User).filter(
            User.last_login >= now - timedelta(hours=24)
        ).count()
        
        # Trades today
        trades_today = db.query(Trade).filter(
            Trade.created_at >= today_start
        ).count()
        
        # Volume 24h
        volume_24h = db.query(func.sum(Trade.amount)).filter(
            Trade.created_at >= now - timedelta(hours=24)
        ).scalar() or 0
        
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
        logger.error("Metrics retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    action_filter: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_database)
):
    """Get audit logs for security and compliance."""
    
    await rate_limiter.check_rate_limit(
        key="admin:audit_logs",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        query = db.query(AuditLog)
        
        # Apply filters
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if action_filter:
            query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(AuditLog.created_at >= start_dt)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(AuditLog.created_at <= end_dt)
        
        # Order by most recent
        query = query.order_by(AuditLog.created_at.desc())
        
        # Get total count
        total_count = query.count()
        
        # Get paginated results
        audit_logs = query.offset(skip).limit(limit).all()
        
        # Format results
        log_list = []
        for log in audit_logs:
            log_data = {
                "id": str(log.id),
                "user_id": str(log.user_id),
                "action": log.action,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat()
            }
            
            # Get user email
            user = db.query(User).filter(User.id == log.user_id).first()
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
        logger.error("Audit logs retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit logs: {str(e)}"
        )


@router.post("/emergency/stop-all")
async def emergency_stop_all_trading(
    reason: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
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
            action="platform_emergency_stop",
            details={
                "reason": reason,
                "affected_users": result.get("affected_users", 0),
                "stopped_sessions": result.get("stopped_sessions", 0)
            },
            ip_address="admin_api",
            user_agent="system"
        )
        
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
        logger.error("Emergency stop failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency stop failed: {str(e)}"
        )


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
