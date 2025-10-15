"""Signal intelligence management endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_database
from app.models.signal import SignalDeliveryLog, SignalEvent, SignalSubscription
from app.models.user import User
from app.schemas.signal import (
    SignalChannelListResponse,
    SignalChannelOut,
    SignalDeliveryAction,
    SignalDeliveryActionResponse,
    SignalDeliveryListResponse,
    SignalDeliveryOut,
    SignalEventListResponse,
    SignalEventOut,
    SignalSubscriptionCreate,
    SignalSubscriptionResponse,
    SignalSubscriptionSummary,
)
from app.services.signal_channel_service import (
    SignalAccessError,
    SignalChannelService,
    SignalSubscriptionError,
    signal_channel_service,
)
from app.services.signal_execution_bridge import signal_execution_bridge
from app.services.signal_performance_service import signal_performance_service
from app.services.signal_backtesting_service import signal_backtesting_service
from app.services.system_monitoring import system_monitoring_service

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/signals", tags=["signals"])


def _serialize_subscription(subscription: SignalSubscription) -> SignalSubscriptionSummary:
    return SignalSubscriptionSummary(
        id=subscription.id,
        is_active=subscription.is_active,
        autopilot_enabled=subscription.autopilot_enabled,
        preferred_channels=subscription.preferred_channels or [],
        billing_plan=subscription.billing_plan,
        reserved_credits=subscription.reserved_credits,
        webhook_url=subscription.webhook_url,
        last_event_at=subscription.last_event_at,
    )


def _serialize_channel(data: Dict[str, Any]) -> SignalChannelOut:
    subscription = None
    if data.get("active_subscription"):
        subscription = SignalSubscriptionSummary(**data["active_subscription"])
    return SignalChannelOut(
        id=data["id"],
        name=data["name"],
        slug=data["slug"],
        description=data["description"],
        risk_profile=data["risk_profile"],
        cadence_minutes=data["cadence_minutes"],
        max_daily_events=data["max_daily_events"],
        autopilot_supported=data["autopilot_supported"],
        min_credit_balance=data["min_credit_balance"],
        required_strategy_ids=data["required_strategy_ids"],
        delivery_channels=data["delivery_channels"],
        pricing=data["pricing"],
        configuration=data["configuration"],
        active_subscription=subscription,
    )


def _serialize_event(event: SignalEvent) -> SignalEventOut:
    return SignalEventOut(
        id=event.id,
        channel_id=event.channel_id,
        summary=event.summary,
        confidence=float(event.confidence or 0),
        risk_band=event.risk_band,
        opportunity_payload=event.opportunity_payload or {},
        triggered_at=event.triggered_at,
    )


def _serialize_delivery(log: SignalDeliveryLog) -> SignalDeliveryOut:
    return SignalDeliveryOut(
        id=log.id,
        event_id=log.event_id,
        subscription_id=log.subscription_id,
        delivery_channel=log.delivery_channel,
        status=log.status,
        credit_cost=log.credit_cost,
        delivered_at=log.delivered_at,
        acknowledged_at=log.acknowledged_at,
        executed_at=log.executed_at,
        execution_reference=log.execution_reference,
    )


@router.get("/channels", response_model=SignalChannelListResponse)
async def list_signal_channels(
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
    channel_service: SignalChannelService = Depends(lambda: signal_channel_service),
) -> SignalChannelListResponse:
    """Return active channels along with the caller's subscription status."""

    channel_dicts = await channel_service.list_channels(db, current_user)
    channels = [_serialize_channel(channel) for channel in channel_dicts]
    return SignalChannelListResponse(channels=channels)


@router.post("/subscribe", response_model=SignalSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def subscribe_to_channel(
    request: SignalSubscriptionCreate,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
    channel_service: SignalChannelService = Depends(lambda: signal_channel_service),
) -> SignalSubscriptionResponse:
    """Subscribe the authenticated user to a signal channel."""

    channel = await channel_service.get_channel(db, request.channel_id)
    if not channel or not channel.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    try:
        subscription = await channel_service.subscribe(
            db,
            user=current_user,
            channel=channel,
            preferred_channels=request.preferred_channels,
            billing_plan=request.billing_plan,
            autopilot_enabled=request.autopilot_enabled,
            webhook_url=str(request.webhook_url) if request.webhook_url else None,
        )
    except SignalAccessError as exc:
        logger.warning("signal_subscription_access_denied", error=str(exc), user_id=str(current_user.id))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SignalSubscriptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return SignalSubscriptionResponse(subscription=_serialize_subscription(subscription))


@router.get("/events", response_model=SignalEventListResponse)
async def list_signal_events(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
) -> SignalEventListResponse:
    stmt = (
        select(SignalEvent)
        .join(SignalSubscription, SignalEvent.generated_for_subscription_id == SignalSubscription.id)
        .where(SignalSubscription.user_id == current_user.id)
        .order_by(SignalEvent.triggered_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    events = result.scalars().all()
    return SignalEventListResponse(events=[_serialize_event(event) for event in events])


@router.get("/deliveries", response_model=SignalDeliveryListResponse)
async def list_signal_deliveries(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
) -> SignalDeliveryListResponse:
    stmt = (
        select(SignalDeliveryLog)
        .join(SignalSubscription, SignalDeliveryLog.subscription_id == SignalSubscription.id)
        .where(SignalSubscription.user_id == current_user.id)
        .order_by(SignalDeliveryLog.delivered_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    deliveries = result.scalars().all()
    return SignalDeliveryListResponse(deliveries=[_serialize_delivery(delivery) for delivery in deliveries])


@router.post("/deliveries/{delivery_id}/acknowledge", response_model=SignalDeliveryActionResponse)
async def acknowledge_delivery(
    delivery_id: UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
) -> SignalDeliveryActionResponse:
    delivery_log = await _get_user_delivery(db, delivery_id, current_user)
    await signal_execution_bridge.acknowledge(db, delivery_log=delivery_log, actor=str(current_user.id))
    return SignalDeliveryActionResponse(result={"status": "acknowledged"})


@router.post("/deliveries/{delivery_id}/execute", response_model=SignalDeliveryActionResponse)
async def execute_delivery(
    delivery_id: UUID,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
) -> SignalDeliveryActionResponse:
    delivery_log = await _get_user_delivery(db, delivery_id, current_user)
    result = await signal_execution_bridge.execute(
        db,
        delivery_log=delivery_log,
        user=current_user,
        execution_mode="manual",
    )
    return SignalDeliveryActionResponse(result=result)


@router.post("/webhook/acknowledge", response_model=SignalDeliveryActionResponse)
async def webhook_acknowledge(
    action: SignalDeliveryAction,
    db: AsyncSession = Depends(get_database),
) -> SignalDeliveryActionResponse:
    await _verify_signature({"delivery_id": str(action.delivery_id)}, action.signature)
    delivery_log = await _get_delivery(db, action.delivery_id)
    await signal_execution_bridge.acknowledge(db, delivery_log=delivery_log, actor="webhook")
    return SignalDeliveryActionResponse(result={"status": "acknowledged"})


@router.post("/webhook/execute", response_model=SignalDeliveryActionResponse)
async def webhook_execute(
    action: SignalDeliveryAction,
    db: AsyncSession = Depends(get_database),
) -> SignalDeliveryActionResponse:
    await _verify_signature({"delivery_id": str(action.delivery_id)}, action.signature)
    delivery_log = await _get_delivery(db, action.delivery_id)

    # Avoid async lazy-loads; fetch user explicitly
    result = await db.execute(
        select(User)
        .join(SignalSubscription, SignalSubscription.user_id == User.id)
        .where(SignalSubscription.id == delivery_log.subscription_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found for delivery")

    result = await signal_execution_bridge.execute(
        db,
        delivery_log=delivery_log,
        user=user,
        execution_mode="webhook",
    )
    return SignalDeliveryActionResponse(result=result)


async def _get_user_delivery(
    db: AsyncSession,
    delivery_id: UUID,
    user: User,
) -> SignalDeliveryLog:
    stmt = (
        select(SignalDeliveryLog)
        .join(SignalSubscription, SignalDeliveryLog.subscription_id == SignalSubscription.id)
        .where(
            SignalDeliveryLog.id == delivery_id,
            SignalSubscription.user_id == user.id,
        )
    )
    result = await db.execute(stmt)
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    return delivery


async def _get_delivery(db: AsyncSession, delivery_id: UUID) -> SignalDeliveryLog:
    result = await db.execute(select(SignalDeliveryLog).where(SignalDeliveryLog.id == delivery_id))
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    return delivery


async def _verify_signature(payload: Dict[str, str], signature: Optional[str]) -> None:
    secret = settings.SIGNALS_WEBHOOK_SECRET
    if not secret:
        # Fail closed: webhook secret must be configured
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured"
        )
    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")

    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    expected = hmac.new(secret.encode(), serialized, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")


# ============================================================================
# SIGNAL CONFIGURATION ENDPOINTS
# ============================================================================

@router.post("/channels/{channel_id}/configure")
async def configure_channel(
    channel_id: UUID,
    config: Dict[str, Any],
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Configure signal channel settings.

    Body:
    {
        "symbols": ["BTC/USDT", "ETH/USDT"],  // Optional: custom symbols
        "timeframe": "1h",  // Optional: 5m, 15m, 1h, 4h, 1d
        "autopilot_enabled": true,  // Optional: enable autopilot
        "max_daily_events": 12,  // Optional: max signals per day
        "preferred_channels": ["telegram", "chat"]  // Optional: delivery channels
    }
    """
    from app.models.signal import SignalChannel, SignalSubscription

    # Get channel
    channel = await db.get(SignalChannel, channel_id)
    if not channel or not channel.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    # Get subscription
    sub_stmt = (
        select(SignalSubscription)
        .where(SignalSubscription.user_id == current_user.id)
        .where(SignalSubscription.channel_id == channel_id)
    )
    subscription = (await db.execute(sub_stmt)).scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be subscribed to configure this channel"
        )

    # Store per-subscription overrides (do not modify channel configuration)
    sub_metadata = subscription.metadata or {}

    if "symbols" in config:
        symbols = config["symbols"]
        if not isinstance(symbols, list):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="symbols must be a list")
        sub_metadata["override_symbols"] = symbols

    if "timeframe" in config:
        timeframe = config["timeframe"]
        valid_timeframes = ["5m", "15m", "1h", "4h", "1d"]
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
            )
        sub_metadata["override_timeframe"] = timeframe

    subscription.metadata = sub_metadata

    # Update subscription settings
    if "autopilot_enabled" in config:
        subscription.autopilot_enabled = bool(config["autopilot_enabled"])

    if "max_daily_events" in config:
        max_events = config["max_daily_events"]
        if not isinstance(max_events, int) or max_events < 1 or max_events > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_daily_events must be between 1 and 50"
            )
        subscription.max_daily_events = max_events

    if "preferred_channels" in config:
        channels = config["preferred_channels"]
        if not isinstance(channels, list):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="preferred_channels must be a list")
        subscription.preferred_channels = channels

    await db.commit()

    return {
        "success": True,
        "channel_id": str(channel_id),
        "subscription": {
            "autopilot_enabled": subscription.autopilot_enabled,
            "max_daily_events": subscription.max_daily_events,
            "preferred_channels": subscription.preferred_channels,
            "override_symbols": sub_metadata.get("override_symbols"),
            "override_timeframe": sub_metadata.get("override_timeframe"),
        }
    }


@router.get("/performance")
async def get_all_performance(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get performance metrics for all signal channels.

    Returns win rate, profit metrics, and quality scores.
    """
    performances = await signal_performance_service.get_all_channel_performance(db, days=days)

    return {
        "success": True,
        "timeframe_days": days,
        "channels": [
            {
                "channel_id": str(perf.channel_id),
                "channel_name": perf.channel_name,
                "total_signals": perf.total_signals,
                "completed_signals": perf.completed_signals,
                "win_count": perf.win_count,
                "loss_count": perf.loss_count,
                "pending_count": perf.pending_count,
                "win_rate": perf.win_rate,
                "avg_profit_pct": perf.avg_profit_pct,
                "avg_win_pct": perf.avg_win_pct,
                "avg_loss_pct": perf.avg_loss_pct,
                "best_signal_pct": perf.best_signal_pct,
                "worst_signal_pct": perf.worst_signal_pct,
                "quality_score": perf.quality_score,
            }
            for perf in performances
        ]
    }


@router.get("/performance/{channel_id}")
async def get_channel_performance(
    channel_id: UUID,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get detailed performance metrics for a specific channel.
    """
    try:
        perf = await signal_performance_service.get_channel_performance(db, channel_id, days=days)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return {
        "success": True,
        "channel_id": str(perf.channel_id),
        "channel_name": perf.channel_name,
        "timeframe_days": perf.timeframe_days,
        "total_signals": perf.total_signals,
        "completed_signals": perf.completed_signals,
        "win_count": perf.win_count,
        "loss_count": perf.loss_count,
        "pending_count": perf.pending_count,
        "win_rate": perf.win_rate,
        "avg_profit_pct": perf.avg_profit_pct,
        "avg_win_pct": perf.avg_win_pct,
        "avg_loss_pct": perf.avg_loss_pct,
        "best_signal_pct": perf.best_signal_pct,
        "worst_signal_pct": perf.worst_signal_pct,
        "quality_score": perf.quality_score,
    }


@router.get("/history")
async def get_signal_history(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get signal history for the current user.

    Returns past signals with their outcomes and performance.
    """
    history = await signal_performance_service.get_user_signal_history(
        db, current_user.id, limit=limit
    )

    return {
        "success": True,
        "count": len(history),
        "signals": history
    }


@router.get("/monitoring")
async def get_signal_monitoring(
    duration_minutes: int = Query(60, ge=5, le=1440),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get signal generation and delivery monitoring metrics.

    Returns metrics about empty signal generation, delivery failures, and alerts.
    Admin-only endpoint for operational monitoring.
    """
    # Check if user is admin (you may want to add a proper admin check)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Get signal-specific metrics
    signal_metrics = {}
    for metric_name in [
        "signal_generation_empty",
        "signal_delivery_failed_all",
        "signal_delivery_telegram_failed",
        "signal_delivery_webhook_failed",
        "signal_delivery_count",
        "signal_evaluation_confidence",
    ]:
        summary = system_monitoring_service.metrics_collector.get_metric_summary(
            metric_name,
            duration_minutes=duration_minutes
        )
        if "error" not in summary:
            signal_metrics[metric_name] = summary

    # Get active alerts related to signals
    all_alerts = system_monitoring_service.get_active_alerts()
    signal_alerts = [
        alert for alert in all_alerts
        if "signal_" in alert["message"].lower()
    ]

    return {
        "success": True,
        "duration_minutes": duration_minutes,
        "metrics": signal_metrics,
        "alerts": {
            "signal_related": signal_alerts,
            "count": len(signal_alerts),
        },
        "thresholds": {
            k: v for k, v in system_monitoring_service.thresholds.items()
            if k.startswith("signal_")
        },
    }


@router.post("/backtest")
async def backtest_strategy(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Backtest a signal strategy against historical data.

    Body:
    {
        "strategy_type": "momentum",  // momentum, breakout, mean_reversion, scalping
        "symbols": ["BTC/USDT", "ETH/USDT"],
        "timeframe": "1h",  // Optional: default 1h
        "days_back": 30,  // Optional: default 30
        "start_date": "2024-01-01",  // Optional: ISO format
        "end_date": "2024-12-31"  // Optional: ISO format
    }
    """
    strategy_type = request.get("strategy_type")
    symbols = request.get("symbols", [])
    timeframe = request.get("timeframe", "1h")
    days_back = request.get("days_back", 30)
    start_date = request.get("start_date")
    end_date = request.get("end_date")

    if not strategy_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="strategy_type is required")

    valid_strategies = ["momentum", "breakout", "mean_reversion", "scalping"]
    if strategy_type not in valid_strategies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid strategy_type. Must be one of: {', '.join(valid_strategies)}"
        )

    if not symbols:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="symbols is required")

    # Run backtest
    result = await signal_backtesting_service.backtest_strategy(
        strategy_type=strategy_type,
        symbols=symbols,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        days_back=days_back,
    )

    return {
        "success": True,
        "backtest": {
            "strategy_type": result.strategy_type,
            "symbols": result.symbols,
            "timeframe": result.timeframe,
            "start_date": result.start_date,
            "end_date": result.end_date,
            "total_trades": result.total_trades,
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
            "win_rate": result.win_rate,
            "total_return_pct": result.total_return_pct,
            "avg_win_pct": result.avg_win_pct,
            "avg_loss_pct": result.avg_loss_pct,
            "best_trade_pct": result.best_trade_pct,
            "worst_trade_pct": result.worst_trade_pct,
            "profit_factor": result.profit_factor,
            "sharpe_ratio": result.sharpe_ratio,
            "max_drawdown_pct": result.max_drawdown_pct,
            "trades": [
                {
                    "entry_time": trade.entry_time.isoformat(),
                    "exit_time": trade.exit_time.isoformat(),
                    "symbol": trade.symbol,
                    "action": trade.action,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "profit_pct": trade.profit_pct,
                    "outcome": trade.outcome,
                    "reason": trade.reason,
                }
                for trade in result.trades
            ]
        }
    }
