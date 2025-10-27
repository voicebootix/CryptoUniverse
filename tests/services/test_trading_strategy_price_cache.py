import asyncio
import os
from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.services.trading_strategies import TradingStrategiesService
from app.services.market_analysis import market_analysis_service
from app.services.market_data_feeds import market_data_feeds


@pytest.mark.asyncio
async def test_symbol_price_cache_reuses_recent_results(monkeypatch):
    service = TradingStrategiesService()
    service._price_cache_ttl = 120.0

    call_count = 0

    async def fake_get_exchange_price(exchange: str, symbol: str):
        nonlocal call_count
        call_count += 1
        return {
            "price": "101.5",
            "volume": "10000",
            "change_24h": "1.2",
            "timestamp": "2024-01-01T00:00:00Z",
        }

    async def fake_market_snapshot(_symbol: str):
        return {"success": False}

    monkeypatch.setattr(market_analysis_service, "get_exchange_price", fake_get_exchange_price)
    monkeypatch.setattr(market_data_feeds, "get_market_snapshot", fake_market_snapshot)

    result_1 = await service._get_symbol_price("binance", "BTCUSDT")
    result_2 = await service._get_symbol_price("binance", "BTCUSDT")

    assert call_count == 1
    assert result_1["price"] == result_2["price"] == 101.5


@pytest.mark.asyncio
async def test_symbol_price_cache_coalesces_inflight_requests(monkeypatch):
    service = TradingStrategiesService()
    service._price_cache_ttl = 120.0

    call_count = 0
    gate = asyncio.Event()

    async def fake_get_exchange_price(exchange: str, symbol: str):
        nonlocal call_count
        call_count += 1
        await gate.wait()
        return {
            "price": "250.0",
            "volume": "12345",
            "change_24h": "-0.5",
            "timestamp": "2024-01-01T00:00:00Z",
        }

    async def fake_market_snapshot(_symbol: str):
        return {"success": False}

    monkeypatch.setattr(market_analysis_service, "get_exchange_price", fake_get_exchange_price)
    monkeypatch.setattr(market_data_feeds, "get_market_snapshot", fake_market_snapshot)

    async def requester():
        return await service._get_symbol_price("binance", "ETHUSDT")

    first_task = asyncio.create_task(requester())
    second_task = asyncio.create_task(requester())

    await asyncio.sleep(0)
    gate.set()

    first_result, second_result = await asyncio.gather(first_task, second_task)

    assert call_count == 1
    assert first_result == second_result

    service.reset_transient_caches()
    assert service._price_cache == {}
    assert service._price_cache_inflight == {}
