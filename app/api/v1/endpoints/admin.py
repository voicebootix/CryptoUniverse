"""
Admin API Endpoints - Enterprise Grade

Provides administrative functions for system management, user management,
system configuration, and monitoring for the AI money manager platform.
"""

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Iterable
import uuid
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, field_validator
from sqlalchemy import and_, or_, func, select, case, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_database
from app.core.logging import get_recent_logs
from app.api.v1.endpoints.auth import get_current_user, require_role
from app.models.user import User, UserRole, UserStatus, UserProfile
from app.models.tenant import Tenant
from app.models.trading import Trade, Position, TradingStrategy
from app.models.exchange import ExchangeAccount
from app.models.credit import CreditAccount, CreditTransactionType
from app.models.system import SystemHealth, AuditLog
from app.models.strategy_access import UserStrategyAccess, StrategyAccessType
from app.models.strategy_submission import StrategySubmission, StrategyStatus
from app.models.signal import SignalDeliveryLog, SignalEvent, SignalSubscription, SignalChannel
from app.models.copy_trading import StrategyPublisher
from app.services.master_controller import MasterSystemController
from app.services.background import BackgroundServiceManager
from app.services.rate_limit import rate_limiter
from app.services.credit_ledger import credit_ledger, InsufficientCreditsError
from app.services.strategy_submission_service import strategy_submission_service

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()

# Initialize services
master_controller = MasterSystemController()
background_manager = BackgroundServiceManager()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _decimal_to_float(value: Optional[Any]) -> float:
    """Safely convert Decimal/None values to float."""

    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_divide(numerator: float, denominator: float) -> float:
    """Return numerator / denominator guarding against division by zero."""

    if not denominator:
        return 0.0
    return numerator / denominator


class PeriodInfo(BaseModel):
    start: Optional[datetime]
    previous_start: Optional[datetime]
    previous_end: Optional[datetime]
    duration_days: Optional[int]


class SignalDeliveryAudit(BaseModel):
    delivery_id: UUID
    channel_slug: str
    user_id: UUID
    delivery_channel: str
    status: str
    credit_cost: int
    delivered_at: datetime
    acknowledged_at: Optional[datetime]
    executed_at: Optional[datetime]
    metadata: Dict[str, Any]
    payload: Dict[str, Any]


def _resolve_period(period: Optional[str]) -> PeriodInfo:
    """Resolve a dashboard period string into start windows."""

    now = datetime.utcnow()
    period_key = (period or "30d").lower()

    if period_key == "7d":
        start = now - timedelta(days=7)
    elif period_key == "30d":
        start = now - timedelta(days=30)
    elif period_key == "90d":
        start = now - timedelta(days=90)
    elif period_key == "ytd":
        start = datetime(now.year, 1, 1)
    elif period_key == "all":
        return PeriodInfo(start=None, previous_start=None, previous_end=None, duration_days=None)
    else:
        start = now - timedelta(days=30)

    duration = now - start
    duration_days = max(int(duration.total_seconds() // 86400) or 1, 1)
    previous_end = start
    previous_start = start - duration if duration_days else None

    return PeriodInfo(
        start=start,
        previous_start=previous_start,
        previous_end=previous_end,
        duration_days=duration_days,
    )


def _collect_revenue_by_user(rows: Iterable[Any]) -> Dict[str, float]:
    """Convert revenue aggregation rows into {user_id: revenue}."""

    revenue_map: Dict[str, float] = {}
    for user_id, revenue_value in rows:
        revenue_map[str(user_id)] = _decimal_to_float(revenue_value)
    return revenue_map


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Credit Analytics Endpoints
# ---------------------------------------------------------------------------


@router.get("/credits/analytics")
async def get_credit_analytics(
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Return aggregated credit system analytics for the admin dashboard."""

    await rate_limiter.check_rate_limit(
        key="admin:credits_analytics",
        limit=60,
        window=60,
        user_id=str(current_user.id)
    )

    try:
        totals_result = await db.execute(
            select(
                func.coalesce(func.sum(CreditAccount.total_credits), 0),
                func.coalesce(func.sum(CreditAccount.available_credits), 0),
                func.coalesce(func.sum(CreditAccount.used_credits), 0),
                func.count(CreditAccount.id),
            )
        )
        total_credits, total_available, total_used, account_count = totals_result.one()

        try:
            revenue_result = await db.execute(
                select(
                    func.coalesce(func.sum(CreditTransaction.usd_value), 0),
                    func.coalesce(func.sum(CreditTransaction.profit_amount_usd), 0),
                )
            )
            total_revenue, total_profit = revenue_result.one()
        except SQLAlchemyError as revenue_error:
            logger.warning(
                "credit_analytics_revenue_fallback",
                error=str(revenue_error),
                note="profit columns missing, defaulting to zero values",
            )
            total_revenue, total_profit = (0, 0)

        active_users_result = await db.execute(
            select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
        )
        active_users = active_users_result.scalar_one_or_none() or 0

        strategies_purchased_result = await db.execute(
            select(func.count(UserStrategyAccess.id)).where(
                UserStrategyAccess.access_type == StrategyAccessType.PURCHASED
            )
        )
        strategies_purchased = strategies_purchased_result.scalar_one_or_none() or 0

        platform_fee_collected = _decimal_to_float(total_profit) * 0.25

        usage_start = datetime.utcnow() - timedelta(days=14)
        usage_stmt = (
            select(
                func.date(CreditTransaction.created_at).label("usage_date"),
                func.coalesce(
                    func.sum(
                        case(
                            (CreditTransaction.amount < 0, -CreditTransaction.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("credits_used"),
                func.coalesce(func.sum(CreditTransaction.usd_value), 0).label("revenue"),
            )
            .where(CreditTransaction.created_at >= usage_start)
            .group_by(func.date(CreditTransaction.created_at))
            .order_by(func.date(CreditTransaction.created_at))
        )

        try:
            usage_rows = await db.execute(usage_stmt)
            usage_data = usage_rows.all()
            daily_usage = [
                {
                    "date": usage_date.isoformat() if isinstance(usage_date, date) else str(usage_date),
                    "credits_used": int(credits_used or 0),
                    "revenue": round(_decimal_to_float(revenue_value), 2),
                }
                for usage_date, credits_used, revenue_value in usage_data
            ]
        except SQLAlchemyError as usage_error:
            logger.warning(
                "credit_analytics_usage_fallback",
                error=str(usage_error),
                note="Falling back to usage counts without revenue totals",
            )

            fallback_usage_stmt = (
                select(
                    func.date(CreditTransaction.created_at).label("usage_date"),
                    func.coalesce(
                        func.sum(
                            case(
                                (CreditTransaction.amount < 0, -CreditTransaction.amount),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("credits_used"),
                )
                .where(CreditTransaction.created_at >= usage_start)
                .group_by(func.date(CreditTransaction.created_at))
                .order_by(func.date(CreditTransaction.created_at))
            )

            fallback_rows = await db.execute(fallback_usage_stmt)
            daily_usage = [
                {
                    "date": usage_date.isoformat() if isinstance(usage_date, date) else str(usage_date),
                    "credits_used": int(credits_used or 0),
                    "revenue": 0.0,
                }
                for usage_date, credits_used in fallback_rows.all()
            ]

        return {
            "total_credits_issued": int(total_credits or 0),
            "total_credits_used": int(total_used or 0),
            "available_credits": int(total_available or 0),
            "credit_accounts": int(account_count or 0),
            "total_revenue_usd": round(_decimal_to_float(total_revenue), 2),
            "total_profit_shared": round(_decimal_to_float(total_profit), 2),
            "active_users": int(active_users),
            "strategies_purchased": int(strategies_purchased),
            "platform_fee_collected": round(platform_fee_collected, 2),
            "daily_credit_usage": daily_usage,
        }

    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("credit_analytics_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate credit analytics",
        ) from exc


@router.get("/credits/transactions")
async def get_credit_transactions(
    limit: int = 50,
    include_user_info: bool = True,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database),
):
    """Return recent credit transactions with optional user metadata."""

    await rate_limiter.check_rate_limit(
        key="admin:credit_transactions",
        limit=100,
        window=60,
        user_id=str(current_user.id),
    )

    limit = max(1, min(limit, 200))

    def _build_transactions(rows: Iterable[Any], include_financials: bool) -> List[Dict[str, Any]]:
        transactions: List[Dict[str, Any]] = []
        for row in rows:
            user: User = row.User  # type: ignore[assignment]
            first_name = getattr(row, "first_name", None)
            last_name = getattr(row, "last_name", None)
            name_parts = [part for part in [first_name, last_name] if part]
            user_name = " ".join(name_parts) or user.full_name_display

            transaction_type = getattr(row, "transaction_type", None)
            if hasattr(transaction_type, "value"):
                transaction_type = transaction_type.value
            elif transaction_type is None:
                transaction_type = "unknown"
            else:
                transaction_type = str(transaction_type)

            status_value = getattr(row, "status", None)
            if hasattr(status_value, "value"):
                status_value = status_value.value
            elif status_value is None:
                status_value = "unknown"
            else:
                status_value = str(status_value)

            usd_value = getattr(row, "usd_value", None) if include_financials else None
            profit_value = (
                getattr(row, "profit_amount_usd", None) if include_financials else None
            )

            transactions.append(
                {
                    "id": str(row.id),
                    "user_id": str(user.id),
                    "user_email": user.email if include_user_info else None,
                    "user_name": user_name if include_user_info else None,
                    "amount": int(getattr(row, "amount", 0) or 0),
                    "transaction_type": transaction_type,
                    "description": getattr(row, "description", ""),
                    "balance_before": int(getattr(row, "balance_before", 0) or 0),
                    "balance_after": int(getattr(row, "balance_after", 0) or 0),
                    "usd_value": round(_decimal_to_float(usd_value), 2)
                    if include_financials
                    else 0.0,
                    "profit_amount_usd": round(_decimal_to_float(profit_value), 2)
                    if include_financials
                    else 0.0,
                    "status": status_value,
                    "source": getattr(row, "source", None),
                    "reference_id": getattr(row, "reference_id", None),
                    "created_at": row.created_at.isoformat()
                    if getattr(row, "created_at", None)
                    else None,
                }
            )

        return transactions

    try:
        base_query = (
            select(
                CreditTransaction.id,
                CreditTransaction.amount,
                CreditTransaction.transaction_type,
                CreditTransaction.description,
                CreditTransaction.balance_before,
                CreditTransaction.balance_after,
                CreditTransaction.usd_value,
                CreditTransaction.profit_amount_usd,
                CreditTransaction.status,
                CreditTransaction.source,
                CreditTransaction.reference_id,
                CreditTransaction.created_at,
                User,
                UserProfile.first_name,
                UserProfile.last_name,
            )
            .join(CreditAccount, CreditTransaction.account_id == CreditAccount.id)
            .join(User, CreditAccount.user_id == User.id)
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
        )

        try:
            rows = await db.execute(base_query)
            transactions = _build_transactions(rows.all(), include_financials=True)
        except SQLAlchemyError as query_error:
            logger.warning(
                "credit_transactions_fallback",
                error=str(query_error),
                note="Falling back to minimal transaction payload",
            )

            fallback_query = (
                select(
                    CreditTransaction.id,
                    CreditTransaction.amount,
                    CreditTransaction.transaction_type,
                    CreditTransaction.description,
                    CreditTransaction.balance_before,
                    CreditTransaction.balance_after,
                    CreditTransaction.status,
                    CreditTransaction.source,
                    CreditTransaction.reference_id,
                    CreditTransaction.created_at,
                    User,
                    UserProfile.first_name,
                    UserProfile.last_name,
                )
                .join(CreditAccount, CreditTransaction.account_id == CreditAccount.id)
                .join(User, CreditAccount.user_id == User.id)
                .outerjoin(UserProfile, UserProfile.user_id == User.id)
                .order_by(CreditTransaction.created_at.desc())
                .limit(limit)
            )

            rows = await db.execute(fallback_query)
            transactions = _build_transactions(rows.all(), include_financials=False)
        return {
            "transactions": transactions,
            "count": len(transactions),
        }

    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("credit_transactions_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch credit transactions",
        ) from exc


# ---------------------------------------------------------------------------
# Revenue Analytics Endpoints
# ---------------------------------------------------------------------------


@router.get("/revenue/metrics")
async def get_revenue_metrics(
    period: str = "30d",
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database),
):
    """Return high-level revenue metrics for the admin dashboard."""

    await rate_limiter.check_rate_limit(
        key="admin:revenue_metrics",
        limit=60,
        window=60,
        user_id=str(current_user.id),
    )

    period_info = _resolve_period(period)
    current_start = period_info.start
    previous_start = period_info.previous_start
    previous_end = period_info.previous_end

    try:
        revenue_stmt = select(
            func.coalesce(func.sum(CreditTransaction.usd_value), 0).label("revenue"),
            func.count(CreditTransaction.id).label("transactions"),
        )
        if current_start:
            revenue_stmt = revenue_stmt.where(CreditTransaction.created_at >= current_start)

        try:
            revenue_result = await db.execute(revenue_stmt)
            current_revenue_value, total_transactions = revenue_result.one()
            current_revenue = _decimal_to_float(current_revenue_value)
        except SQLAlchemyError as revenue_error:
            logger.warning(
                "revenue_metrics_revenue_fallback",
                error=str(revenue_error),
                note="Defaulting revenue totals to zero",
            )
            current_revenue = 0.0
            total_transactions = 0

        previous_revenue = 0.0
        if previous_start and previous_end:
            previous_stmt = select(func.coalesce(func.sum(CreditTransaction.usd_value), 0)).where(
                CreditTransaction.created_at >= previous_start,
                CreditTransaction.created_at < previous_end,
            )
            try:
                previous_value = (await db.execute(previous_stmt)).scalar_one_or_none()
                previous_revenue = _decimal_to_float(previous_value)
            except SQLAlchemyError as previous_error:
                logger.warning(
                    "revenue_metrics_previous_fallback",
                    error=str(previous_error),
                    note="Previous revenue defaulted to zero",
                )
                previous_revenue = 0.0

        monthly_ago = datetime.utcnow() - timedelta(days=30)
        monthly_revenue_stmt = select(func.coalesce(func.sum(CreditTransaction.usd_value), 0)).where(
            CreditTransaction.created_at >= monthly_ago
        )
        try:
            monthly_revenue = _decimal_to_float(
                (await db.execute(monthly_revenue_stmt)).scalar_one_or_none()
            )
        except SQLAlchemyError as monthly_error:
            logger.warning(
                "revenue_metrics_monthly_fallback",
                error=str(monthly_error),
                note="Monthly revenue defaulted to zero",
            )
            monthly_revenue = 0.0

        revenue_growth = 0.0
        if previous_revenue:
            revenue_growth = _safe_divide(current_revenue - previous_revenue, previous_revenue) * 100

        total_users = (await db.execute(select(func.count(User.id)))).scalar_one_or_none() or 0
        active_users = (
            await db.execute(select(func.count(User.id)).where(User.status == UserStatus.ACTIVE))
        ).scalar_one_or_none() or 0
        premium_users = (
            await db.execute(
                select(func.count(CreditAccount.id)).where(CreditAccount.available_credits >= 500)
            )
        ).scalar_one_or_none() or 0

        new_user_start = current_start or (datetime.utcnow() - timedelta(days=30))
        new_users = (
            await db.execute(select(func.count(User.id)).where(User.created_at >= new_user_start))
        ).scalar_one_or_none() or 0

        previous_new_users = 0
        if previous_start and previous_end:
            previous_new_users = (
                await db.execute(
                    select(func.count(User.id)).where(
                        User.created_at >= previous_start,
                        User.created_at < previous_end,
                    )
                )
            ).scalar_one_or_none() or 0

        user_growth_rate = 0.0
        if previous_new_users:
            user_growth_rate = _safe_divide(new_users - previous_new_users, previous_new_users) * 100
        elif new_users:
            user_growth_rate = 100.0

        churn_users = (
            await db.execute(
                select(func.count(User.id)).where(User.status == UserStatus.SUSPENDED)
            )
        ).scalar_one_or_none() or 0
        churn_rate = _safe_divide(churn_users, total_users) * 100

        total_strategies = (
            await db.execute(select(func.count(TradingStrategy.id)))
        ).scalar_one_or_none() or 0
        published_strategies = (
            await db.execute(
                select(func.count(StrategySubmission.id)).where(
                    StrategySubmission.status == StrategyStatus.PUBLISHED
                )
            )
        ).scalar_one_or_none() or 0
        strategy_publishers = (
            await db.execute(
                select(func.count(func.distinct(StrategySubmission.user_id))).where(
                    StrategySubmission.status.in_([
                        StrategyStatus.APPROVED,
                        StrategyStatus.PUBLISHED,
                    ])
                )
            )
        ).scalar_one_or_none() or 0

        avg_strategy_price_value = (
            await db.execute(
                select(func.avg(StrategySubmission.price_amount)).where(
                    StrategySubmission.price_amount.isnot(None)
                )
            )
        ).scalar_one_or_none()
        avg_strategy_price = _decimal_to_float(avg_strategy_price_value)

        profit_stmt = select(func.coalesce(func.sum(CreditTransaction.profit_amount_usd), 0))
        if current_start:
            profit_stmt = profit_stmt.where(CreditTransaction.created_at >= current_start)
        try:
            total_profit_shared = _decimal_to_float(
                (await db.execute(profit_stmt)).scalar_one_or_none()
            )
        except SQLAlchemyError as profit_error:
            logger.warning(
                "revenue_metrics_profit_fallback",
                error=str(profit_error),
                note="Profit totals defaulted to zero",
            )
            total_profit_shared = 0.0
        profit_share_revenue = total_profit_shared * 0.25
        avg_profit_share_per_user = _safe_divide(total_profit_shared, active_users)

        credits_totals = await db.execute(
            select(
                func.coalesce(func.sum(CreditAccount.total_credits), 0),
                func.coalesce(func.sum(CreditAccount.used_credits), 0),
                func.count(CreditAccount.id),
            )
        )
        total_credits_issued, total_credits_used, credit_accounts = credits_totals.one()
        credit_conversion_rate = _safe_divide(
            _decimal_to_float(total_credits_used), _decimal_to_float(total_credits_issued)
        ) * 100
        avg_credits_per_user = _safe_divide(
            _decimal_to_float(total_credits_issued), credit_accounts or 1
        )

        transaction_volume = current_revenue
        avg_transaction_value = _safe_divide(transaction_volume, total_transactions)

        return {
            "total_revenue": round(current_revenue, 2),
            "monthly_revenue": round(monthly_revenue, 2),
            "revenue_growth": round(revenue_growth, 2),
            "arr": round(monthly_revenue * 12, 2),
            "mrr": round(monthly_revenue, 2),
            "total_users": int(total_users),
            "active_users": int(active_users),
            "premium_users": int(premium_users),
            "user_growth_rate": round(user_growth_rate, 2),
            "churn_rate": round(churn_rate, 2),
            "total_strategies": int(total_strategies),
            "published_strategies": int(published_strategies),
            "strategy_publishers": int(strategy_publishers),
            "avg_strategy_price": round(avg_strategy_price, 2),
            "total_transactions": int(total_transactions),
            "transaction_volume": round(transaction_volume, 2),
            "avg_transaction_value": round(avg_transaction_value, 2),
            "total_profit_shared": round(total_profit_shared, 2),
            "profit_share_revenue": round(profit_share_revenue, 2),
            "avg_profit_share_per_user": round(avg_profit_share_per_user, 2),
            "total_credits_issued": int(total_credits_issued or 0),
            "total_credits_used": int(total_credits_used or 0),
            "credit_conversion_rate": round(credit_conversion_rate, 2),
            "avg_credits_per_user": round(avg_credits_per_user, 2),
        }

    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("revenue_metrics_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate revenue metrics",
        ) from exc


@router.get("/revenue/breakdown")
async def get_revenue_breakdown(
    period: str = "30d",
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database),
):
    """Return revenue breakdown by stream (credits, subscriptions, etc.)."""

    await rate_limiter.check_rate_limit(
        key="admin:revenue_breakdown",
        limit=60,
        window=60,
        user_id=str(current_user.id),
    )

    period_info = _resolve_period(period)
    current_start = period_info.start
    previous_start = period_info.previous_start
    previous_end = period_info.previous_end

    try:
        breakdown_stmt = (
            select(
                CreditTransaction.transaction_type,
                func.coalesce(func.sum(CreditTransaction.usd_value), 0).label("amount"),
            )
            .group_by(CreditTransaction.transaction_type)
        )
        if current_start:
            breakdown_stmt = breakdown_stmt.where(CreditTransaction.created_at >= current_start)

        rows = await db.execute(breakdown_stmt)
        breakdown_rows = rows.all()

        previous_map: Dict[str, float] = {}
        if previous_start and previous_end:
            previous_stmt = (
                select(
                    CreditTransaction.transaction_type,
                    func.coalesce(func.sum(CreditTransaction.usd_value), 0).label("amount"),
                )
                .where(
                    CreditTransaction.created_at >= previous_start,
                    CreditTransaction.created_at < previous_end,
                )
                .group_by(CreditTransaction.transaction_type)
            )
            try:
                previous_rows = await db.execute(previous_stmt)
                previous_map = {}
                for row in previous_rows.all():
                    txn_type_raw = getattr(row, "transaction_type", None)
                    txn_type = getattr(txn_type_raw, "value", txn_type_raw) or "unknown"
                    previous_map[str(txn_type)] = _decimal_to_float(row.amount)
            except SQLAlchemyError as previous_error:
                logger.warning(
                    "revenue_breakdown_previous_fallback",
                    error=str(previous_error),
                    note="Previous period breakdown unavailable",
                )
                previous_map = {}

        total_amount = sum(_decimal_to_float(getattr(row, "amount", 0)) for row in breakdown_rows) or 1.0

        color_map = {
            CreditTransactionType.PURCHASE.value: "#2563eb",
            CreditTransactionType.USAGE.value: "#16a34a",
            CreditTransactionType.BONUS.value: "#f97316",
            CreditTransactionType.REFUND.value: "#eab308",
            CreditTransactionType.TRANSFER.value: "#9333ea",
            CreditTransactionType.ADJUSTMENT.value: "#0ea5e9",
            CreditTransactionType.EXPIRY.value: "#f43f5e",
        }

        breakdown = []
        for row in breakdown_rows:
            txn_type_raw = getattr(row, "transaction_type", None)
            stream = str(getattr(txn_type_raw, "value", txn_type_raw) or "unknown")
            amount = _decimal_to_float(row.amount)
            percentage = _safe_divide(amount, total_amount) * 100
            previous_amount = previous_map.get(stream, 0.0)
            growth = 0.0
            if previous_amount:
                growth = _safe_divide(amount - previous_amount, previous_amount) * 100

            breakdown.append(
                {
                    "revenue_stream": stream.replace("_", " ").title(),
                    "amount": round(amount, 2),
                    "percentage": round(percentage, 2),
                    "growth": round(growth, 2),
                    "color": color_map.get(stream, "#64748b"),
                }
            )

        breakdown.sort(key=lambda item: item["amount"], reverse=True)
        return {"breakdown": breakdown}

    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("revenue_breakdown_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate revenue breakdown",
        ) from exc


@router.get("/revenue/user-segments")
async def get_revenue_user_segments(
    period: str = "30d",
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database),
):
    """Return revenue contribution by major user segments."""

    await rate_limiter.check_rate_limit(
        key="admin:revenue_segments",
        limit=60,
        window=60,
        user_id=str(current_user.id),
    )

    period_info = _resolve_period(period)
    current_start = period_info.start or (datetime.utcnow() - timedelta(days=30))

    try:
        revenue_stmt = (
            select(
                CreditAccount.user_id,
                func.coalesce(func.sum(CreditTransaction.usd_value), 0).label("revenue"),
            )
            .join(CreditAccount, CreditTransaction.account_id == CreditAccount.id)
            .group_by(CreditAccount.user_id)
        )
        if period_info.start:
            revenue_stmt = revenue_stmt.where(CreditTransaction.created_at >= period_info.start)

        try:
            revenue_rows = await db.execute(revenue_stmt)
            revenue_by_user = _collect_revenue_by_user(revenue_rows.all())
        except SQLAlchemyError as segments_error:
            logger.warning(
                "revenue_segments_fallback",
                error=str(segments_error),
                note="User segment revenue defaults to zero",
            )
            revenue_by_user = {}

        active_ids = (
            await db.execute(select(User.id).where(User.status == UserStatus.ACTIVE))
        ).scalars().all()
        new_ids = (
            await db.execute(select(User.id).where(User.created_at >= current_start))
        ).scalars().all()
        high_value_ids = (
            await db.execute(
                select(CreditAccount.user_id).where(CreditAccount.available_credits >= 500)
            )
        ).scalars().all()
        dormant_ids = (
            await db.execute(select(User.id).where(User.status == UserStatus.INACTIVE))
        ).scalars().all()

        total_users = max(len(active_ids) + len(dormant_ids), 1)

        def _segment_stats(ids: List[Any]) -> Dict[str, float]:
            str_ids = [str(value) for value in ids]
            total_rev = sum(revenue_by_user.get(uid, 0.0) for uid in str_ids)
            count = len(ids)
            avg = _safe_divide(total_rev, count) if count else 0.0
            return {
                "count": count,
                "revenue": total_rev,
                "average": avg,
            }

        active_stats = _segment_stats(active_ids)
        new_stats = _segment_stats(new_ids)
        high_value_stats = _segment_stats(high_value_ids)
        dormant_stats = _segment_stats(dormant_ids)

        segments = [
            {
                "segment": "Active Traders",
                "user_count": active_stats["count"],
                "revenue_contribution": round(active_stats["revenue"], 2),
                "avg_revenue_per_user": round(active_stats["average"], 2),
                "churn_rate": round(_safe_divide(len(dormant_ids), total_users) * 100, 2),
                "growth_rate": round(
                    _safe_divide(len(new_ids), active_stats["count"] or 1) * 100, 2
                ),
            },
            {
                "segment": "New Signups",
                "user_count": new_stats["count"],
                "revenue_contribution": round(new_stats["revenue"], 2),
                "avg_revenue_per_user": round(new_stats["average"], 2),
                "churn_rate": 0.0,
                "growth_rate": 100.0 if new_stats["count"] else 0.0,
            },
            {
                "segment": "High Value",
                "user_count": high_value_stats["count"],
                "revenue_contribution": round(high_value_stats["revenue"], 2),
                "avg_revenue_per_user": round(high_value_stats["average"], 2),
                "churn_rate": round(
                    _safe_divide(dormant_stats["count"], max(high_value_stats["count"], 1))
                    * 100,
                    2,
                ),
                "growth_rate": round(
                    _safe_divide(high_value_stats["count"], total_users) * 100, 2
                ),
            },
            {
                "segment": "Dormant Users",
                "user_count": dormant_stats["count"],
                "revenue_contribution": round(dormant_stats["revenue"], 2),
                "avg_revenue_per_user": round(dormant_stats["average"], 2),
                "churn_rate": round(
                    _safe_divide(dormant_stats["count"], total_users) * 100, 2
                ),
                "growth_rate": round(
                    -_safe_divide(dormant_stats["count"], total_users) * 100, 2
                ),
            },
        ]

        return {"segments": segments}

    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("revenue_segments_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate user segment metrics",
        ) from exc


@router.get("/revenue/geographic")
async def get_revenue_geographic(
    period: str = "30d",
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database),
):
    """Return revenue by geography (country)."""

    await rate_limiter.check_rate_limit(
        key="admin:revenue_geographic",
        limit=60,
        window=60,
        user_id=str(current_user.id),
    )

    period_info = _resolve_period(period)
    start = period_info.start or (datetime.utcnow() - timedelta(days=30))

    try:
        geo_stmt = (
            select(
                UserProfile.country,
                func.count(func.distinct(User.id)).label("user_count"),
                func.coalesce(func.sum(CreditTransaction.usd_value), 0).label("revenue"),
            )
            .join(User, UserProfile.user_id == User.id)
            .join(CreditAccount, CreditAccount.user_id == User.id)
            .join(CreditTransaction, CreditTransaction.account_id == CreditAccount.id)
            .where(UserProfile.country.isnot(None))
            .group_by(UserProfile.country)
        )

        geo_stmt = geo_stmt.where(CreditTransaction.created_at >= start)

        geographic: List[Dict[str, Any]] = []
        try:
            rows = await db.execute(geo_stmt)
            for country, user_count, revenue_value in rows.all():
                revenue = _decimal_to_float(revenue_value)
                geographic.append(
                    {
                        "country": country,
                        "country_code": country,
                        "revenue": round(revenue, 2),
                        "user_count": int(user_count or 0),
                        "avg_revenue_per_user": round(
                            _safe_divide(revenue, user_count or 1), 2
                        ),
                        "growth_rate": 0.0,
                    }
                )
        except SQLAlchemyError as geo_error:
            logger.warning(
                "revenue_geographic_fallback",
                error=str(geo_error),
                note="Returning empty geographic distribution",
            )

        geographic.sort(key=lambda item: item["revenue"], reverse=True)
        return {"geographic": geographic}

    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("revenue_geographic_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate geographic revenue",
        ) from exc


@router.get("/revenue/timeseries")
async def get_revenue_timeseries(
    period: str = "30d",
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database),
):
    """Return revenue time series for charts."""

    await rate_limiter.check_rate_limit(
        key="admin:revenue_timeseries",
        limit=60,
        window=60,
        user_id=str(current_user.id),
    )

    period_info = _resolve_period(period)
    period_days = period_info.duration_days or 30
    start = period_info.start or (datetime.utcnow() - timedelta(days=period_days))

    try:
        timeseries_stmt = (
            select(
                func.date(CreditTransaction.created_at).label("bucket"),
                func.coalesce(func.sum(CreditTransaction.usd_value), 0).label("total_revenue"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                CreditTransaction.transaction_type
                                == CreditTransactionType.USAGE,
                                CreditTransaction.profit_amount_usd,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("profit_share"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                CreditTransaction.transaction_type
                                == CreditTransactionType.PURCHASE,
                                CreditTransaction.usd_value,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("credit_revenue"),
                func.count(CreditTransaction.id).label("transactions"),
            )
            .where(CreditTransaction.created_at >= start)
            .group_by(func.date(CreditTransaction.created_at))
            .order_by(func.date(CreditTransaction.created_at))
        )

        try:
            timeseries_rows = await db.execute(timeseries_stmt)
            timeseries_data = timeseries_rows.all()
        except SQLAlchemyError as timeseries_error:
            logger.warning(
                "revenue_timeseries_fallback",
                error=str(timeseries_error),
                note="Returning empty timeseries due to missing financial data",
            )
            timeseries_data = []

        new_users_rows = await db.execute(
            select(func.date(User.created_at), func.count(User.id))
            .where(User.created_at >= start)
            .group_by(func.date(User.created_at))
        )
        new_users_map = {row[0]: row[1] for row in new_users_rows.all()}

        active_users_total = (
            await db.execute(select(func.count(User.id)).where(User.status == UserStatus.ACTIVE))
        ).scalar_one_or_none() or 0

        timeseries = []
        for bucket, total_revenue, profit_share, credit_revenue, tx_count in timeseries_data:
            bucket_date = bucket.isoformat() if isinstance(bucket, date) else str(bucket)
            timeseries.append(
                {
                    "date": bucket_date,
                    "total_revenue": round(_decimal_to_float(total_revenue), 2),
                    "profit_share_revenue": round(_decimal_to_float(profit_share), 2),
                    "subscription_revenue": 0.0,
                    "one_time_revenue": 0.0,
                    "credit_revenue": round(_decimal_to_float(credit_revenue), 2),
                    "new_users": int(new_users_map.get(bucket, 0)),
                    "active_users": int(active_users_total),
                    "transactions": int(tx_count or 0),
                }
            )

        return {"timeseries": timeseries}

    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("revenue_timeseries_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate revenue timeseries",
        ) from exc


@router.get("/revenue/top-performers")
async def get_revenue_top_performers(
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database),
):
    """Return top performing strategies, publishers, and customers."""

    await rate_limiter.check_rate_limit(
        key="admin:revenue_top_performers",
        limit=60,
        window=60,
        user_id=str(current_user.id),
    )

    try:
        strategies_stmt = (
            select(
                StrategySubmission.id,
                StrategySubmission.name,
                StrategySubmission.total_revenue,
                StrategySubmission.total_subscribers,
                StrategySubmission.user_id,
                StrategySubmission.average_rating,
                User.email,
                UserProfile.first_name,
                UserProfile.last_name,
            )
            .join(User, User.id == StrategySubmission.user_id)
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .where(
                StrategySubmission.status.in_([
                    StrategyStatus.APPROVED,
                    StrategyStatus.PUBLISHED,
                ])
            )
            .order_by(StrategySubmission.total_revenue.desc())
            .limit(5)
        )

        strategy_rows = await db.execute(strategies_stmt)
        strategies = []
        for row in strategy_rows.all():
            strategies.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "publisher": row.first_name or row.email.split("@")[0],
                    "revenue": round(_decimal_to_float(row.total_revenue), 2),
                    "users": int(row.total_subscribers or 0),
                    "growth_rate": 0.0,
                }
            )

        publisher_stmt = (
            select(
                StrategySubmission.user_id,
                func.coalesce(func.sum(StrategySubmission.total_revenue), 0).label("total_revenue"),
                func.count(StrategySubmission.id).label("total_strategies"),
                func.coalesce(func.avg(StrategySubmission.average_rating), 0).label("avg_rating"),
                StrategyPublisher.display_name,
                User.email,
            )
            .outerjoin(StrategyPublisher, StrategyPublisher.user_id == StrategySubmission.user_id)
            .join(User, User.id == StrategySubmission.user_id)
            .where(
                StrategySubmission.status.in_([
                    StrategyStatus.APPROVED,
                    StrategyStatus.PUBLISHED,
                ])
            )
            .group_by(
                StrategySubmission.user_id,
                StrategyPublisher.display_name,
                User.email,
            )
            .order_by(desc("total_revenue"))
            .limit(5)
        )

        publisher_rows = await db.execute(publisher_stmt)
        publishers = []
        for row in publisher_rows.all():
            publishers.append(
                {
                    "id": str(row.user_id),
                    "name": row.display_name or row.email.split("@")[0],
                    "total_revenue": round(_decimal_to_float(row.total_revenue), 2),
                    "total_strategies": int(row.total_strategies or 0),
                    "avg_rating": round(_decimal_to_float(row.avg_rating), 2),
                    "growth_rate": 0.0,
                }
            )

        try:
            customer_revenue_rows = await db.execute(
                select(
                    CreditAccount.user_id,
                    func.coalesce(func.sum(CreditTransaction.usd_value), 0).label("revenue"),
                )
                .join(CreditAccount, CreditTransaction.account_id == CreditAccount.id)
                .group_by(CreditAccount.user_id)
            )
            revenue_by_user = _collect_revenue_by_user(customer_revenue_rows.all())
        except SQLAlchemyError as customer_error:
            logger.warning(
                "revenue_top_performers_customer_fallback",
                error=str(customer_error),
                note="Customer revenue defaults to zero",
            )
            revenue_by_user = {}
        top_user_ids = [user_id for user_id, _ in sorted(
            revenue_by_user.items(), key=lambda item: item[1], reverse=True
        )[:5]]

        active_access_rows = await db.execute(
            select(UserStrategyAccess.user_id, func.count(UserStrategyAccess.id))
            .where(UserStrategyAccess.is_active == True)
            .group_by(UserStrategyAccess.user_id)
        )
        active_access_map = {
            str(row[0]): int(row[1]) for row in active_access_rows.all()
        }

        customers: List[Dict[str, Any]] = []
        if top_user_ids:
            user_uuid_tuple = tuple(UUID(user_id) for user_id in top_user_ids)
            user_rows = await db.execute(
                select(User, UserProfile)
                .outerjoin(UserProfile, UserProfile.user_id == User.id)
                .where(User.id.in_(user_uuid_tuple))
            )
            user_map = {str(user.id): (user, profile) for user, profile in user_rows.all()}

            for user_id in top_user_ids:
                user, profile = user_map.get(user_id, (None, None))
                if not user:
                    continue
                name = (
                    profile.full_name
                    if profile and profile.full_name
                    else user.email.split("@")[0]
                )
                customers.append(
                    {
                        "id": user_id,
                        "name": name,
                        "total_spent": round(revenue_by_user.get(user_id, 0.0), 2),
                        "active_strategies": active_access_map.get(user_id, 0),
                        "join_date": user.created_at.isoformat() if user.created_at else None,
                        "lifetime_value": round(revenue_by_user.get(user_id, 0.0), 2),
                    }
                )

        return {
            "strategies": strategies,
            "publishers": publishers,
            "users": customers,
        }

    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("revenue_top_performers_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate top performers",
        ) from exc


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
        from app.services.strategy_submission_service import strategy_submission_service

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

            # Validate credit amount is non-negative
            if request.credit_amount < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Credit amount must be non-negative"
                )

            # Get or create credit account using ledger helper that handles dialect-specific locking
            credit_account = await credit_ledger.get_account(
                db,
                target_user.id,
                for_update=True,
                create_if_missing=True,
                initial_credits=0,
            )

            current_balance = int(credit_account.available_credits or 0)
            target_balance = int(request.credit_amount)
            delta = target_balance - current_balance

            # Generate reference_id for audit/idempotency
            reference_id = str(uuid.uuid4())

            metadata = {
                "requested_by": current_user.email,
                "reason": request.reason,
                "target_balance": target_balance,
                "reference_id": reference_id,
            }

            if delta > 0:
                await credit_ledger.add_credits(
                    db,
                    credit_account,
                    credits=delta,
                    transaction_type=CreditTransactionType.ADJUSTMENT,
                    description=f"Admin credit reset increase by {current_user.email}",
                    source="admin_console",
                    provider="admin_console",
                    reference_id=reference_id,
                    metadata=metadata,
                    track_lifetime=False,
                )
            elif delta < 0:
                try:
                    await credit_ledger.consume_credits(
                        db,
                        credit_account,
                        credits=abs(delta),
                        description=f"Admin credit reset decrease by {current_user.email}",
                        source="admin_console",
                        transaction_type=CreditTransactionType.ADJUSTMENT,
                        metadata=metadata,
                        track_usage=False,
                    )
                except InsufficientCreditsError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot reduce credits below zero",
                    ) from e

            action_taken = f"Credits set to {target_balance}"
        
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


# Strategy Approval functionality - integrated into main admin router


# Strategy Approval Models
class ReviewStatsResponse(BaseModel):
    total_pending: int
    under_review: int
    approved_today: int
    rejected_today: int
    avg_review_time_hours: int
    my_assigned: int


class StrategyReviewRequest(BaseModel):
    action: str  # "approve", "reject", "request_changes"
    comment: Optional[str] = None

    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        allowed_actions = ["approve", "reject", "request_changes"]
        if v.lower() not in allowed_actions:
            raise ValueError(f"Action must be one of: {allowed_actions}")
        return v.lower()


class StrategyAssignmentRequest(BaseModel):
    reviewer_id: Optional[str] = None


# Strategy Approval Endpoints
@router.get("/strategies/review-stats")
async def get_strategy_review_stats(
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Get strategy review statistics."""

    await rate_limiter.check_rate_limit(
        key="admin:review_stats",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )

    try:
        stats = await strategy_submission_service.get_review_stats(
            db=db,
            reviewer=current_user
        )

        return ReviewStatsResponse(
            total_pending=stats.total_pending,
            under_review=stats.under_review,
            approved_today=stats.approved_today,
            rejected_today=stats.rejected_today,
            avg_review_time_hours=stats.avg_review_time_hours,
            my_assigned=stats.my_assigned
        )

    except Exception as e:
        logger.exception("Strategy review stats retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get strategy review stats"
        ) from e


@router.get("/strategies/pending")
async def get_pending_strategies(
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Get strategies pending approval."""

    await rate_limiter.check_rate_limit(
        key="admin:pending_strategies",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )

    try:
        pending_strategies = await strategy_submission_service.get_pending_submissions(
            db=db,
            status_filter=status_filter
        )

        return {
            "strategies": pending_strategies,
            "total_count": len(pending_strategies),
            "status": "success"
        }

    except Exception as e:
        logger.exception("Pending strategies retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pending strategies"
        ) from e


@router.post("/strategies/{submission_id}/assign")
async def assign_strategy_submission(
    submission_id: str,
    request: StrategyAssignmentRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Assign a strategy submission to a reviewer."""

    await rate_limiter.check_rate_limit(
        key="admin:assign_strategy",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )

    try:
        reviewer = current_user
        if request.reviewer_id:
            try:
                reviewer_uuid = UUID(request.reviewer_id)
            except (ValueError, TypeError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid reviewer_id"
                ) from exc

            reviewer_instance = await db.get(User, reviewer_uuid)
            if not reviewer_instance:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Reviewer not found"
                )
            reviewer = reviewer_instance

        submission = await strategy_submission_service.assign_submission(
            submission_id=submission_id,
            reviewer=reviewer,
            db=db
        )

        return {
            "status": "success",
            "message": "Strategy submission assigned",
            "submission_id": submission_id,
            "reviewer": reviewer.email,
            "status_value": submission.status.value
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.exception("Strategy assignment failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign strategy"
        ) from e


@router.post("/strategies/{strategy_id}/review")
async def review_strategy(
    strategy_id: str,
    request: StrategyReviewRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_database)
):
    """Review a strategy (approve, reject, or request changes)."""

    await rate_limiter.check_rate_limit(
        key="admin:review_strategy",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )

    try:
        submission = await strategy_submission_service.review_submission(
            submission_id=strategy_id,
            reviewer=current_user,
            action=request.action,
            comment=request.comment,
            db=db
        )

        logger.info(
            "Strategy submission review processed",
            submission_id=strategy_id,
            reviewer=str(current_user.id),
            action=request.action
        )

        return {
            "status": "success",
            "message": f"Strategy has been {request.action.replace('_', ' ')}d successfully",
            "action": request.action,
            "submission_id": submission.id,
            "reviewer": current_user.email,
            "timestamp": datetime.utcnow().isoformat(),
            "status_value": submission.status.value,
            "published_strategy_id": (submission.strategy_config or {}).get("published_strategy_id")
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.exception("Strategy review failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to review strategy"
        ) from e

@router.get("/signals/deliveries", response_model=List[SignalDeliveryAudit])
async def admin_signal_deliveries(
    limit: int = Query(100, ge=1, le=500),
    channel_slug: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
) -> List[SignalDeliveryAudit]:
    stmt = (
        select(
            SignalDeliveryLog,
            SignalChannel.slug,
            SignalSubscription.user_id,
        )
        .join(SignalSubscription, SignalDeliveryLog.subscription_id == SignalSubscription.id)
        .join(SignalChannel, SignalSubscription.channel_id == SignalChannel.id)
        .order_by(SignalDeliveryLog.delivered_at.desc())
        .limit(limit)
    )
    if channel_slug:
        stmt = stmt.where(SignalChannel.slug == channel_slug)
    if status_filter:
        stmt = stmt.where(SignalDeliveryLog.status == status_filter)

    result = await db.execute(stmt)
    records = result.all()

    return [
        SignalDeliveryAudit(
            delivery_id=delivery.id,
            channel_slug=slug,
            user_id=user_id,
            delivery_channel=delivery.delivery_channel,
            status=delivery.status,
            credit_cost=delivery.credit_cost,
            delivered_at=delivery.delivered_at,
            acknowledged_at=delivery.acknowledged_at,
            executed_at=delivery.executed_at,
            metadata=delivery.metadata or {},
            payload=delivery.payload or {},
        )
        for delivery, slug, user_id in records
    ]


# ============================================================================
# SYSTEM DIAGNOSTICS & LOGS
# ============================================================================

@router.get("/system/logs")
async def get_system_logs(
    lines: int = Query(100, ge=1, le=1000, description="Number of log lines to retrieve"),
    service: Optional[str] = Query(None, description="Filter by service name (background, signal, etc)"),
    level: Optional[str] = Query(None, description="Filter by log level (INFO, WARNING, ERROR)"),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """
    Retrieve recent system logs for debugging.

    This endpoint reads structured logs from memory/file system for admin diagnostics.
    Useful for debugging background services without direct server access.
    """
    await rate_limiter.check_rate_limit(
        key="admin:system_logs",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )

    try:
        import os
        import json
        from collections import deque

        logs = []

        # Try to read from log file if it exists
        log_file_paths = [
            "/var/log/cryptouniverse.log",
            "./logs/app.log",
            "./cryptouniverse.log",
        ]

        log_file = None
        for path in log_file_paths:
            if os.path.exists(path):
                log_file = path
                break

        if log_file:
            # Read last N lines from log file
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Use deque for efficient tail reading
                all_lines = deque(f, maxlen=lines * 2)  # Get more than needed for filtering

                for line in all_lines:
                    try:
                        # Try to parse as JSON (structlog format)
                        log_entry = json.loads(line.strip())

                        # Apply filters
                        if service and service.lower() not in str(log_entry.get('event', '')).lower():
                            continue
                        if level and log_entry.get('level', '').upper() != level.upper():
                            continue

                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # Plain text log line
                        if service and service.lower() not in line.lower():
                            continue
                        if level and level.upper() not in line.upper():
                            continue

                        logs.append({
                            "timestamp": None,
                            "level": "UNKNOWN",
                            "event": line.strip(),
                            "format": "plain"
                        })

                    if len(logs) >= lines:
                        break
        else:
            # No log file found - return in-memory logs captured from stdout
            in_memory_logs = get_recent_logs(lines * 2)
            for log_entry in in_memory_logs:
                if service and service.lower() not in str(log_entry.get('event', '')).lower():
                    continue
                if level and log_entry.get('level', '').upper() != level.upper():
                    continue
                logs.append(log_entry)

            if not logs:
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "WARNING",
                    "event": "No log file found. Streaming recent in-memory logs returned zero entries.",
                    "log_paths_checked": log_file_paths
                })

        return {
            "success": True,
            "log_file": log_file,
            "logs": logs[-lines:],  # Return last N logs
            "total_returned": len(logs[-lines:]),
            "filters": {
                "service": service,
                "level": level,
                "lines": lines
            }
        }

    except Exception as e:
        logger.exception("Failed to retrieve system logs")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve logs: {str(e)}"
        )


@router.get("/system/background-services")
async def get_background_services_detailed(
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """
    Get detailed status of all background services including startup info.

    This provides diagnostic information about:
    - Which services are running
    - Service startup times
    - Last execution times
    - Error counts
    - Configuration intervals
    - Service effectiveness metrics (e.g., symbols discovered, signals sent, users synced)
    """
    await rate_limiter.check_rate_limit(
        key="admin:background_services",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )

    try:
        # Get health check from background manager
        services_health = await background_manager.health_check()

        # Get system metrics which includes service info
        system_metrics = await background_manager.get_system_metrics()

        # Get detailed status for each service
        service_details = {}
        for service_name in background_manager.intervals.keys():
            try:
                detail = await background_manager.get_service_status(service_name)

                # Get service effectiveness metrics
                metrics = await background_manager.get_service_metrics(service_name)

                service_details[service_name] = {
                    "status": services_health.get(service_name, "not_started"),
                    "interval_seconds": background_manager.intervals.get(service_name, 0),
                    "details": detail,
                    "metrics": metrics  # Include effectiveness metrics
                }
            except Exception as e:
                service_details[service_name] = {
                    "status": "error",
                    "error": str(e)
                }

        return {
            "success": True,
            "uptime_hours": system_metrics.get("uptime_hours", 0),
            "services": service_details,
            "services_summary": {
                "total": len(service_details),
                "running": sum(1 for s in service_details.values() if s.get("status") == "running"),
                "stopped": sum(1 for s in service_details.values() if s.get("status") in ["stopped", "not_started"]),
                "error": sum(1 for s in service_details.values() if s.get("status") == "error"),
            },
            "intervals": background_manager.intervals,
            "redis_available": system_metrics.get("active_connections", 0) > 0,
        }

    except Exception as e:
        logger.exception("Failed to retrieve background services status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve services status: {str(e)}"
        )
