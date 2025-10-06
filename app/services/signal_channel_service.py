"""Service managing signal intelligence channels and subscriptions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credit import CreditTransactionType
from app.models.signal import SignalChannel, SignalSubscription
from app.models.strategy_access import UserStrategyAccess
from app.models.user import User
from app.services.credit_ledger import credit_ledger, InsufficientCreditsError

logger = structlog.get_logger(__name__)


class SignalAccessError(Exception):
    """Raised when a user lacks required strategy entitlements."""


class SignalSubscriptionError(Exception):
    """Raised when subscription provisioning fails."""


@dataclass(frozen=True)
class ChannelPlan:
    """Pricing metadata for a signal channel billing plan."""

    name: str
    reservation_credits: int
    per_signal_credits: int


DEFAULT_CHANNEL_DEFINITIONS: Sequence[Dict[str, Any]] = (
    {
        "slug": "momentum-alpha",
        "name": "Momentum Alpha Signals",
        "description": "Momentum and mean-reversion blend covering BTC, ETH, SOL and complementary majors.",
        "risk_profile": "balanced",
        "cadence_minutes": 20,
        "max_daily_events": 12,
        "autopilot_supported": True,
        "min_credit_balance": 150,
        "required_strategy_ids": [
            "ai_spot_momentum_strategy",
            "ai_spot_mean_reversion",
        ],
        "delivery_channels": ["telegram", "chat", "api"],
        "pricing": {
            "plans": {
                "standard": {"reservation_credits": 100, "per_signal": 5},
                "enterprise": {"reservation_credits": 250, "per_signal": 3},
            }
        },
        "configuration": {
            "default_symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            "minimum_confidence": 65,
            "timeframe": "1h",
        },
    },
    {
        "slug": "breakout-pro",
        "name": "Breakout Pro",
        "description": "High velocity breakout confirmations with protective risk envelopes across top futures pairs.",
        "risk_profile": "aggressive",
        "cadence_minutes": 15,
        "max_daily_events": 18,
        "autopilot_supported": True,
        "min_credit_balance": 300,
        "required_strategy_ids": [
            "ai_spot_breakout_strategy",
            "ai_scalping_strategy",
        ],
        "delivery_channels": ["telegram", "chat", "api"],
        "pricing": {
            "plans": {
                "standard": {"reservation_credits": 200, "per_signal": 8},
                "enterprise": {"reservation_credits": 400, "per_signal": 6},
            }
        },
        "configuration": {
            "default_symbols": ["BTC/USDT", "ETH/USDT", "AVAX/USDT", "ARB/USDT"],
            "minimum_confidence": 70,
            "timeframe": "15m",
        },
    },
)


class SignalChannelService:
    """Enterprise orchestration around signal channels and subscriptions."""

    def __init__(self) -> None:
        self.logger = logger

    async def seed_default_channels(self, db: AsyncSession) -> None:
        """Ensure default channels exist so onboarding works day one."""

        result = await db.execute(select(SignalChannel.slug))
        existing_slugs = {row[0] for row in result}

        created = False
        for definition in DEFAULT_CHANNEL_DEFINITIONS:
            if definition["slug"] in existing_slugs:
                continue

            channel = SignalChannel(
                name=definition["name"],
                slug=definition["slug"],
                description=definition["description"],
                risk_profile=definition.get("risk_profile", "balanced"),
                cadence_minutes=definition.get("cadence_minutes", 15),
                max_daily_events=definition.get("max_daily_events", 12),
                autopilot_supported=definition.get("autopilot_supported", True),
                min_credit_balance=definition.get("min_credit_balance", 0),
                required_strategy_ids=definition.get("required_strategy_ids", []),
                delivery_channels=definition.get("delivery_channels", []),
                pricing=definition.get("pricing", {}),
                configuration=definition.get("configuration", {}),
            )
            db.add(channel)
            created = True

        if created:
            await db.flush()
            self.logger.info("Default signal channels seeded", slugs=list(existing_slugs))

    async def list_channels(self, db: AsyncSession, user: User) -> List[Dict[str, Any]]:
        """Return channels with subscription state for the requesting user."""

        await self.seed_default_channels(db)

        channels_result = await db.execute(
            select(SignalChannel).where(SignalChannel.is_active.is_(True)).order_by(SignalChannel.name)
        )
        channels = channels_result.scalars().all()

        subscriptions_result = await db.execute(
            select(SignalSubscription).where(SignalSubscription.user_id == user.id)
        )
        subscription_map = {sub.channel_id: sub for sub in subscriptions_result.scalars().all()}

        return [self._serialize_channel(channel, subscription_map.get(channel.id)) for channel in channels]

    async def get_channel_by_slug(self, db: AsyncSession, slug: str) -> Optional[SignalChannel]:
        result = await db.execute(select(SignalChannel).where(SignalChannel.slug == slug))
        return result.scalar_one_or_none()

    async def get_channel(self, db: AsyncSession, channel_id: UUID) -> Optional[SignalChannel]:
        result = await db.execute(
            select(SignalChannel).where(SignalChannel.id == channel_id)
        )
        return result.scalar_one_or_none()

    async def subscribe(
        self,
        db: AsyncSession,
        *,
        user: User,
        channel: SignalChannel,
        preferred_channels: Optional[Sequence[str]] = None,
        billing_plan: str = "standard",
        autopilot_enabled: bool = False,
        webhook_url: Optional[str] = None,
    ) -> SignalSubscription:
        """Provision or reactivate a subscription with entitlement and credit validation."""

        existing_result = await db.execute(
            select(SignalSubscription).where(
                SignalSubscription.channel_id == channel.id,
                SignalSubscription.user_id == user.id,
            )
        )
        existing_subscription = existing_result.scalar_one_or_none()
        if existing_subscription and existing_subscription.is_active:
            raise SignalSubscriptionError("Subscription is already active for this channel")

        await self._validate_entitlements(db, user, channel)
        await self._validate_credit_balance(db, user, channel)

        preferred = list(preferred_channels or channel.delivery_channels or [])
        if not preferred:
            raise SignalSubscriptionError("At least one delivery channel must be selected")

        invalid_channels = [value for value in preferred if not channel.allows_channel(value)]
        if invalid_channels:
            raise SignalSubscriptionError(
                f"Channel does not support delivery medium(s): {', '.join(invalid_channels)}"
            )

        plan = self._resolve_plan(channel, billing_plan)
        reservation_id = None
        reserved_credits = 0
        if plan.reservation_credits > 0:
            reservation_id, reserved_credits = await self._reserve_credits(
                db,
                user=user,
                channel=channel,
                plan=plan,
            )

        reactivated = existing_subscription is not None

        if existing_subscription:
            metadata = dict(existing_subscription.metadata or {})
            if reservation_id:
                metadata["reservation_transaction_id"] = reservation_id
            metadata["reactivated_at"] = datetime.utcnow().isoformat()

            existing_subscription.is_active = True
            existing_subscription.autopilot_enabled = autopilot_enabled
            existing_subscription.preferred_channels = preferred
            existing_subscription.billing_plan = plan.name
            existing_subscription.reserved_credits = reserved_credits
            existing_subscription.webhook_url = webhook_url
            existing_subscription.max_daily_events = channel.max_daily_events
            existing_subscription.metadata = metadata
            existing_subscription.updated_at = datetime.utcnow()
            subscription = existing_subscription
        else:
            metadata = {"provisioned_at": datetime.utcnow().isoformat()}
            if reservation_id:
                metadata["reservation_transaction_id"] = reservation_id

            subscription = SignalSubscription(
                channel_id=channel.id,
                user_id=user.id,
                is_active=True,
                autopilot_enabled=autopilot_enabled,
                preferred_channels=preferred,
                billing_plan=plan.name,
                reserved_credits=reserved_credits,
                webhook_url=webhook_url,
                max_daily_events=channel.max_daily_events,
                metadata=metadata,
            )
            db.add(subscription)

        await db.flush()

        log_message = "Signal subscription reactivated" if reactivated else "Signal subscription provisioned"
        self.logger.info(
            log_message,
            user_id=str(user.id),
            channel_slug=channel.slug,
            billing_plan=plan.name,
            reserved_credits=reserved_credits,
        )

        return subscription

    async def unsubscribe(self, db: AsyncSession, subscription: SignalSubscription) -> None:
        """Deactivate a subscription and release reserved credits."""

        subscription.is_active = False
        subscription.updated_at = datetime.utcnow()
        await db.flush()

        # Credits are released by creating a compensating transaction.
        if subscription.reserved_credits > 0:
            account = await credit_ledger.get_account(db, subscription.user_id, create_if_missing=True)
            await credit_ledger.add_credits(
                db,
                account,
                credits=subscription.reserved_credits,
                transaction_type=CreditTransactionType.REFUND,
                description=f"Release reserved credits for signal channel {subscription.channel_id}",
                source="signals",
                metadata={
                    "channel_id": str(subscription.channel_id),
                    "subscription_id": str(subscription.id),
                    "reason": "unsubscribe",
                },
            )
            subscription.reserved_credits = 0

        self.logger.info(
            "Signal subscription deactivated",
            subscription_id=str(subscription.id),
            user_id=str(subscription.user_id),
        )

    async def _validate_entitlements(self, db: AsyncSession, user: User, channel: SignalChannel) -> None:
        if not channel.required_strategy_ids:
            return

        stmt = (
            select(UserStrategyAccess.strategy_id)
            .where(
                and_(
                    UserStrategyAccess.user_id == user.id,
                    UserStrategyAccess.strategy_id.in_(channel.required_strategy_ids),
                    UserStrategyAccess.is_active.is_(True),
                )
            )
        )
        result = await db.execute(stmt)
        owned = {row[0] for row in result}

        missing = [strategy for strategy in channel.required_strategy_ids if strategy not in owned]
        if missing:
            raise SignalAccessError(
                "Missing required strategy access: " + ", ".join(sorted(missing))
            )

    async def _validate_credit_balance(
        self,
        db: AsyncSession,
        user: User,
        channel: SignalChannel,
    ) -> None:
        account = await credit_ledger.get_account(
            db,
            user.id,
            create_if_missing=True,
        )
        available = int(account.available_credits or 0)
        if available < channel.min_credit_balance:
            raise SignalSubscriptionError(
                f"Insufficient credits. Required minimum {channel.min_credit_balance}, available {available}."
            )

    async def _reserve_credits(
        self,
        db: AsyncSession,
        *,
        user: User,
        channel: SignalChannel,
        plan: ChannelPlan,
    ) -> Tuple[Optional[str], int]:
        account = await credit_ledger.get_account(db, user.id, create_if_missing=True)
        try:
            transaction = await credit_ledger.consume_credits(
                db,
                account,
                credits=plan.reservation_credits,
                description=f"Reservation for {channel.name} ({plan.name})",
                source="signals",
                metadata={
                    "channel_id": str(channel.id),
                    "channel_slug": channel.slug,
                    "plan": plan.name,
                    "reservation": True,
                },
                transaction_type=CreditTransactionType.RESERVATION,
            )
        except InsufficientCreditsError as exc:
            raise SignalSubscriptionError(str(exc)) from exc

        return str(transaction.id), plan.reservation_credits

    def _resolve_plan(self, channel: SignalChannel, billing_plan: str) -> ChannelPlan:
        plans = (channel.pricing or {}).get("plans", {})
        if billing_plan not in plans:
            if not plans:
                return ChannelPlan(name="standard", reservation_credits=0, per_signal_credits=0)
            billing_plan = next(iter(plans.keys()))

        plan_data = plans[billing_plan]
        return ChannelPlan(
            name=billing_plan,
            reservation_credits=int(plan_data.get("reservation_credits", 0)),
            per_signal_credits=int(plan_data.get("per_signal", 0)),
        )

    def get_plan(self, channel: SignalChannel, billing_plan: str) -> ChannelPlan:
        """Expose plan resolution for downstream services."""

        return self._resolve_plan(channel, billing_plan)

    def _serialize_channel(
        self,
        channel: SignalChannel,
        subscription: Optional[SignalSubscription],
    ) -> Dict[str, Any]:
        plans = (channel.pricing or {}).get("plans", {})
        return {
            "id": str(channel.id),
            "name": channel.name,
            "slug": channel.slug,
            "description": channel.description,
            "risk_profile": channel.risk_profile,
            "cadence_minutes": channel.cadence_minutes,
            "max_daily_events": channel.max_daily_events,
            "autopilot_supported": channel.autopilot_supported,
            "min_credit_balance": channel.min_credit_balance,
            "required_strategy_ids": channel.required_strategy_ids or [],
            "delivery_channels": channel.delivery_channels or [],
            "pricing": plans,
            "configuration": channel.configuration or {},
            "active_subscription": None
            if not subscription
            else {
                "id": str(subscription.id),
                "is_active": subscription.is_active,
                "autopilot_enabled": subscription.autopilot_enabled,
                "preferred_channels": subscription.preferred_channels or [],
                "billing_plan": subscription.billing_plan,
                "reserved_credits": subscription.reserved_credits,
                "webhook_url": subscription.webhook_url,
                "last_event_at": subscription.last_event_at.isoformat()
                if subscription.last_event_at
                else None,
            },
        }


signal_channel_service = SignalChannelService()
