from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

from tools.run_strategy_diagnostics import (
    DEFAULT_STRATEGY_MATRIX,
    _format_table,
    run_diagnostics,
)


EXPECTED_STRATEGIES = {
    "risk_management",
    "portfolio_optimization",
    "spot_momentum_strategy",
    "spot_mean_reversion",
    "spot_breakout_strategy",
    "scalping_strategy",
    "pairs_trading",
    "statistical_arbitrage",
    "market_making",
    "futures_trade",
    "options_trade",
    "funding_arbitrage",
    "hedge_position",
    "complex_strategy",
}


def test_default_strategy_matrix_matches_expected_set():
    assert set(DEFAULT_STRATEGY_MATRIX) == EXPECTED_STRATEGIES


@pytest.mark.asyncio
async def test_run_diagnostics_collects_success_and_failure_entries():
    calls = []

    async def fake_execute_strategy(*, function: str, **kwargs):
        calls.append({"function": function, "symbol": kwargs.get("symbol")})
        if function == "risk_management":
            return {
                "success": True,
                "execution_result": {"alpha": 0.12},
                "timestamp": "2024-01-01T00:00:00Z",
                "execution_time_seconds": 0.42,
            }
        raise RuntimeError("boom")

    fake_service = SimpleNamespace(execute_strategy=fake_execute_strategy)
    matrix = {
        "risk_management": DEFAULT_STRATEGY_MATRIX["risk_management"],
        "options_trade": DEFAULT_STRATEGY_MATRIX["options_trade"],
    }

    results = await run_diagnostics(
        service=fake_service,
        strategy_matrix=matrix,
        user_id="test-user",
        simulation_mode=True,
    )

    assert calls[0]["function"] == "risk_management"
    assert calls[1]["function"] == "options_trade"

    first, second = results
    assert first["function"] == "risk_management"
    assert first["success"] is True
    assert first["summary"]["execution_result_keys"] == ["alpha"]
    assert first["error"] is None

    assert second["function"] == "options_trade"
    assert second["success"] is False
    assert second["error"] == "boom"


@pytest.mark.parametrize(
    "rows, expected_tail",
    [
        (
            [
                {
                    "function": "risk_management",
                    "symbol": "BTC/USDT",
                    "success": True,
                    "summary": {"execution_result_keys": ["alpha", "beta"]},
                }
            ],
            "risk_management | BTC/USDT | ✅ | execution_result_keys=alpha,beta",
        ),
        (
            [
                {
                    "function": "options_trade",
                    "symbol": "BTC/USDT",
                    "success": False,
                    "error": "Failed to fetch chain",
                }
            ],
            "options_trade | BTC/USDT | ❌ | Failed to fetch chain",
        ),
    ],
)
def test_format_table(rows, expected_tail):
    formatted = _format_table(rows).splitlines()
    assert formatted[0] == "Function | Symbol | Status | Details"
    assert set(formatted[1]) == {"-"}
    assert formatted[2] == expected_tail
