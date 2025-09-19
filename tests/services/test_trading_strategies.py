from pathlib import Path
from unittest.mock import AsyncMock

import os
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

from app.services.trading_strategies import TradingStrategiesService


def _create_service() -> TradingStrategiesService:
    """Helper to instantiate the trading strategies service for tests."""
    return TradingStrategiesService()


def test_normalize_strategy_performance_data_respects_unit_flags():
    service = _create_service()

    strategy_data = {
        "total_return": 15.5,
        "benchmark_return": 10.0,
        "volatility": 0.5,
        "max_drawdown": -12.0,
        "win_rate": 60,
        "avg_trade": 0.01,
        "largest_win": 3.5,
        "largest_loss": -2.5,
        "returns_are_percent": True,
        "benchmark_is_percent": True,
        "volatility_is_percent": True,
        "max_drawdown_is_percent": True,
        "win_rate_is_percent": True,
        "avg_trade_is_percent": False,
        "largest_win_is_percent": True,
        "largest_loss_is_percent": True,
    }

    normalized = service._normalize_strategy_performance_data(strategy_data)

    assert normalized["total_return_decimal"] == pytest.approx(0.155)
    assert normalized["benchmark_return_decimal"] == pytest.approx(0.10)
    assert normalized["volatility_decimal"] == pytest.approx(0.005)
    assert normalized["volatility_pct"] == pytest.approx(0.5)
    assert normalized["max_drawdown_decimal"] == pytest.approx(-0.12)
    assert normalized["win_rate_decimal"] == pytest.approx(0.60)
    assert normalized["avg_trade_decimal"] == pytest.approx(0.01)
    assert normalized["avg_trade_pct"] == pytest.approx(1.0)
    assert normalized["largest_loss_decimal"] == pytest.approx(-0.025)
    assert normalized["units"]["volatility_is_percent"] is True
    assert normalized["units"]["avg_trade_is_percent"] is False


@pytest.mark.asyncio
async def test_strategy_performance_handles_percent_and_decimal_sources():
    service = _create_service()

    percent_based_data = {
        "total_return": 12.0,
        "benchmark_return": 9.0,
        "volatility": 3.0,
        "max_drawdown": -5.0,
        "win_rate": 55.0,
        "avg_trade": 1.5,
        "largest_win": 4.0,
        "largest_loss": -3.0,
        "recovery_time": 10,
        "profit_factor": 1.8,
        "treynor_ratio": 1.1,
        "beta": 0.9,
        "correlation": 0.8,
        "up_capture": 87,
        "down_capture": 73,
        "hit_rate": 60,
        "worst_relative": -4.0,
        "returns_are_percent": True,
        "benchmark_is_percent": True,
        "volatility_is_percent": True,
        "max_drawdown_is_percent": True,
        "win_rate_is_percent": True,
        "avg_trade_is_percent": True,
        "largest_win_is_percent": True,
        "largest_loss_is_percent": True,
    }

    decimal_based_data = {
        "total_return": 0.12,
        "benchmark_return": 0.09,
        "volatility": 0.03,
        "max_drawdown": -0.05,
        "win_rate": 0.55,
        "avg_trade": 0.015,
        "largest_win": 0.04,
        "largest_loss": -0.03,
        "recovery_time": 10,
        "profit_factor": 1.8,
        "treynor_ratio": 1.1,
        "beta": 0.9,
        "correlation": 0.8,
        "up_capture": 87,
        "down_capture": 73,
        "hit_rate": 60,
        "worst_relative": -4.0,
        "returns_are_percent": False,
        "benchmark_is_percent": False,
        "volatility_is_percent": False,
        "max_drawdown_is_percent": False,
        "win_rate_is_percent": False,
        "avg_trade_is_percent": False,
        "largest_win_is_percent": False,
        "largest_loss_is_percent": False,
    }

    service._get_strategy_performance_data = AsyncMock(return_value=percent_based_data)
    percent_result = await service.strategy_performance("test", "30d")

    service._get_strategy_performance_data = AsyncMock(return_value=decimal_based_data)
    decimal_result = await service.strategy_performance("test", "30d")

    def _extract_core_metrics(result):
        metrics = result["strategy_performance_analysis"]["performance_metrics"]
        risk = result["strategy_performance_analysis"]["risk_adjusted_metrics"]
        comparison = result["strategy_performance_analysis"]["benchmark_comparison"]
        return metrics, risk, comparison

    percent_metrics, percent_risk, percent_comparison = _extract_core_metrics(percent_result)
    decimal_metrics, decimal_risk, decimal_comparison = _extract_core_metrics(decimal_result)

    assert percent_metrics["total_return_pct"] == pytest.approx(12.0)
    assert decimal_metrics["total_return_pct"] == pytest.approx(12.0)
    assert percent_metrics["annualized_return_pct"] == pytest.approx(decimal_metrics["annualized_return_pct"])
    assert percent_metrics["volatility_annualized"] == pytest.approx(decimal_metrics["volatility_annualized"])
    assert percent_metrics["max_drawdown_pct"] == pytest.approx(-5.0)
    assert decimal_metrics["max_drawdown_pct"] == pytest.approx(-5.0)
    assert percent_metrics["winning_trades_pct"] == pytest.approx(55.0)
    assert decimal_metrics["winning_trades_pct"] == pytest.approx(55.0)
    assert percent_metrics["average_trade_return"] == pytest.approx(1.5)
    assert decimal_metrics["average_trade_return"] == pytest.approx(1.5)
    assert percent_metrics["largest_win"] == pytest.approx(4.0)
    assert decimal_metrics["largest_win"] == pytest.approx(4.0)
    assert percent_metrics["largest_loss"] == pytest.approx(-3.0)
    assert decimal_metrics["largest_loss"] == pytest.approx(-3.0)

    assert percent_risk["sharpe_ratio"] == pytest.approx(decimal_risk["sharpe_ratio"])
    assert percent_risk["calmar_ratio"] == pytest.approx(decimal_risk["calmar_ratio"])
    assert percent_risk["information_ratio"] == pytest.approx(decimal_risk["information_ratio"])
    assert percent_risk["var_adjusted_return"] == pytest.approx(decimal_risk["var_adjusted_return"])
    assert percent_risk["cvar_adjusted_return"] == pytest.approx(decimal_risk["cvar_adjusted_return"])

    assert percent_comparison["outperformance"] == pytest.approx(3.0)
    assert decimal_comparison["outperformance"] == pytest.approx(3.0)
    assert percent_comparison["outperformance_pct"] == pytest.approx(decimal_comparison["outperformance_pct"])
    assert percent_comparison["tracking_error"] == pytest.approx(decimal_comparison["tracking_error"])

    assert percent_result["strategy_performance_analysis"]["optimization_recommendations"] == \
        decimal_result["strategy_performance_analysis"]["optimization_recommendations"]
