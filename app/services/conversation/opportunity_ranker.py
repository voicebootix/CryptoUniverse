"""Utilities to normalize and rank opportunity results across services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

RISK_MAP = {
    "low": 0.2,
    "medium": 0.5,
    "medium-low": 0.4,
    "medium-high": 0.6,
    "balanced": 0.5,
    "moderate": 0.5,
    "elevated": 0.7,
    "high": 0.85,
}


@dataclass
class RankedOpportunity:
    symbol: str
    direction: str
    potential_usd: Optional[float]
    allocation: Optional[float]
    win_probability: Optional[float]
    risk_level: str
    rationale: Optional[str]
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "potential_usd": self.potential_usd,
            "allocation": self.allocation,
            "win_probability": self.win_probability,
            "risk_level": self.risk_level,
            "rationale": self.rationale,
            "score": self.score,
        }


def rank_opportunities(
    raw_result: Any,
    *,
    risk_profile: str,
    portfolio_value: float,
    limit: int = 5,
) -> List[RankedOpportunity]:
    """Flatten opportunity payloads and score them for conversational output."""

    opportunities = _extract_opportunity_iterable(raw_result)
    ranked: List[RankedOpportunity] = []

    for item in opportunities:
        normalized = _normalize_opportunity(item)
        if not normalized:
            continue

        risk_penalty = _risk_penalty(normalized["risk_level"], risk_profile)
        win_probability = normalized.get("win_probability") or 0.0
        expected_return = normalized.get("expected_return") or 0.0
        potential_usd = normalized.get("potential_usd")

        # Score emphasizes probability alignment with risk appetite and availability of rationale
        score = (
            win_probability * 0.4
            + expected_return * 0.3
            + (1.0 - risk_penalty) * 0.2
            + (0.1 if normalized.get("rationale") else 0.0)
        )

        ranked.append(
            RankedOpportunity(
                symbol=normalized.get("symbol", "UNKNOWN"),
                direction=normalized.get("direction", ""),
                potential_usd=potential_usd,
                allocation=_suggest_allocation(normalized, portfolio_value),
                win_probability=win_probability,
                risk_level=normalized.get("risk_level", "unknown"),
                rationale=normalized.get("rationale"),
                score=score,
            )
        )

    ranked.sort(key=lambda opp: opp.score, reverse=True)
    return ranked[:limit]


def _extract_opportunity_iterable(raw_result: Any) -> Iterable[Dict[str, Any]]:
    if not raw_result:
        return []

    if isinstance(raw_result, dict):
        if "opportunities" in raw_result and isinstance(raw_result["opportunities"], list):
            return raw_result["opportunities"]
        # Some services return nested lists keyed by strategy name
        nested = []
        for value in raw_result.values():
            if isinstance(value, list):
                nested.extend(value)
            elif isinstance(value, dict) and isinstance(value.get("opportunities"), list):
                nested.extend(value["opportunities"])
        return nested

    if isinstance(raw_result, list):
        return raw_result

    return []


def _normalize_opportunity(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None

    symbol = item.get("symbol") or item.get("asset") or item.get("pair")
    if not symbol:
        return None

    direction = item.get("direction") or item.get("trade_type") or item.get("action", "")
    rationale = item.get("rationale") or item.get("reasoning") or item.get("analysis")

    def _coerce_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    potential_usd = _coerce_float(
        item.get("potential_profit")
        or item.get("profit_potential")
        or item.get("potential_usd")
        or item.get("expected_profit")
    )

    win_probability = _coerce_float(
        item.get("win_probability")
        or item.get("confidence")
        or item.get("probability")
    )
    if win_probability and win_probability > 1:
        win_probability = win_probability / 100.0

    expected_return = _coerce_float(item.get("expected_return") or item.get("return_pct"))
    if expected_return and expected_return > 1.5:
        expected_return = expected_return / 100.0

    risk_level = str(item.get("risk_level") or item.get("risk") or "medium").lower()

    normalized = {
        "symbol": symbol,
        "direction": direction,
        "rationale": rationale,
        "potential_usd": potential_usd,
        "expected_return": expected_return or 0.0,
        "win_probability": win_probability or 0.0,
        "risk_level": risk_level,
    }

    allocation = item.get("suggested_allocation") or item.get("allocation_fraction")
    normalized["allocation_fraction"] = _coerce_float(allocation)

    return normalized


def _risk_penalty(opportunity_risk: str, user_risk: str) -> float:
    opp_score = RISK_MAP.get(opportunity_risk.lower(), 0.6)
    user_score = RISK_MAP.get(user_risk.lower(), 0.5)
    return abs(opp_score - user_score)


def _suggest_allocation(opportunity: Dict[str, Any], portfolio_value: float) -> Optional[float]:
    fraction = opportunity.get("allocation_fraction")
    if fraction is None:
        # If we have potential profit and expected return, estimate allocation
        potential = opportunity.get("potential_usd")
        expected_return = opportunity.get("expected_return")
        if potential and expected_return:
            try:
                base_capital = potential / max(expected_return, 0.01)
                if portfolio_value > 0:
                    return min(base_capital / portfolio_value, 1.0)
            except ZeroDivisionError:
                return None
        return None

    try:
        value = float(fraction)
        return value if 0 <= value <= 1 else max(0.0, min(value / 100.0, 1.0))
    except (TypeError, ValueError):
        return None
