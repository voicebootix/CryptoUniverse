import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///tmp/test.db")

from app.services import trading_strategies


@pytest.mark.asyncio
async def test_strategy_performance_handles_missing_trade_counts(monkeypatch):
    monkeypatch.setattr(trading_strategies, "TradeExecutionService", lambda: SimpleNamespace())
    monkeypatch.setattr(trading_strategies, "MarketAnalysisService", lambda: SimpleNamespace())
    monkeypatch.setattr(trading_strategies, "DerivativesEngine", lambda _executor: SimpleNamespace())
    monkeypatch.setattr(
        trading_strategies,
        "SpotAlgorithms",
        lambda _executor, _analyzer: SimpleNamespace(),
    )

    service = trading_strategies.TradingStrategiesService()

    async def fake_get_strategy_performance_data(*_args, **_kwargs):
        return {
            "data_quality": "verified",
            "status": "verified",
            "total_return": 0.12,
            "benchmark_return": 0.08,
            "volatility": 0.05,
            "max_drawdown": 0.1,
            "win_rate": 0.6,
            "avg_trade": 0.01,
            "largest_win": 0.04,
            "largest_loss": 0.03,
        }

    def fake_normalize(data):
        return data, {}

    monkeypatch.setattr(
        service,
        "_get_strategy_performance_data",
        fake_get_strategy_performance_data,
    )
    monkeypatch.setattr(service, "_normalize_strategy_performance_data", fake_normalize)
    monkeypatch.setattr(service, "_get_period_days_safe", lambda _period: 30)

    result = await service.strategy_performance("demo", "30d")

    assert result["success"] is True
    metrics = result["strategy_performance_analysis"]["performance_metrics"]
    assert metrics["total_trades"] == 0
    assert metrics["winning_trades"] == 0
    assert metrics["losing_trades"] == 0
