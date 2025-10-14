"""Service using technical analysis engine for signal generation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import SignalChannel, SignalEvent, SignalSubscription
from app.models.user import User
from app.services.signal_generation_engine import signal_generation_engine, TechnicalSignal
from app.services.system_monitoring import system_monitoring_service

logger = structlog.get_logger(__name__)


@dataclass
class EvaluationResult:
    """Lightweight container for returning evaluation output."""

    event: SignalEvent
    signal: TechnicalSignal


class SignalEvaluationError(Exception):
    """Raised when the evaluation pipeline fails."""


class SignalEvaluationService:
    """
    NEW IMPLEMENTATION: Uses dedicated signal generation engine.

    NO LONGER uses execute_5_phase_autonomous_cycle.
    Generates proper technical analysis signals instead.
    """

    def __init__(self) -> None:
        self.engine = signal_generation_engine
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
        """
        Generate signal using technical analysis engine.

        This is called by signal_delivery_service for each subscription.
        But signals are actually batch-generated and cached!
        """

        source = f"signal:{channel.slug}"
        user_id = str(user.id) if user else "system"

        self.logger.info(
            "Evaluating signal for subscription",
            channel=channel.slug,
            user_id=user_id,
            symbols=list(symbols) if symbols else None,
        )

        # Get configuration
        config = channel.configuration or {}

        # Check for per-subscription overrides first
        sub_metadata = {}
        if subscription and subscription.metadata:
            sub_metadata = subscription.metadata if isinstance(subscription.metadata, dict) else {}

        # Priority: subscription override > passed symbols > channel default
        override_symbols = sub_metadata.get("override_symbols")
        if override_symbols:
            # Normalize override_symbols to list
            if isinstance(override_symbols, str):
                target_symbols = [override_symbols]
            elif isinstance(override_symbols, list):
                target_symbols = override_symbols
            else:
                target_symbols = []
        elif symbols:
            target_symbols = list(symbols)
        else:
            target_symbols = config.get("default_symbols", [])

        # Priority: subscription override > channel config > default
        timeframe = sub_metadata.get("override_timeframe") or config.get("timeframe", "1h")

        # Generate batch signals (cached for 15 minutes)
        batch_signals = await self.engine.generate_batch_signals(
            symbols=target_symbols if target_symbols else None,
            timeframe=timeframe,
        )

        # Filter signals by channel's required strategies
        filtered_signals = batch_signals.get_by_strategy(channel.required_strategy_ids or [])

        if not filtered_signals:
            # Record empty signal generation for monitoring
            system_monitoring_service.metrics_collector.record_metric(
                "signal_generation_empty",
                1.0,
                {
                    "channel": channel.slug,
                    "timeframe": timeframe,
                    "strategies": str(channel.required_strategy_ids),
                },
            )
            self.logger.warning(
                "No signals generated for channel",
                channel=channel.slug,
                required_strategies=channel.required_strategy_ids,
                timeframe=timeframe,
                symbols=target_symbols,
            )
            raise SignalEvaluationError(
                f"No signals generated for channel {channel.slug} with required strategies"
            )

        # Pick best signal (highest confidence)
        best_signal = sorted(filtered_signals, key=lambda s: s.confidence, reverse=True)[0]

        # Build opportunity payload from technical signal
        opportunity_payload = {
            "symbol": best_signal.symbol,
            "action": best_signal.action,
            "entry_price": best_signal.entry_price,
            "stop_loss": best_signal.stop_loss,
            "take_profit": best_signal.take_profit,
            "indicators": best_signal.indicators,
            "reasoning": best_signal.reasoning,
            "risk_score": best_signal.risk_score,
            "timeframe": best_signal.timeframe,
            "strategy_type": best_signal.strategy_type,
        }

        summary = self._build_summary(best_signal, channel)

        event = SignalEvent(
            channel_id=channel.id,
            generated_for_subscription_id=subscription.id if subscription else None,
            summary=summary,
            confidence=Decimal(str(best_signal.confidence)),
            risk_band=channel.risk_profile,  # Use channel risk profile
            opportunity_payload=opportunity_payload,
            analysis_snapshot={
                "source": "technical_analysis",
                "engine_version": "1.0.0",
                "all_signals_count": len(filtered_signals),
                "timestamp": best_signal.timestamp.isoformat(),
            },
            metadata={
                "source": source,
                "symbols": [best_signal.symbol],
                "timeframe": timeframe,
                "strategy_type": best_signal.strategy_type,
            },
            created_by_user_id=user.id if user else None,
        )
        db.add(event)
        await db.flush()

        # Record metrics
        system_monitoring_service.metrics_collector.record_metric(
            "signal_evaluation_confidence",
            best_signal.confidence,
            {"channel": channel.slug},
        )

        self.logger.info(
            "Signal evaluation complete",
            channel=channel.slug,
            user_id=user_id,
            confidence=best_signal.confidence,
            action=best_signal.action,
            symbol=best_signal.symbol,
        )

        return EvaluationResult(event=event, signal=best_signal)

    def _build_summary(self, signal: TechnicalSignal, channel: SignalChannel) -> str:
        """Build human-readable summary from technical signal."""
        stop_loss_str = f", SL: ${signal.stop_loss:.2f}" if signal.stop_loss else ""
        take_profit_str = f", TP: ${signal.take_profit:.2f}" if signal.take_profit else ""

        return (
            f"{channel.name}: {signal.action} {signal.symbol} @ ${signal.entry_price:.2f}"
            f"{stop_loss_str}{take_profit_str}. "
            f"Confidence: {signal.confidence:.1f}%. {signal.reasoning}"
        )


signal_evaluation_service = SignalEvaluationService()
