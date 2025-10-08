import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.services.trading_strategies import trading_strategies_service
from app.services import trading_strategies as trading_module


@pytest.mark.asyncio
async def test_spot_breakout_strategy_uses_nested_analysis(monkeypatch):
    parameters = trading_module.StrategyParameters(symbol="BTCUSDT", quantity=1.0, timeframe="1h")

    sr_payload = {
        "success": True,
        "support_resistance_analysis": {
            "symbols_analyzed": ["BTCUSDT"],
            "timeframes": ["1h"],
            "detailed_analysis": {
                "BTCUSDT": {
                    "resistance_levels": [
                        {"level": 26000.0, "strength": "STRONG"},
                        {"level": 26500.0, "strength": "MODERATE"},
                    ],
                    "support_levels": [
                        {"level": 24000.0, "strength": "STRONG"},
                        {"level": 23500.0, "strength": "MODERATE"},
                    ],
                }
            },
        },
    }

    sr_mock = AsyncMock(return_value=sr_payload)
    price_mock = AsyncMock(return_value={"price": 25000.0})
    execute_mock = AsyncMock(return_value={"success": True})

    monkeypatch.setattr(
        trading_strategies_service.market_analyzer,
        "support_resistance_detection",
        sr_mock,
    )
    monkeypatch.setattr(trading_strategies_service, "_get_symbol_price", price_mock)
    monkeypatch.setattr(trading_strategies_service.trade_executor, "execute_trade", execute_mock)

    result = await trading_strategies_service.spot_algorithms.spot_breakout_strategy(
        "BTCUSDT", parameters, user_id="user-1"
    )

    assert result["success"] is True
    assert result["current_price"] == 25000.0
    assert result["key_levels"]["resistance"]
    assert result["breakout_analysis"]
    sr_mock.assert_awaited_once()
    price_mock.assert_awaited()
