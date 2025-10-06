"""Signal intelligence management endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict, Optional
from uuid import UUID

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
    user = delivery_log.subscription.user
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
        # No secret configured, treat as disabled verification.
        return
    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")

    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    expected = hmac.new(secret.encode(), serialized, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
