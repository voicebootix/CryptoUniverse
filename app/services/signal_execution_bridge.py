"""Bridge translating delivery acknowledgements and executions into core systems."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import SignalDeliveryLog, SignalEvent
from app.models.user import User
from app.services.master_controller import MasterSystemController
from app.services.system_monitoring import system_monitoring_service

logger = structlog.get_logger(__name__)


class SignalExecutionBridge:
    """Handles acknowledgement and execution follow-ups for delivered signals."""

    def __init__(self, controller: Optional[MasterSystemController] = None) -> None:
        self.controller = controller or MasterSystemController()
        self.logger = logger

    async def acknowledge(
        self,
        db: AsyncSession,
        *,
        delivery_log: SignalDeliveryLog,
        actor: str,
    ) -> SignalDeliveryLog:
        event = await self._ensure_event_context(db, delivery_log)
        delivery_log.acknowledged_at = datetime.utcnow()
        metadata = dict(delivery_log.metadata or {})
        acknowledgements = metadata.setdefault("acknowledgements", [])
        acknowledgements.append({
            "actor": actor,
            "timestamp": delivery_log.acknowledged_at.isoformat(),
        })
        delivery_log.metadata = metadata
        await db.flush()

        system_monitoring_service.metrics_collector.record_metric(
            "signal_acknowledgements",
            1.0,
            {
                "channel": event.channel.slug if event and event.channel else "unknown",
            },
        )

        return delivery_log

    async def execute(
        self,
        db: AsyncSession,
        *,
        delivery_log: SignalDeliveryLog,
        user: User,
        execution_mode: str = "autonomous",
    ) -> Dict[str, Any]:
        if delivery_log.executed_at:
            return {
                "status": "already_executed",
                "execution_reference": delivery_log.execution_reference,
            }

        event = await self._ensure_event_context(db, delivery_log)
        if not event:
            raise ValueError("Delivery log is not associated with a signal event")

        symbols = event.metadata.get("symbols") or []
        result = await self.controller.execute_5_phase_autonomous_cycle(
            user_id=str(user.id),
            source=f"signal_execution:{event.channel.slug if event.channel else event.channel_id}",
            symbols=symbols,
            analysis_only=False,
            risk_tolerance=event.risk_band,
        )

        delivery_log.executed_at = datetime.utcnow()
        delivery_log.execution_reference = result.get("cycle_id")
        metadata = dict(delivery_log.metadata or {})
        metadata.setdefault("execution_mode", execution_mode)
        metadata["execution_result"] = result
        delivery_log.metadata = metadata
        await db.flush()

        system_monitoring_service.metrics_collector.record_metric(
            "signal_executions",
            1.0,
            {"channel": event.channel.slug if event.channel else "unknown"},
        )

        self.logger.info(
            "Signal execution triggered",
            delivery_id=str(delivery_log.id),
            user_id=str(user.id),
            execution_reference=delivery_log.execution_reference,
        )

        return result

    async def _ensure_event_context(
        self, db: AsyncSession, delivery_log: SignalDeliveryLog
    ) -> Optional[SignalEvent]:
        """Ensure the associated event and channel are loaded for the delivery log."""

        await db.refresh(delivery_log, attribute_names=["event"])
        event = delivery_log.event
        if event is not None:
            await db.refresh(event, attribute_names=["channel"])
        return event


signal_execution_bridge = SignalExecutionBridge()
