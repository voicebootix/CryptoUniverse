import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/app")

from app.services.trading_strategies import TradingStrategiesService, StrategyParameters


@pytest.mark.asyncio
async def test_portfolio_optimization_reuses_provided_snapshot(monkeypatch):
    service = TradingStrategiesService.__new__(TradingStrategiesService)

    sanitized_snapshot = {
        "positions": [
            {
                "symbol": "BTC/USDT",
                "quantity": 1.0,
                "market_value": 25000.0,
                "entry_price": 20000.0,
            }
        ],
        "total_value_usd": 26000.0,
        "cash_balance": 1000.0,
        "data_source": "test",
    }

    snapshot_builder = AsyncMock(return_value=sanitized_snapshot)
    monkeypatch.setattr(service, "_build_portfolio_snapshot_from_parameters", snapshot_builder)

    fake_opt_result = {
        "success": True,
        "optimization_result": {
            "expected_return": 0.05,
            "risk_metrics": {"portfolio_volatility": 0.12},
            "expected_sharpe": 1.5,
            "weights": {"BTC/USDT": 0.6},
            "rebalancing_needed": False,
        },
    }

    fake_portfolio_service = SimpleNamespace(
        get_portfolio=AsyncMock(side_effect=AssertionError("should not refetch portfolio")),
        optimize_allocation=AsyncMock(side_effect=AssertionError("should not call raw optimizer")),
        optimize_allocation_with_portfolio_data=AsyncMock(return_value=fake_opt_result),
    )
    monkeypatch.setattr(
        "app.services.portfolio_risk_core.portfolio_risk_service",
        fake_portfolio_service,
    )

    result = await service._execute_management_function(
        function="portfolio_optimization",
        symbol="BTC/USDT",
        parameters=StrategyParameters(symbol="BTC/USDT", quantity=1.0),
        user_id="user-123",
        raw_parameters={"portfolio_snapshot": {"positions": sanitized_snapshot["positions"]}},
        preloaded_portfolio=None,
    )

    assert result["success"] is True
    assert fake_portfolio_service.get_portfolio.await_count == 0
    assert fake_portfolio_service.optimize_allocation.await_count == 0
    assert fake_portfolio_service.optimize_allocation_with_portfolio_data.await_count == 6
    snapshot_builder.assert_awaited_once()
