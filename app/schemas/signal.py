"""Pydantic schemas for signal intelligence operations."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, conlist


class SignalSubscriptionSummary(BaseModel):
    id: UUID
    is_active: bool
    autopilot_enabled: bool
    preferred_channels: List[str]
    billing_plan: str
    reserved_credits: int
    webhook_url: Optional[HttpUrl] = None
    last_event_at: Optional[datetime] = None


class SignalChannelOut(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str
    risk_profile: str
    cadence_minutes: int
    max_daily_events: int
    autopilot_supported: bool
    min_credit_balance: int
    required_strategy_ids: List[str]
    delivery_channels: List[str]
    pricing: dict
    configuration: dict
    active_subscription: Optional[SignalSubscriptionSummary] = None


class SignalChannelListResponse(BaseModel):
    success: bool = True
    channels: List[SignalChannelOut]


class SignalSubscriptionCreate(BaseModel):
    channel_id: UUID
    preferred_channels: conlist(str, min_length=1)  # type: ignore[arg-type]
    billing_plan: str = Field("standard", max_length=50)
    autopilot_enabled: bool = False
    webhook_url: Optional[HttpUrl] = None


class SignalSubscriptionResponse(BaseModel):
    success: bool = True
    subscription: SignalSubscriptionSummary


class SignalEventOut(BaseModel):
    id: UUID
    channel_id: UUID
    summary: str
    confidence: float
    risk_band: str
    opportunity_payload: dict
    triggered_at: datetime


class SignalEventListResponse(BaseModel):
    success: bool = True
    events: List[SignalEventOut]


class SignalDeliveryOut(BaseModel):
    id: UUID
    event_id: UUID
    subscription_id: UUID
    delivery_channel: str
    status: str
    credit_cost: int
    delivered_at: datetime
    acknowledged_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    execution_reference: Optional[str] = None


class SignalDeliveryListResponse(BaseModel):
    success: bool = True
    deliveries: List[SignalDeliveryOut]


class SignalDeliveryAction(BaseModel):
    delivery_id: UUID
    signature: Optional[str] = None


class SignalDeliveryActionResponse(BaseModel):
    success: bool = True
    result: dict
