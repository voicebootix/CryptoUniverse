"""Service executing the five-phase pipeline for signal generation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import SignalChannel, SignalEvent, SignalSubscription
from app.models.user import User
from app.services.master_controller import MasterSystemController
from app.services.system_monitoring import system_monitoring_service

logger = structlog.get_logger(__name__)


@dataclass
class EvaluationResult:
    """Lightweight container for returning evaluation output."""

    event: SignalEvent
    pipeline_result: Dict[str, Any]


class SignalEvaluationError(Exception):
    """Raised when the evaluation pipeline fails."""


class SignalEvaluationService:
    """Wraps the master controller pipeline in analysis-only mode."""

    def __init__(self, controller: Optional[MasterSystemController] = None) -> None:
        self._controller = controller or MasterSystemController()
        self.logger = logger

    async def evaluate(
        self,
        db: AsyncSession,
        *,
        channel: SignalChannel,
        subscription: Optional[SignalSubscription],
        user: Optional[User],
        symbols: Optional[Sequence[str]] = None,
    ) -> EvaluationResult:
        """Execute the five-phase pipeline and persist the resulting event."""

        source = f"signal:{channel.slug}"
        user_id = str(user.id) if user else "system"

        self.logger.info(
            "Running signal evaluation",
            channel=channel.slug,
            user_id=user_id,
            symbols=list(symbols) if symbols else None,
        )

        pipeline_result = await self._controller.execute_5_phase_autonomous_cycle(
            user_id=user_id,
            source=source,
            symbols=list(symbols) if symbols else None,
            analysis_only=True,
            risk_tolerance=channel.risk_profile,
        )

        if not pipeline_result.get("success"):
            raise SignalEvaluationError(
                f"Pipeline execution failed for channel {channel.slug}: {pipeline_result}"
            )

        summary = self._build_summary(pipeline_result, channel)
        confidence = self._extract_confidence(pipeline_result)
        risk_band = self._determine_risk_band(pipeline_result, channel)
        opportunity_payload = self._extract_opportunity_payload(pipeline_result)

        event = SignalEvent(
            channel_id=channel.id,
            generated_for_subscription_id=subscription.id if subscription else None,
            summary=summary,
            confidence=Decimal(str(confidence)),
            risk_band=risk_band,
            opportunity_payload=opportunity_payload,
            analysis_snapshot=pipeline_result,
            metadata={
                "source": source,
                "symbols": list(symbols) if symbols else channel.configuration.get("default_symbols", []),
            },
            created_by_user_id=user.id if user else None,
        )
        db.add(event)
        await db.flush()

        # Record metrics for observability
        execution_time = float(pipeline_result.get("execution_time_ms", 0))
        system_monitoring_service.metrics_collector.record_metric(
            "signal_evaluation_latency_ms",
            execution_time,
            {"channel": channel.slug},
        )
        system_monitoring_service.metrics_collector.record_metric(
            "signal_evaluation_confidence",
            confidence,
            {"channel": channel.slug},
        )

        self.logger.info(
            "Signal evaluation complete",
            channel=channel.slug,
            user_id=user_id,
            confidence=confidence,
            risk_band=risk_band,
        )

        return EvaluationResult(event=event, pipeline_result=pipeline_result)

    def _build_summary(self, pipeline_result: Dict[str, Any], channel: SignalChannel) -> str:
        phase_2 = pipeline_result.get("phases", {}).get("phase_2", {})
        phase_3 = pipeline_result.get("phases", {}).get("phase_3", {})
        symbol = phase_2.get("symbol", "-")
        action = phase_2.get("action", "HOLD")
        position_size = phase_3.get("position_size_usd", 0)
        return (
            f"{channel.name}: {action} {symbol} with position size ${position_size:,.2f}."
            " Confidence and risk metrics attached."
        )

    def _extract_confidence(self, pipeline_result: Dict[str, Any]) -> float:
        phase_4 = pipeline_result.get("phases", {}).get("phase_4", {})
        confidence = phase_4.get("consensus_confidence")
        if confidence is None:
            confidence = pipeline_result.get("phases", {}).get("phase_2", {}).get("confidence", 0)
        return float(confidence or 0)

    def _determine_risk_band(
        self, pipeline_result: Dict[str, Any], channel: SignalChannel
    ) -> str:
        risk_metrics = pipeline_result.get("phases", {}).get("phase_3", {})
        risk_score = risk_metrics.get("risk_score")
        if risk_score is None:
            return channel.risk_profile
        if risk_score < 0.02:
            return "conservative"
        if risk_score < 0.05:
            return "balanced"
        return "aggressive"

    def _extract_opportunity_payload(self, pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
        phases = pipeline_result.get("phases", {})
        return {
            "market": phases.get("phase_1", {}),
            "signal": phases.get("phase_2", {}),
            "position": phases.get("phase_3", {}),
            "validation": phases.get("phase_4", {}),
        }


signal_evaluation_service = SignalEvaluationService()
