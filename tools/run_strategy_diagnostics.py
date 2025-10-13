#!/usr/bin/env python3
"""Run the 14 opportunity discovery strategies and report their status.

This helper is designed for operators who need to verify that every
strategy backing the enterprise opportunity scanner is capable of
producing actionable analytics.  It executes each strategy in sequence,
collects outcome metadata, and prints a concise report that can be used
for incident triage or deployment validation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

from app.services.trading_strategies import TradingStrategiesService

# The exact strategy functions that power opportunity discovery.
DEFAULT_STRATEGY_MATRIX: Mapping[str, Mapping[str, Any]] = {
    "risk_management": {
        "parameters": {
            "analysis_type": "comprehensive",
            "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        },
    },
    "portfolio_optimization": {
        "parameters": {
            "rebalance_frequency": "weekly",
            "risk_target": "balanced",
            "portfolio_snapshot": {
                "cash": 1500,
                "positions": [
                    {"symbol": "BTC/USDT", "quantity": 0.05, "entry_price": 42000},
                    {"symbol": "ETH/USDT", "quantity": 0.75, "entry_price": 2500},
                    {"symbol": "SOL/USDT", "quantity": 12.0, "entry_price": 110},
                ],
            },
        },
    },
    "spot_momentum_strategy": {
        "parameters": {"timeframe": "1h", "lookback": 50},
    },
    "spot_mean_reversion": {
        "parameters": {"timeframe": "1h", "lookback": 40},
    },
    "spot_breakout_strategy": {
        "parameters": {"timeframe": "4h", "sensitivity": 2.0},
    },
    "scalping_strategy": {
        "parameters": {"timeframe": "5m", "risk_per_trade": 0.01},
    },
    "pairs_trading": {
        "parameters": {"pair_symbols": "BTC-ETH", "lookback": 60},
    },
    "statistical_arbitrage": {
        "parameters": {"universe": "BTC,ETH,SOL,ADA", "zscore_threshold": 2.0},
    },
    "market_making": {
        "parameters": {"spread_percentage": 0.12, "inventory_target": 0.5},
    },
    "futures_trade": {
        "strategy_type": "long_futures",
        "parameters": {"leverage": 3, "timeframe": "1h"},
    },
    "options_trade": {
        "strategy_type": "call_option",
        "parameters": {"strike_price": 52000, "expiry_days": 30},
    },
    "funding_arbitrage": {
        "parameters": {"symbols": "BTC,ETH", "min_funding_rate": 0.002},
    },
    "hedge_position": {
        "parameters": {
            "primary_position_size": 1.5,
            "primary_side": "long",
            "hedge_ratio": 0.5,
            "hedge_type": "direct_hedge",
        },
    },
    "complex_strategy": {
        "strategy_type": "iron_condor",
        "parameters": {
            "wings_width": 500,
            "credit_target": 200,
            "contract_multiplier": 100,
        },
    },
}


def _summarize_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Extract a minimal subset of keys for human readable output."""

    summary_keys = (
        "success",
        "signal_strength",
        "confidence_score",
        "expected_return",
        "risk_metrics",
        "trade_plan",
        "opportunity_summary",
        "execution_time_seconds",
    )

    summary = {key: payload[key] for key in summary_keys if key in payload}

    execution_result = payload.get("execution_result")
    if isinstance(execution_result, Mapping):
        summary.setdefault("execution_result_keys", sorted(execution_result.keys()))

    return summary


async def run_diagnostics(
    *,
    service: Optional[TradingStrategiesService] = None,
    strategy_matrix: Optional[Mapping[str, Mapping[str, Any]]] = None,
    user_id: str = "strategy-diagnostics",
    base_symbol: str = "BTC/USDT",
    simulation_mode: bool = False,
) -> List[MutableMapping[str, Any]]:
    """Execute each configured strategy and collect diagnostic metadata."""

    trading_service = service or TradingStrategiesService()
    matrix = strategy_matrix or DEFAULT_STRATEGY_MATRIX

    results: List[MutableMapping[str, Any]] = []

    for function_name, config in matrix.items():
        parameters = dict(config.get("parameters", {}))
        symbol = config.get("symbol", base_symbol)
        strategy_type = config.get("strategy_type")
        exchange = config.get("exchange", "binance")
        risk_mode = config.get("risk_mode", "balanced")

        try:
            payload = await trading_service.execute_strategy(
                function=function_name,
                strategy_type=strategy_type,
                symbol=symbol,
                parameters=parameters,
                risk_mode=risk_mode,
                exchange=exchange,
                user_id=user_id,
                simulation_mode=simulation_mode,
            )
            success = bool(payload.get("success", True))
            results.append(
                {
                    "function": function_name,
                    "symbol": symbol,
                    "strategy_type": strategy_type,
                    "success": success,
                    "timestamp": payload.get("timestamp", datetime.utcnow().isoformat()),
                    "summary": _summarize_payload(payload),
                    "error": None if success else payload.get("error"),
                }
            )
        except Exception as exc:  # pragma: no cover - catastrophic failure path
            results.append(
                {
                    "function": function_name,
                    "symbol": symbol,
                    "strategy_type": strategy_type,
                    "success": False,
                    "timestamp": datetime.utcnow().isoformat(),
                    "summary": {},
                    "error": str(exc),
                }
            )

    return results


def _format_table(rows: Iterable[Mapping[str, Any]]) -> str:
    """Create a simple ASCII table for terminal display."""

    headers = ("Function", "Symbol", "Status", "Details")
    lines = [" | ".join(headers)]
    lines.append("-" * max(len(line) for line in lines))

    for row in rows:
        status = "✅" if row.get("success") else "❌"
        details = row.get("error")
        if not details:
            summary = row.get("summary", {})
            details = ", ".join(
                f"{key}={value}" for key, value in summary.items() if key != "execution_result_keys"
            )
            if not details and summary.get("execution_result_keys"):
                keys = ",".join(summary["execution_result_keys"])
                details = f"execution_result_keys={keys}"
        lines.append(" | ".join(
            (
                row.get("function", ""),
                row.get("symbol", ""),
                status,
                details or "(no details)",
            )
        ))

    return "\n".join(lines)


def main(argv: Optional[Iterable[str]] = None) -> int:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--symbol",
        default="BTC/USDT",
        help="Default symbol to use when a strategy configuration does not specify one",
    )
    parser.add_argument(
        "--user-id",
        default="strategy-diagnostics",
        help="User identifier forwarded to strategy execution",
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run strategies in simulation mode to avoid live market calls",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of a formatted table",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    async def _async_main() -> int:
        results = await run_diagnostics(
            user_id=args.user_id,
            base_symbol=args.symbol,
            simulation_mode=args.simulation,
        )

        if args.json:
            print(json.dumps(results, indent=2, sort_keys=True))
        else:
            print(_format_table(results))

        failed = [row for row in results if not row.get("success")]
        return 0 if not failed else 1

    return asyncio.run(_async_main())


if __name__ == "__main__":  # pragma: no cover - CLI invocation
    raise SystemExit(main())
