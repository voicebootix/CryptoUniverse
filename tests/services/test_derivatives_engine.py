import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.services import trading_strategies as trading_module


@pytest.mark.asyncio
async def test_derivatives_engine_position_size_uses_price_fetcher():
    async def fake_price(exchange: str, symbol: str):
        assert exchange == "binance"
        assert symbol == "BTCUSDT"
        return {"price": 20000.0}

    engine = trading_module.DerivativesEngine(MagicMock(), price_fetcher=fake_price)
    params = trading_module.StrategyParameters(
        symbol="BTCUSDT",
        quantity=1.0,
        risk_percentage=1.0,
        leverage=2.0,
    )

    quantity = await engine._calculate_leveraged_position_size(params, "binance", "user-abc", "BTCUSDT")

    expected = round(((10000 * 0.01) * 2.0) / 20000.0, 6)
    assert quantity == expected


@pytest.mark.asyncio
async def test_derivatives_engine_returns_zero_when_price_missing():
    async def empty_price(exchange: str, symbol: str):
        return {}

    engine = trading_module.DerivativesEngine(MagicMock(), price_fetcher=empty_price)
    params = trading_module.StrategyParameters(symbol="ETHUSDT", quantity=1.0)

    quantity = await engine._calculate_leveraged_position_size(params, "binance", "user-xyz", "ETHUSDT")
    assert quantity == 0.0
