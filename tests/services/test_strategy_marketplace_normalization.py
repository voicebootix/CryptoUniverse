from pathlib import Path
import os
import sys
import types

import pytest


sys.path.append(str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

try:  # pragma: no cover - optional dependency shim for tests
    import aiosqlite  # type: ignore # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    fake_aiosqlite = types.ModuleType("aiosqlite")

    def _unavailable(*_args, **_kwargs):
        raise RuntimeError("aiosqlite is not available in the test environment")

    fake_aiosqlite.connect = _unavailable
    fake_aiosqlite.PARSE_DECLTYPES = None
    fake_aiosqlite.PARSE_COLNAMES = None
    sys.modules["aiosqlite"] = fake_aiosqlite

if "app.services.trading_strategies" not in sys.modules:  # pragma: no cover
    fake_trading_module = types.ModuleType("app.services.trading_strategies")

    class _FakeTradingStrategiesService:  # pragma: no cover - test shim
        async def strategy_performance(self, *args, **kwargs):
            return {"success": False}

    fake_trading_module.trading_strategies_service = _FakeTradingStrategiesService()
    sys.modules["app.services.trading_strategies"] = fake_trading_module

from app.services.strategy_marketplace_service import StrategyMarketplaceService


@pytest.fixture()
def service() -> StrategyMarketplaceService:
    return StrategyMarketplaceService()


def test_normalize_performance_data_maps_strategy_performance_metrics(service: StrategyMarketplaceService):
    performance_result = {
        "success": True,
        "strategy_performance_analysis": {
            "performance_metrics": {
                "net_pnl_usd": 1523.5,
                "winning_trades_pct": 62.5,
                "average_trade_return": 1.8,
                "max_drawdown_pct": -6.5,
                "total_return_pct": 18.0,
                "total_trades": 48,
                "winning_trades": 30,
                "largest_win": 4.2,
                "largest_loss": -3.1,
                "supported_symbols": ["BTCUSDT", "ETHUSDT"],
            },
            "risk_adjusted_metrics": {
                "sharpe_ratio": 1.42,
            },
            "unit_metadata": {
                "pnl_unit": "usd",
                "returns_unit": "percent",
                "max_drawdown_unit": "percent",
                "win_rate_unit": "percent",
                "average_trade_unit": "percent",
                "largest_win_unit": "percent",
                "largest_loss_unit": "percent",
            },
            "performance_badges": ["Live performance"],
            "data_quality": "verified_real_trades",
            "status": "live",
        },
    }

    normalized = service._normalize_performance_data(performance_result, "momentum")

    assert normalized["total_pnl"] == pytest.approx(1523.5)
    assert normalized["win_rate"] == pytest.approx(0.625)
    assert normalized["total_trades"] == 48
    assert normalized["avg_return"] == pytest.approx(0.018)
    assert normalized["max_drawdown"] == pytest.approx(-0.065)
    assert normalized["sharpe_ratio"] == pytest.approx(1.42)
    assert normalized["winning_trades"] == 30
    assert normalized["best_trade_pnl"] == pytest.approx(0.042)
    assert normalized["worst_trade_pnl"] == pytest.approx(-0.031)
    assert normalized["supported_symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert normalized["data_quality"] == "verified_real_trades"
    assert normalized["status"] == "live"
    assert normalized["badges"] == ["Live performance"]
    assert normalized["last_7_days_pnl"] == 0.0
    assert normalized["last_30_days_pnl"] == 0.0


def test_normalize_performance_data_handles_fractional_units(service: StrategyMarketplaceService):
    performance_result = {
        "performance_metrics": {
            "total_pnl": 250.0,
            "win_rate": 0.58,
            "total_trades": 20,
            "average_trade_return": 0.012,
            "max_drawdown": -0.2,
            "largest_win": 45.0,
            "largest_loss": -25.0,
            "last_7_days_pnl": 10.0,
            "last_30_days_pnl": 40.0,
        },
        "unit_metadata": {
            "win_rate_unit": "fraction",
            "average_trade_unit": "fraction",
            "max_drawdown_unit": "fraction",
            "largest_win_unit": "usd",
            "largest_loss_unit": "usd",
        },
        "data_quality": "simulated",
    }

    normalized = service._normalize_performance_data(performance_result, "scalping")

    assert normalized["total_pnl"] == pytest.approx(250.0)
    assert normalized["win_rate"] == pytest.approx(0.58)
    assert normalized["total_trades"] == 20
    assert normalized["avg_return"] == pytest.approx(0.012)
    assert normalized["max_drawdown"] == pytest.approx(-0.2)
    assert normalized["winning_trades"] == 12
    assert normalized["best_trade_pnl"] == pytest.approx(45.0)
    assert normalized["worst_trade_pnl"] == pytest.approx(-25.0)
    assert normalized["last_7_days_pnl"] == pytest.approx(10.0)
    assert normalized["last_30_days_pnl"] == pytest.approx(40.0)
    assert normalized["badges"] == ["Simulated / No live trades"]
