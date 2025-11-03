"""Shared constants for opportunity discovery and strategy scanning policies."""

from __future__ import annotations

from typing import Any, Dict
import copy

from app.core.config import get_settings

# Canonical defaults that preserve historical scanning behavior per strategy.
DEFAULT_STRATEGY_POLICY_PRESETS: Dict[str, Dict[str, Any]] = {
    "funding_arbitrage": {"max_symbols": 20, "priority": 130, "enabled": True},
    "statistical_arbitrage": {"max_symbols": 50, "priority": 125, "enabled": True},
    "spot_momentum_strategy": {"max_symbols": 30, "priority": 120, "enabled": True},
    "spot_mean_reversion": {"max_symbols": 25, "priority": 118, "enabled": True},
    "spot_breakout_strategy": {"max_symbols": 20, "priority": 116, "enabled": True},
    "scalping_strategy": {"max_symbols": 8, "priority": 112, "enabled": True},
    "market_making": {"max_symbols": 10, "priority": 110, "enabled": True},
    "futures_trade": {"max_symbols": 20, "priority": 108, "enabled": True},
    "options_trade": {"max_symbols": 15, "chunk_size": 5, "priority": 106, "enabled": True},
    "volatility_trading": {"max_symbols": 12, "priority": 104, "enabled": True},
    "news_sentiment": {"max_symbols": 12, "priority": 102, "enabled": True},
    "community_strategy": {"max_symbols": 8, "priority": 100, "enabled": True},
    "hedge_position": {"max_symbols": 5, "priority": 98, "enabled": True},
    "futures_arbitrage": {"max_symbols": 10, "priority": 96, "enabled": True},
    "complex_strategy": {"max_symbols": 10, "priority": 94, "enabled": True},
}


def build_strategy_policy_baseline() -> Dict[str, Dict[str, Any]]:
    """Return default strategy scanning policies merged with configured overrides."""

    settings = get_settings()
    baseline = copy.deepcopy(DEFAULT_STRATEGY_POLICY_PRESETS)
    overrides = getattr(settings, "opportunity_strategy_symbol_policies", {}) or {}

    if isinstance(overrides, dict):
        for raw_key, raw_value in overrides.items():
            if not isinstance(raw_value, dict):
                continue
            key = str(raw_key).strip()
            if not key:
                continue

            base_entry = baseline.get(key, {"priority": 100, "enabled": True})
            merged_entry = base_entry.copy()

            if "max_symbols" in raw_value:
                merged_entry["max_symbols"] = raw_value.get("max_symbols")
            if "chunk_size" in raw_value:
                merged_entry["chunk_size"] = raw_value.get("chunk_size")
            if "enabled" in raw_value:
                merged_entry["enabled"] = bool(raw_value.get("enabled", True))
            if "priority" in raw_value and raw_value.get("priority") is not None:
                try:
                    merged_entry["priority"] = int(raw_value.get("priority"))
                except (TypeError, ValueError):
                    pass

            merged_entry["source"] = "config"
            baseline[key] = merged_entry

    for key, entry in baseline.items():
        entry.setdefault("source", "default")

    return baseline
