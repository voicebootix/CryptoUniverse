"""State hydration helpers that keep portfolio, credit, and strategy data in sync."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import structlog

from app.core.database import AsyncSessionLocal
from app.services.chat_service_adapters_fixed import chat_adapters_fixed as chat_adapters
from app.services.credit_ledger import credit_ledger
from app.services.strategy_marketplace_service import strategy_marketplace_service

logger = structlog.get_logger(__name__)


@dataclass
class CreditSnapshot:
    available_credits: int = 0
    total_credits: int = 0
    credit_to_usd_ratio: float = 1.0
    profit_potential_usd: float = 0.0
    is_vip: bool = False
    tier: str = "standard"


@dataclass
class StrategySnapshot:
    active: List[Dict[str, Any]] = field(default_factory=list)
    marketplace_highlights: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationStateSnapshot:
    """Serializable snapshot of user state for conversational responses."""

    portfolio: Dict[str, Any] = field(default_factory=dict)
    credit: CreditSnapshot = field(default_factory=CreditSnapshot)
    strategies: StrategySnapshot = field(default_factory=StrategySnapshot)
    opportunities: List[Dict[str, Any]] = field(default_factory=list)
    trading_mode: str = "balanced"
    risk_profile: str = "balanced"
    hydrated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["hydrated_at"] = self.hydrated_at.isoformat()
        return data

    def summarize_holdings(self, limit: int = 3) -> List[Tuple[str, float]]:
        positions = (self.portfolio or {}).get("positions", [])
        top_positions = []
        for position in positions[:limit]:
            symbol = position.get("symbol") or position.get("asset")
            pct = float(position.get("percentage") or 0.0)
            if symbol:
                top_positions.append((symbol, pct))
        return top_positions

    @property
    def portfolio_value(self) -> float:
        value = (self.portfolio or {}).get("total_value")
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


class ConversationStateHydrator:
    """Fetch the latest portfolio, credit, and strategy state with graceful fallbacks."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def hydrate(
        self,
        user_id: str,
        *,
        intent_hint: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConversationStateSnapshot:
        portfolio_task = asyncio.create_task(self._fetch_portfolio(user_id))
        credit_task = asyncio.create_task(self._fetch_credit(user_id))
        strategy_task = asyncio.create_task(self._fetch_strategies(user_id))

        portfolio_result, credit_result, strategy_result = await asyncio.gather(
            portfolio_task, credit_task, strategy_task, return_exceptions=True
        )

        snapshot = ConversationStateSnapshot()
        snapshot.portfolio = self._coerce_portfolio(portfolio_result)
        snapshot.credit = self._coerce_credit(credit_result)
        snapshot.strategies = self._coerce_strategies(strategy_result)

        # Derive trading mode / risk profile from strategy metadata when available
        snapshot.trading_mode = (
            (context or {}).get("user_config", {}).get("trading_mode")
            or snapshot.strategies.summary.get("trading_mode")
            or snapshot.portfolio.get("trading_mode")
            or "balanced"
        )
        snapshot.risk_profile = (
            (context or {}).get("user_config", {}).get("risk_profile")
            or snapshot.portfolio.get("risk_level")
            or snapshot.strategies.summary.get("risk_profile")
            or "balanced"
        )

        return snapshot

    async def _fetch_portfolio(self, user_id: str) -> Any:
        try:
            return await chat_adapters.get_portfolio_summary(user_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("portfolio_hydration_failed", user_id=user_id, error=str(exc))
            return {"error": str(exc)}

    async def _fetch_credit(self, user_id: str) -> Any:
        try:
            async with AsyncSessionLocal() as db:
                account = await credit_ledger.get_account(db, user_id, create_if_missing=True)
                if not account:
                    return None
                available = int(account.available_credits or 0)
                total = int(account.total_credits or 0)
                ratio = float(account.credit_to_usd_ratio or 1.0)
                profit_potential = float(account.calculate_profit_potential()) if hasattr(account, "calculate_profit_potential") else 0.0
                return {
                    "available": available,
                    "total": total,
                    "ratio": ratio,
                    "profit_potential": profit_potential,
                    "is_vip": bool(getattr(account, "is_vip", False)),
                }
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("credit_hydration_failed", user_id=user_id, error=str(exc))
            return None

    async def _fetch_strategies(self, user_id: str) -> Any:
        try:
            return await strategy_marketplace_service.get_user_strategy_portfolio(user_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("strategy_hydration_failed", user_id=user_id, error=str(exc))
            return None

    def _coerce_portfolio(self, portfolio_result: Any) -> Dict[str, Any]:
        if isinstance(portfolio_result, dict):
            return portfolio_result
        return {}

    def _coerce_credit(self, credit_result: Any) -> CreditSnapshot:
        snapshot = CreditSnapshot()
        if not isinstance(credit_result, dict):
            return snapshot

        snapshot.available_credits = int(credit_result.get("available") or 0)
        snapshot.total_credits = int(credit_result.get("total") or 0)
        snapshot.credit_to_usd_ratio = float(credit_result.get("ratio") or 1.0)
        snapshot.profit_potential_usd = float(credit_result.get("profit_potential") or 0.0)
        snapshot.is_vip = bool(credit_result.get("is_vip"))
        snapshot.tier = "vip" if snapshot.is_vip else "standard"
        return snapshot

    def _coerce_strategies(self, strategy_result: Any) -> StrategySnapshot:
        snapshot = StrategySnapshot()
        if not isinstance(strategy_result, dict):
            return snapshot

        snapshot.active = strategy_result.get("active_strategies", []) or []
        snapshot.marketplace_highlights = strategy_result.get("available_strategies", []) or []
        summary_fields = {
            key: strategy_result.get(key)
            for key in [
                "total_strategies",
                "active_strategy_count",
                "risk_profile",
                "trading_mode",
                "recommended_categories",
            ]
            if key in strategy_result
        }
        snapshot.summary = {k: v for k, v in summary_fields.items() if v is not None}
        return snapshot


conversation_state_hydrator = ConversationStateHydrator()
