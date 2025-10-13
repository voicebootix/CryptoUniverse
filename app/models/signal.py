"""Signal intelligence models supporting enterprise delivery."""

import uuid
from typing import List

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SignalChannel(Base):
    """Channel definition describing how signals are produced and priced."""

    __tablename__ = "signal_channels"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    risk_profile = Column(String(40), nullable=False, default="balanced")
    cadence_minutes = Column(Integer, nullable=False, default=15)
    max_daily_events = Column(Integer, nullable=False, default=12)
    autopilot_supported = Column(Boolean, nullable=False, default=True)
    min_credit_balance = Column(Integer, nullable=False, default=0)
    required_strategy_ids = Column(JSONB, nullable=False, default=list)
    delivery_channels = Column(JSONB, nullable=False, default=list)
    pricing = Column(JSONB, nullable=False, default=dict)
    configuration = Column(JSONB, nullable=False, default=dict)
    metadata = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    subscriptions = relationship(
        "SignalSubscription",
        back_populates="channel",
        cascade="all, delete-orphan",
    )
    events = relationship(
        "SignalEvent",
        back_populates="channel",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_signal_channels_active", "is_active"),
        Index("idx_signal_channels_cadence", "cadence_minutes"),
    )

    def allows_channel(self, channel: str) -> bool:
        delivery_channels: List[str] = self.delivery_channels or []
        return channel in delivery_channels


class SignalSubscription(Base):
    """User subscription to a channel including billing context."""

    __tablename__ = "signal_subscriptions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("signal_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True)
    autopilot_enabled = Column(Boolean, nullable=False, default=False)
    preferred_channels = Column(JSONB, nullable=False, default=list)
    billing_plan = Column(String(50), nullable=False, default="standard")
    reserved_credits = Column(Integer, nullable=False, default=0)
    webhook_url = Column(String(512), nullable=True)
    max_daily_events = Column(Integer, nullable=False, default=12)
    cadence_override_minutes = Column(Integer, nullable=True)
    metadata = Column(JSONB, nullable=False, default=dict)
    last_event_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    channel = relationship("SignalChannel", back_populates="subscriptions")
    user = relationship("User", back_populates="signal_subscriptions")
    deliveries = relationship(
        "SignalDeliveryLog",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("channel_id", "user_id", name="uq_signal_subscription"),
        Index("idx_signal_subscription_user", "user_id", "is_active"),
        Index("idx_signal_subscription_channel", "channel_id", "is_active"),
    )


class SignalEvent(Base):
    """Discrete evaluated signal ready for delivery."""

    __tablename__ = "signal_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("signal_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generated_for_subscription_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("signal_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    triggered_at = Column(DateTime, nullable=False, server_default=func.now())
    summary = Column(Text, nullable=False)
    confidence = Column(Numeric(5, 2), nullable=False, default=0)
    risk_band = Column(String(32), nullable=False, default="balanced")
    opportunity_payload = Column(JSONB, nullable=False, default=dict)
    analysis_snapshot = Column(JSONB, nullable=False, default=dict)
    metadata = Column(JSONB, nullable=False, default=dict)
    created_by_user_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Performance tracking fields
    actual_outcome = Column(String(32), nullable=True)  # "win", "loss", "pending", "skipped"
    actual_profit_pct = Column(Numeric(10, 4), nullable=True)
    closed_at = Column(DateTime, nullable=True)
    close_price = Column(Numeric(20, 8), nullable=True)

    channel = relationship("SignalChannel", back_populates="events")
    subscription = relationship("SignalSubscription")
    deliveries = relationship(
        "SignalDeliveryLog",
        back_populates="event",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_signal_events_channel_time", "channel_id", "triggered_at"),
        Index("idx_signal_events_subscription", "generated_for_subscription_id"),
        Index("idx_signal_events_outcome", "actual_outcome"),
    )


class SignalDeliveryLog(Base):
    """Audit log capturing each delivery attempt and acknowledgement."""

    __tablename__ = "signal_delivery_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("signal_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("signal_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    delivery_channel = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=False, default=dict)
    credit_cost = Column(Integer, nullable=False, default=0)
    credit_transaction_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("credit_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    delivered_at = Column(DateTime, nullable=False, server_default=func.now())
    acknowledged_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    execution_reference = Column(String(255), nullable=True)
    metadata = Column(JSONB, nullable=False, default=dict)

    event = relationship("SignalEvent", back_populates="deliveries")
    subscription = relationship("SignalSubscription", back_populates="deliveries")

    __table_args__ = (
        Index("idx_signal_delivery_channel", "delivery_channel", "status"),
        Index("idx_signal_delivery_time", "delivered_at"),
        Index("idx_signal_delivery_credit", "credit_transaction_id"),
    )
