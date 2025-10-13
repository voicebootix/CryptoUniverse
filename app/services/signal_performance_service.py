"""Signal performance tracking and quality scoring service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import SignalChannel, SignalDeliveryLog, SignalEvent, SignalSubscription
from app.services.market_data_coordinator import market_data_coordinator

logger = structlog.get_logger(__name__)


@dataclass
class SignalPerformance:
    """Performance metrics for a signal channel."""

    channel_id: UUID
    channel_name: str
    total_signals: int
    completed_signals: int
    win_count: int
    loss_count: int
    pending_count: int
    win_rate: float
    avg_profit_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    best_signal_pct: float
    worst_signal_pct: float
    total_return_pct: float
    quality_score: float  # 0-100
    timeframe_days: int


class SignalPerformanceService:
    """Track and analyze signal performance over time."""

    def __init__(self):
        self.logger = logger

    async def track_signal_outcome(
        self,
        db: AsyncSession,
        event: SignalEvent,
        force_check: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if signal hit target or stop loss and update outcome.

        Called periodically by background service to track all pending signals.
        """
        if event.actual_outcome and event.actual_outcome != "pending" and not force_check:
            return None  # Already tracked

        payload = event.opportunity_payload or {}
        symbol = payload.get("symbol")
        entry_price = payload.get("entry_price")
        stop_loss = payload.get("stop_loss")
        take_profit = payload.get("take_profit")
        action = payload.get("action", "BUY")

        if not symbol or not entry_price:
            return None

        # Get current price
        try:
            market_data = await market_data_coordinator.get_market_data(symbol)
            if not market_data.get("success"):
                return None

            current_price = float(market_data.get("price", 0))
            if current_price <= 0:
                return None

        except Exception as e:
            self.logger.warning("Failed to fetch price for signal tracking", symbol=symbol, error=str(e))
            return None

        # Check outcome
        outcome = None
        profit_pct = 0.0

        if action == "BUY":
            # For BUY signals
            if take_profit and current_price >= take_profit:
                outcome = "win"
                profit_pct = ((current_price - entry_price) / entry_price) * 100
            elif stop_loss and current_price <= stop_loss:
                outcome = "loss"
                profit_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # SELL
            # For SELL signals
            if take_profit and current_price <= take_profit:
                outcome = "win"
                profit_pct = ((entry_price - current_price) / entry_price) * 100
            elif stop_loss and current_price >= stop_loss:
                outcome = "loss"
                profit_pct = ((entry_price - current_price) / entry_price) * 100

        # Check if signal expired (24 hours)
        if not outcome and event.triggered_at:
            age = datetime.utcnow() - event.triggered_at
            if age > timedelta(hours=24):
                outcome = "expired"
                profit_pct = ((current_price - entry_price) / entry_price) * 100 if action == "BUY" else ((entry_price - current_price) / entry_price) * 100

        # Update event if outcome determined
        if outcome:
            event.actual_outcome = outcome
            event.actual_profit_pct = Decimal(str(profit_pct))
            event.closed_at = datetime.utcnow()
            event.close_price = Decimal(str(current_price))
            await db.flush()

            self.logger.info(
                "Signal outcome tracked",
                event_id=str(event.id),
                symbol=symbol,
                outcome=outcome,
                profit_pct=profit_pct,
            )

            return {
                "event_id": str(event.id),
                "symbol": symbol,
                "outcome": outcome,
                "profit_pct": profit_pct,
                "entry_price": entry_price,
                "close_price": current_price,
            }

        return None

    async def get_channel_performance(
        self,
        db: AsyncSession,
        channel_id: UUID,
        days: int = 30,
    ) -> SignalPerformance:
        """Get performance metrics for a signal channel."""

        # Get channel
        channel_stmt = select(SignalChannel).where(SignalChannel.id == channel_id)
        channel_result = await db.execute(channel_stmt)
        channel = channel_result.scalar_one_or_none()

        if not channel:
            raise ValueError(f"Channel {channel_id} not found")

        # Get events from last N days
        start_date = datetime.utcnow() - timedelta(days=days)
        events_stmt = (
            select(SignalEvent)
            .where(
                and_(
                    SignalEvent.channel_id == channel_id,
                    SignalEvent.triggered_at >= start_date,
                )
            )
        )
        events_result = await db.execute(events_stmt)
        events = events_result.scalars().all()

        total_signals = len(events)
        win_count = 0
        loss_count = 0
        pending_count = 0
        profits: List[float] = []
        wins: List[float] = []
        losses: List[float] = []

        for event in events:
            if event.actual_outcome == "win":
                win_count += 1
                profit = float(event.actual_profit_pct or 0)
                profits.append(profit)
                wins.append(profit)
            elif event.actual_outcome == "loss":
                loss_count += 1
                profit = float(event.actual_profit_pct or 0)
                profits.append(profit)
                losses.append(profit)
            elif event.actual_outcome == "pending" or not event.actual_outcome:
                pending_count += 1

        completed_signals = win_count + loss_count
        win_rate = (win_count / completed_signals * 100) if completed_signals > 0 else 0
        avg_profit_pct = (sum(profits) / len(profits)) if profits else 0
        avg_win_pct = (sum(wins) / len(wins)) if wins else 0
        avg_loss_pct = (sum(losses) / len(losses)) if losses else 0
        best_signal_pct = max(profits) if profits else 0
        worst_signal_pct = min(profits) if profits else 0
        total_return_pct = sum(profits) if profits else 0.0

        # Calculate quality score (0-100)
        quality_score = self._calculate_quality_score(
            win_rate=win_rate,
            avg_profit_pct=avg_profit_pct,
            total_signals=total_signals,
            completed_signals=completed_signals,
        )

        return SignalPerformance(
            channel_id=channel_id,
            channel_name=channel.name,
            total_signals=total_signals,
            completed_signals=completed_signals,
            win_count=win_count,
            loss_count=loss_count,
            pending_count=pending_count,
            win_rate=win_rate,
            avg_profit_pct=avg_profit_pct,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            best_signal_pct=best_signal_pct,
            worst_signal_pct=worst_signal_pct,
            total_return_pct=total_return_pct,
            quality_score=quality_score,
            timeframe_days=days,
        )

    def _calculate_quality_score(
        self,
        win_rate: float,
        avg_profit_pct: float,
        total_signals: int,
        completed_signals: int,
    ) -> float:
        """
        Calculate signal quality score (0-100).

        Factors:
        - Win rate (40% weight)
        - Average profit (30% weight)
        - Sample size (20% weight)
        - Completion rate (10% weight)
        """
        if completed_signals == 0:
            return 0.0

        # Win rate score (0-40 points)
        win_rate_score = min(40, (win_rate / 100) * 40)

        # Profit score (0-30 points)
        # Normalize to 0-30 where 5% avg profit = 30 points
        profit_score = min(30, (avg_profit_pct / 5) * 30) if avg_profit_pct > 0 else 0

        # Sample size score (0-20 points)
        # Need at least 20 completed signals for full score
        sample_score = min(20, (completed_signals / 20) * 20)

        # Completion rate score (0-10 points)
        completion_rate = (completed_signals / total_signals) if total_signals > 0 else 0
        completion_score = completion_rate * 10

        total_score = win_rate_score + profit_score + sample_score + completion_score
        return round(total_score, 2)

    async def get_all_channel_performance(
        self,
        db: AsyncSession,
        days: int = 30,
    ) -> List[SignalPerformance]:
        """Get performance for all active channels."""

        channels_stmt = select(SignalChannel).where(SignalChannel.is_active.is_(True))
        channels_result = await db.execute(channels_stmt)
        channels = channels_result.scalars().all()

        performances = []
        for channel in channels:
            try:
                perf = await self.get_channel_performance(db, channel.id, days)
                performances.append(perf)
            except Exception as e:
                self.logger.error("Failed to get channel performance", channel_id=str(channel.id), error=str(e))

        # Sort by quality score descending
        performances.sort(key=lambda p: p.quality_score, reverse=True)
        return performances

    async def get_user_signal_history(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get signal history for a user."""

        # Get user's deliveries
        stmt = (
            select(SignalDeliveryLog, SignalEvent, SignalChannel)
            .join(SignalEvent, SignalDeliveryLog.event_id == SignalEvent.id)
            .join(SignalChannel, SignalEvent.channel_id == SignalChannel.id)
            .join(SignalSubscription, SignalDeliveryLog.subscription_id == SignalSubscription.id)
            .where(SignalSubscription.user_id == user_id)
            .order_by(SignalDeliveryLog.delivered_at.desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        rows = result.all()

        history = []
        for delivery, event, channel in rows:
            payload = event.opportunity_payload or {}
            history.append({
                "event_id": str(event.id),
                "channel_name": channel.name,
                "channel_slug": channel.slug,
                "symbol": payload.get("symbol"),
                "action": payload.get("action"),
                "entry_price": payload.get("entry_price"),
                "stop_loss": payload.get("stop_loss"),
                "take_profit": payload.get("take_profit"),
                "confidence": float(event.confidence),
                "triggered_at": event.triggered_at.isoformat(),
                "delivered_at": delivery.delivered_at.isoformat(),
                "delivery_channel": delivery.delivery_channel,
                "status": delivery.status,
                "executed": delivery.executed_at is not None,
                "executed_at": delivery.executed_at.isoformat() if delivery.executed_at else None,
                "outcome": event.actual_outcome,
                "profit_pct": float(event.actual_profit_pct) if event.actual_profit_pct else None,
                "closed_at": event.closed_at.isoformat() if event.closed_at else None,
            })

        return history


signal_performance_service = SignalPerformanceService()
