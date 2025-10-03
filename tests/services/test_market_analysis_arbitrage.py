import asyncio
import os
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///tmp/test.db")

from app.services.exchange_universe_service import exchange_universe_service
from app.services.market_analysis_core import MarketAnalysisService


@pytest.mark.asyncio
async def test_arbitrage_scanner_uses_dynamic_universe(monkeypatch):
    service = MarketAnalysisService()

    exchanges_mock = AsyncMock(return_value=["binance", "kraken"])
    symbols_mock = AsyncMock(return_value=["BTC", "ETH"])

    monkeypatch.setattr(exchange_universe_service, "get_user_exchanges", exchanges_mock)
    monkeypatch.setattr(exchange_universe_service, "get_symbol_universe", symbols_mock)

    async def fake_collect(symbol: str, exchange_list):
        return [
            {
                "exchange": "binance",
                "price": 100.0,
                "volume": 10.0,
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "exchange": "kraken",
                "price": 101.0,
                "volume": 8.0,
                "timestamp": "2024-01-01T00:00:01Z",
            },
        ]

    monkeypatch.setattr(service, "_collect_symbol_prices_for_arbitrage", fake_collect)

    result = await service.cross_exchange_arbitrage_scanner(
        symbols="SMART_ADAPTIVE",
        exchanges="all",
        min_profit_bps=10,
        user_id="user-1",
    )

    await service.exchange_manager.close()

    assert result["success"] is True
    summary = result["data"]["summary"]
    assert summary["symbols_scanned"] == 2
    assert summary["exchanges_scanned"] == 2
    assert summary["total_opportunities"] > 0
    assert exchanges_mock.await_count == 1
    assert symbols_mock.await_count == 1


@pytest.mark.asyncio
async def test_collect_symbol_prices_timeout(monkeypatch):
    service = MarketAnalysisService()

    async def fake_get_symbol_price(exchange, symbol):
        await asyncio.sleep(0)
        raise asyncio.TimeoutError

    monkeypatch.setattr(service, "_get_symbol_price", fake_get_symbol_price)

    results = await service._collect_symbol_prices_for_arbitrage("BTC", ["binance", "kraken"])

    await service.exchange_manager.close()

    assert results == []


@pytest.mark.asyncio
async def test_arbitrage_scanner_completes_when_exchanges_timeout(monkeypatch):
    service = MarketAnalysisService()
    service._per_exchange_timeout = 0.05

    monkeypatch.setattr(
        exchange_universe_service,
        "get_user_exchanges",
        AsyncMock(return_value=["fast", "slow", "faster"]),
    )
    monkeypatch.setattr(
        exchange_universe_service,
        "get_symbol_universe",
        AsyncMock(return_value=["BTC"]),
    )

    async def fake_get_symbol_price(exchange, symbol):
        if exchange == "slow":
            await asyncio.sleep(0.2)
            return {"price": 105.0, "volume": 1.0}
        if exchange == "fast":
            await asyncio.sleep(0.01)
            return {"price": 100.0, "volume": 5.0}
        await asyncio.sleep(0.01)
        return {"price": 102.0, "volume": 4.0}

    monkeypatch.setattr(service, "_get_symbol_price", fake_get_symbol_price)

    result = await asyncio.wait_for(
        service.cross_exchange_arbitrage_scanner(
            symbols="SMART_ADAPTIVE",
            exchanges="all",
            min_profit_bps=10,
            user_id="user-123",
        ),
        timeout=1,
    )

    await service.exchange_manager.close()

    assert result["success"] is True
    opportunities = result["data"]["opportunities"]
    # Only the fast exchanges should contribute because the slow exchange timed out
    assert all(opp["buy_exchange"] != "slow" and opp["sell_exchange"] != "slow" for opp in opportunities)
    # Ensure at least one opportunity was generated from fast vs faster
    assert any({opp["buy_exchange"], opp["sell_exchange"]} == {"fast", "faster"} for opp in opportunities)
