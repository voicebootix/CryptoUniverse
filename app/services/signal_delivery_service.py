"""Coordinated signal delivery across chat, Telegram, and webhook channels."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.credit import CreditTransactionType
from app.models.signal import SignalChannel, SignalDeliveryLog, SignalSubscription
from app.models.telegram_integration import UserTelegramConnection
from app.models.user import User
from app.services.credit_ledger import credit_ledger
from app.services.signal_channel_service import (
    ChannelPlan,
    SignalChannelService,
    signal_channel_service,
)
from app.services.signal_evaluation_service import (
    SignalEvaluationService,
    signal_evaluation_service,
)
from app.services.system_monitoring import system_monitoring_service
from app.services.telegram_core import telegram_commander_service
from app.services.websocket import manager as websocket_manager

logger = structlog.get_logger(__name__)
settings = get_settings()


class SignalDeliveryService:
    """Enterprise delivery pipeline for evaluated signals."""

    def __init__(
        self,
        *,
        channel_service: SignalChannelService = signal_channel_service,
        evaluation_service: SignalEvaluationService = signal_evaluation_service,
    ) -> None:
        self.logger = logger
        self.channel_service = channel_service
        self.evaluation_service = evaluation_service

    async def dispatch_channel(
        self,
        db: AsyncSession,
        *,
        channel: SignalChannel,
        subscriptions: Sequence[SignalSubscription],
        user_map: Dict[str, User],
    ) -> List[SignalDeliveryLog]:
        """Evaluate a channel once per subscription and deliver signals."""

        deliveries: List[SignalDeliveryLog] = []
        for subscription in subscriptions:
            user = user_map.get(str(subscription.user_id))
            if not user:
                continue

            try:
                subscription_deliveries = await self.dispatch_subscription(
                    db,
                    channel=channel,
                    subscription=subscription,
                    user=user,
                )
                deliveries.extend(subscription_deliveries)
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Signal delivery failed",
                    subscription_id=str(subscription.id),
                    channel_slug=channel.slug,
                    error=str(exc),
                )
        return deliveries

    async def dispatch_subscription(
        self,
        db: AsyncSession,
        *,
        channel: SignalChannel,
        subscription: SignalSubscription,
        user: User,
    ) -> List[SignalDeliveryLog]:
        """Evaluate and deliver a signal for a single subscription."""

        evaluation = await self.evaluation_service.evaluate(
            db,
            channel=channel,
            subscription=subscription,
            user=user,
            symbols=None,
        )
        event = evaluation.event
        subscription.last_event_at = datetime.utcnow()
        await db.flush()

        plan = self.channel_service.get_plan(channel, subscription.billing_plan)
        cost, transaction_id = await self._debit_per_signal(
            db,
            subscription=subscription,
            channel=channel,
            plan=plan,
            event_id=event.id,
        )

        preferred_channels = subscription.preferred_channels or channel.delivery_channels or []
        deliveries: List[SignalDeliveryLog] = []
        charged = False

        for medium in preferred_channels:
            delivery_log = await self._deliver_to_medium(
                db,
                medium=medium,
                subscription=subscription,
                user=user,
                event_payload=evaluation.pipeline_result,
                summary=event.summary,
                channel=channel,
                event_id=event.id,
                credit_transaction_id=transaction_id,
                credit_cost=cost if not charged else 0,
            )
            if delivery_log:
                db.add(delivery_log)
                deliveries.append(delivery_log)
                charged = charged or delivery_log.credit_cost > 0

        await db.flush()

        system_monitoring_service.metrics_collector.record_metric(
            "signal_delivery_count",
            float(len(deliveries)),
            {"channel": channel.slug},
        )

        return deliveries

    async def _deliver_to_medium(
        self,
        db: AsyncSession,
        *,
        medium: str,
        subscription: SignalSubscription,
        user: User,
        event_payload: Dict[str, Any],
        summary: str,
        channel: SignalChannel,
        event_id,
        credit_transaction_id: Optional[str],
        credit_cost: int,
    ) -> Optional[SignalDeliveryLog]:
        medium = medium.lower()
        if medium == "telegram":
            return await self._deliver_telegram(
                db,
                subscription=subscription,
                user=user,
                event_payload=event_payload,
                summary=summary,
                channel=channel,
                event_id=event_id,
                credit_transaction_id=credit_transaction_id,
                credit_cost=credit_cost,
            )
        if medium == "chat":
            return await self._deliver_chat(
                subscription=subscription,
                user=user,
                event_payload=event_payload,
                summary=summary,
                channel=channel,
                event_id=event_id,
                credit_transaction_id=credit_transaction_id,
                credit_cost=credit_cost,
            )
        if medium == "api" and subscription.webhook_url:
            return await self._deliver_webhook(
                subscription=subscription,
                event_payload=event_payload,
                summary=summary,
                channel=channel,
                event_id=event_id,
                webhook_url=subscription.webhook_url,
                credit_transaction_id=credit_transaction_id,
                credit_cost=credit_cost,
            )

        self.logger.debug(
            "Unsupported delivery medium or missing configuration",
            medium=medium,
            subscription_id=str(subscription.id),
        )
        return None

    async def _deliver_telegram(
        self,
        db: AsyncSession,
        *,
        subscription: SignalSubscription,
        user: User,
        event_payload: Dict[str, Any],
        summary: str,
        channel: SignalChannel,
        event_id,
        credit_transaction_id: Optional[str],
        credit_cost: int,
    ) -> Optional[SignalDeliveryLog]:
        connection = await self._get_active_telegram_connection(db, user_id=user.id)
        if not connection:
            self.logger.info(
                "Telegram delivery skipped: no active connection",
                user_id=str(user.id),
            )
            return None

        message = self._render_message(summary, event_payload, channel)
        response = await telegram_commander_service.send_direct_message(
            chat_id=connection.telegram_chat_id,
            message_content=message,
            message_type="alert",
            priority="high",
        )
        status = "delivered" if response.get("success") else "failed"
        error_message = None if response.get("success") else response.get("error")

        return SignalDeliveryLog(
            event_id=event_id,
            subscription_id=subscription.id,
            delivery_channel="telegram",
            status=status,
            error_message=error_message,
            payload={"message": message, "response": response},
            credit_cost=credit_cost,
            credit_transaction_id=credit_transaction_id,
            metadata={
                "telegram_chat_id": connection.telegram_chat_id,
            },
        )

    async def _deliver_chat(
        self,
        *,
        subscription: SignalSubscription,
        user: User,
        event_payload: Dict[str, Any],
        summary: str,
        channel: SignalChannel,
        event_id,
        credit_transaction_id: Optional[str],
        credit_cost: int,
    ) -> SignalDeliveryLog:
        message = {
            "type": "signal_delivery",
            "summary": summary,
            "channel": channel.slug,
            "payload": event_payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await websocket_manager.broadcast(message, user_id=str(user.id))

        log_entry = SignalDeliveryLog(
            event_id=event_id,
            subscription_id=subscription.id,
            delivery_channel="chat",
            status="delivered",
            payload=message,
            credit_cost=credit_cost,
            credit_transaction_id=credit_transaction_id,
            metadata={"websocket": True},
        )
        return log_entry

    async def _deliver_webhook(
        self,
        *,
        subscription: SignalSubscription,
        event_payload: Dict[str, Any],
        summary: str,
        channel: SignalChannel,
        event_id,
        webhook_url: str,
        credit_transaction_id: Optional[str],
        credit_cost: int,
    ) -> SignalDeliveryLog:
        payload = {
            "event_id": str(event_id),
            "subscription_id": str(subscription.id),
            "channel": channel.slug,
            "summary": summary,
            "payload": event_payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        headers = {
            "Content-Type": "application/json",
        }
        signature = self._sign_payload(payload)
        if signature:
            headers["X-Signature"] = signature

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(webhook_url, content=json.dumps(payload), headers=headers)
        status = "delivered" if response.status_code < 400 else "failed"

        log_entry = SignalDeliveryLog(
            event_id=event_id,
            subscription_id=subscription.id,
            delivery_channel="api",
            status=status,
            error_message=None if status == "delivered" else response.text,
            payload=payload,
            credit_cost=credit_cost,
            credit_transaction_id=credit_transaction_id,
            metadata={"status_code": response.status_code},
        )
        return log_entry

    async def _get_active_telegram_connection(
        self, db: AsyncSession, *, user_id
    ) -> Optional[UserTelegramConnection]:
        stmt = (
            select(UserTelegramConnection)
            .where(
                UserTelegramConnection.user_id == user_id,
                UserTelegramConnection.is_active.is_(True),
                UserTelegramConnection.notifications_enabled.is_(True),
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    def _render_message(self, summary: str, payload: Dict[str, Any], channel: SignalChannel) -> str:
        validation = payload.get("phases", {}).get("phase_4", {})
        confidence = validation.get("consensus_confidence")
        phase_2 = payload.get("phases", {}).get("phase_2", {})
        symbol = phase_2.get("symbol", "-")
        action = phase_2.get("action", "HOLD")
        price_hint = phase_2.get("entry_price") or phase_2.get("price")
        parts = [
            f"📡 *{channel.name}*",
            summary,
            f"Action: {action} {symbol}",
        ]
        if price_hint:
            parts.append(f"Entry: {price_hint}")
        if confidence is not None:
            parts.append(f"Confidence: {confidence}%")
        parts.append("Respond with /execute to run via autopilot or acknowledge to log completion.")
        return "\n".join(parts)

    async def _debit_per_signal(
        self,
        db: AsyncSession,
        *,
        subscription: SignalSubscription,
        channel: SignalChannel,
        plan: ChannelPlan,
        event_id,
    ) -> Tuple[int, Optional[str]]:
        if plan.per_signal_credits <= 0:
            return 0, None

        account = await credit_ledger.get_account(db, subscription.user_id, create_if_missing=True)
        transaction = await credit_ledger.consume_credits(
            db,
            account,
            credits=plan.per_signal_credits,
            description=f"Signal delivery for {channel.name}",
            source="signals",
            metadata={
                "channel_id": str(channel.id),
                "subscription_id": str(subscription.id),
                "event_id": str(event_id),
                "plan": plan.name,
            },
            transaction_type=CreditTransactionType.USAGE,
        )
        return plan.per_signal_credits, str(transaction.id)

    def _sign_payload(self, payload: Dict[str, Any]) -> Optional[str]:
        secret = getattr(settings, "SIGNALS_WEBHOOK_SECRET", None)
        if not secret:
            return None
        serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        digest = hmac.new(secret.encode(), serialized, hashlib.sha256).hexdigest()
        return digest


signal_delivery_service = SignalDeliveryService()
