import os
from pathlib import Path

import pytest
from unittest.mock import AsyncMock

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

# Ensure application modules are importable when tests run in isolation
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.services.trading_strategies import trading_strategies_service
from app.services import trading_strategies as trading_module


@pytest.mark.asyncio
async def test_execute_strategy_passes_parameters_to_funding(monkeypatch):
    funding_mock = AsyncMock(return_value={"success": True})
    monkeypatch.setattr(trading_strategies_service, "funding_arbitrage", funding_mock)

    params = {"symbols": "SOL,ADA", "exchanges": "binance,bybit", "min_funding_rate": 0.01}

    await trading_strategies_service.execute_strategy(
        function="funding_arbitrage",
        parameters=params,
        user_id="user-123",
    )

    funding_mock.assert_awaited_once()
    kwargs = funding_mock.await_args.kwargs
    assert kwargs["symbols"] == "SOL,ADA"
    assert kwargs["exchanges"] == "binance,bybit"
    assert kwargs["min_funding_rate"] == 0.01
    assert kwargs["user_id"] == "user-123"


@pytest.mark.asyncio
async def test_execute_strategy_passes_universe_to_statistical(monkeypatch):
    stat_mock = AsyncMock(return_value={"success": True})
    monkeypatch.setattr(trading_strategies_service, "statistical_arbitrage", stat_mock)

    params = {"universe": "BTC,ETH", "exchanges": "binance,kraken"}

    await trading_strategies_service.execute_strategy(
        function="statistical_arbitrage",
        strategy_type="mean_reversion",
        parameters=params,
        user_id="user-456",
    )

    stat_mock.assert_awaited_once()
    kwargs = stat_mock.await_args.kwargs
    assert kwargs["universe"] == "BTC,ETH"
    assert kwargs["parameters"] == params
    assert kwargs["user_id"] == "user-456"


@pytest.mark.asyncio
async def test_funding_arbitrage_dynamic_universe(monkeypatch):
    exchange_mock = AsyncMock(return_value=["binance", "bybit"])
    symbol_mock = AsyncMock(return_value=["BTCUSDT", "SOL"])
    monkeypatch.setattr(trading_module.exchange_universe_service, "get_user_exchanges", exchange_mock)
    monkeypatch.setattr(trading_module.exchange_universe_service, "get_symbol_universe", symbol_mock)

    async def fake_funding(symbol_pair: str, exchange: str):
        base = 0.015 if exchange == "binance" else -0.005
        return {
            "current_funding_rate": base,
            "predicted_funding_rate": base,
            "funding_interval": 8,
        }

    funding_info_mock = AsyncMock(side_effect=fake_funding)
    monkeypatch.setattr(trading_strategies_service, "_get_perpetual_funding_info", funding_info_mock)

    result = await trading_strategies_service.funding_arbitrage(
        symbols="SMART_ADAPTIVE",
        exchanges="all",
        min_funding_rate=0.001,
        user_id="user-789",
    )

    exchange_mock.assert_awaited_once_with(
        "user-789",
        [],
        default_exchanges=trading_strategies_service.market_analyzer.exchange_manager.exchange_configs.keys(),
    )
    symbol_mock.assert_awaited_once_with("user-789", None, ["binance", "bybit"])

    analysis = result["funding_arbitrage_analysis"]
    assert set(analysis["funding_analysis"].keys()) == {"BTC", "SOL"}
    assert analysis["opportunities"], "expected arbitrage opportunities to be generated"


@pytest.mark.asyncio
async def test_statistical_arbitrage_dynamic_universe(monkeypatch):
    exchange_mock = AsyncMock(return_value=["kraken", "binance"])
    symbol_mock = AsyncMock(return_value=["ETHUSDT", "AVAX"])
    monkeypatch.setattr(trading_module.exchange_universe_service, "get_user_exchanges", exchange_mock)
    monkeypatch.setattr(trading_module.exchange_universe_service, "get_symbol_universe", symbol_mock)

    price_data = {
        "ETHUSDT": {"price": 1800.0, "volume": 5_000_000.0, "change_24h": 2.5},
        "AVAXUSDT": {"price": 35.0, "volume": 1_500_000.0, "change_24h": -1.0},
    }

    async def fake_price(exchange: str, symbol: str):
        record = price_data.get(symbol)
        if not record:
            return None
        return {
            "price": record["price"],
            "volume": record["volume"],
            "change_24h": record["change_24h"],
        }

    price_mock = AsyncMock(side_effect=fake_price)
    monkeypatch.setattr(trading_strategies_service, "_get_symbol_price", price_mock)

    result = await trading_strategies_service.statistical_arbitrage(
        universe="SMART_ADAPTIVE",
        parameters={"exchanges": "kraken", "max_universe": 10},
        user_id="user-999",
    )

    exchange_mock.assert_awaited_once_with(
        "user-999",
        ["kraken"],
        default_exchanges=trading_strategies_service.market_analyzer.exchange_manager.exchange_configs.keys(),
    )
    symbol_mock.assert_awaited_once_with("user-999", None, ["kraken", "binance"], limit=10)

    analysis = result["statistical_arbitrage_analysis"]
    assert analysis["universe"] == ["ETH", "AVAX"], analysis
    assert analysis["universe_analysis"]["exchanges_scanned"] == ["kraken", "binance"]
    assert analysis["opportunities"], "expected stat-arb opportunities to be generated"
