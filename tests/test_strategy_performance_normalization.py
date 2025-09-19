import math
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

from app.services.trading_strategies import TradingStrategiesService


def test_normalize_strategy_performance_data_uses_unit_flags():
    data = {
        "total_return": 12.0,
        "benchmark_return": 8.0,
        "volatility": 5.0,
        "max_drawdown": -10.0,
        "win_rate": 62.0,
        "avg_trade": 0.5,
        "largest_win": 4.0,
        "largest_loss": -3.0,
        "returns_are_percent": True,
        "benchmark_is_percent": True,
        "volatility_is_percent": True,
        "max_drawdown_is_percent": True,
        "win_rate_is_percent": True,
        "average_trade_is_percent": True,
        "largest_win_is_percent": True,
        "largest_loss_is_percent": True,
    }

    normalized, flags = TradingStrategiesService._normalize_strategy_performance_data(data)

    assert normalized["total_return"] == pytest.approx(0.12)
    assert normalized["benchmark_return"] == pytest.approx(0.08)
    assert normalized["volatility"] == pytest.approx(0.05)
    assert normalized["max_drawdown"] == pytest.approx(-0.10)
    assert normalized["avg_trade"] == pytest.approx(0.005)
    assert normalized["largest_loss"] == pytest.approx(-0.03)
    assert flags["returns_are_percent"] is True
    assert flags["volatility_is_percent"] is True


def test_normalize_strategy_performance_data_handles_decimal_inputs():
    data = {
        "total_return": 0.12,
        "benchmark_return": 0.08,
        "volatility": 0.05,
        "max_drawdown": -0.10,
        "win_rate": 0.62,
        "avg_trade": 0.005,
        "largest_win": 0.04,
        "largest_loss": -0.03,
        "returns_are_percent": False,
        "benchmark_is_percent": False,
        "volatility_is_percent": False,
        "max_drawdown_is_percent": False,
        "win_rate_is_percent": False,
        "average_trade_is_percent": False,
        "largest_win_is_percent": False,
        "largest_loss_is_percent": False,
    }

    normalized, flags = TradingStrategiesService._normalize_strategy_performance_data(data)

    assert normalized["total_return"] == pytest.approx(0.12)
    assert normalized["benchmark_return"] == pytest.approx(0.08)
    assert normalized["volatility"] == pytest.approx(0.05)
    assert normalized["max_drawdown"] == pytest.approx(-0.10)
    assert normalized["avg_trade"] == pytest.approx(0.005)
    assert normalized["largest_win"] == pytest.approx(0.04)
    assert flags["returns_are_percent"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "strategy_data",
    [
        {
            "total_return": 12.0,
            "benchmark_return": 8.0,
            "volatility": 5.0,
            "max_drawdown": -10.0,
            "win_rate": 60.0,
            "avg_trade": 1.2,
            "largest_win": 6.0,
            "largest_loss": -4.0,
            "returns_are_percent": True,
            "benchmark_is_percent": True,
            "volatility_is_percent": True,
            "max_drawdown_is_percent": True,
            "win_rate_is_percent": True,
            "average_trade_is_percent": True,
            "largest_win_is_percent": True,
            "largest_loss_is_percent": True,
        },
        {
            "total_return": 0.12,
            "benchmark_return": 0.08,
            "volatility": 0.05,
            "max_drawdown": -0.10,
            "win_rate": 0.60,
            "avg_trade": 0.012,
            "largest_win": 0.06,
            "largest_loss": -0.04,
            "returns_are_percent": False,
            "benchmark_is_percent": False,
            "volatility_is_percent": False,
            "max_drawdown_is_percent": False,
            "win_rate_is_percent": False,
            "average_trade_is_percent": False,
            "largest_win_is_percent": False,
            "largest_loss_is_percent": False,
        },
    ],
)
async def test_strategy_performance_handles_multiple_unit_sources(strategy_data):
    service = TradingStrategiesService.__new__(TradingStrategiesService)

    async def fake_get_strategy_data(*args, **kwargs):
        return dict(strategy_data)

    service._get_strategy_performance_data = fake_get_strategy_data  # type: ignore[assignment]

    result = await service.strategy_performance(
        strategy_name="Test Strategy",
        analysis_period="30d",
        parameters=None,
        user_id="tester",
    )

    perf = result["strategy_performance_analysis"]
    metrics = perf["performance_metrics"]
    risk = perf["risk_adjusted_metrics"]
    units = perf["unit_metadata"]

    expected_sharpe = round(
        (0.12 - 0.05) / (0.05 * math.sqrt(252)),
        3,
    )

    assert metrics["total_return_pct"] == pytest.approx(12.0)
    assert metrics["max_drawdown_pct"] == pytest.approx(-10.0)
    assert metrics["volatility_annualized"] == pytest.approx(0.05 * math.sqrt(252) * 100)
    assert metrics["average_trade_return"] == pytest.approx(1.2)
    assert risk["sharpe_ratio"] == pytest.approx(expected_sharpe)
    assert risk["calmar_ratio"] == pytest.approx(round(0.12 / 0.10, 3))
    assert perf["benchmark_comparison"]["outperformance"] == pytest.approx(4.0)
    assert perf["benchmark_comparison"]["benchmark_return_pct"] == pytest.approx(8.0)
    assert units["returns_are_percent"] is strategy_data["returns_are_percent"]
