import os
import types

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///tmp/test.db")

from app.services.market_analysis_core import MarketAnalysisService
from app.services.trading_strategies import TradingStrategiesService


@pytest.mark.asyncio
async def test_get_exchange_price_uses_in_memory_cache(monkeypatch):
    service = MarketAnalysisService()

    async def fake_load(self, cache_key):
        return None

    async def fake_store(self, cache_key, data, ttl):
        return None

    fetch_calls = {"count": 0}

    async def fake_bulk(self, exchange, symbols):
        fetch_calls["count"] += 1
        return {
            self._normalize_symbol_for_exchange(exchange, s)[1]: {
                "price": 101.0,
                "volume": 1.0,
                "timestamp": "now",
            }
            for s in symbols
        }

    monkeypatch.setattr(service, "_load_price_from_redis", types.MethodType(fake_load, service))
    monkeypatch.setattr(service, "_store_price_in_redis", types.MethodType(fake_store, service))
    monkeypatch.setattr(service, "_fetch_bulk_symbol_prices", types.MethodType(fake_bulk, service))

    first = await service.get_exchange_price("binance", "btc")
    second = await service.get_exchange_price("binance", "BTC/USDT")

    assert first["price"] == pytest.approx(101.0)
    assert second["price"] == pytest.approx(101.0)
    assert fetch_calls["count"] == 1


@pytest.mark.asyncio
async def test_preload_exchange_prices_deduplicates(monkeypatch):
    service = MarketAnalysisService()

    calls = []

    async def fake_bulk(self, exchange, symbols):
        calls.append((exchange, tuple(sorted(symbols))))
        return {
            symbol: {"price": 1.0, "timestamp": "now"}
            for symbol in symbols
        }

    async def fake_store(self, cache_key, data, ttl):
        return None

    monkeypatch.setattr(service, "_fetch_bulk_symbol_prices", types.MethodType(fake_bulk, service))
    monkeypatch.setattr(service, "_store_price_in_redis", types.MethodType(fake_store, service))

    await service.preload_exchange_prices(
        [("binance", "btc"), ("binance", "BTC/USDT"), ("kraken", "ETH/USD")],
        concurrency=2,
    )

    assert any(
        exchange == "binance" and ("BTC/USDT",) == tuple(symbols)
        for exchange, symbols in calls
    )
    assert any(exchange == "kraken" for exchange, _ in calls)


@pytest.mark.asyncio
async def test_trading_strategies_price_uses_shared_service(monkeypatch):
    service = TradingStrategiesService()

    class StubAnalysis:
        def __init__(self):
            self.calls = []

        async def get_exchange_price(self, exchange, symbol, ttl=None):
            self.calls.append((exchange, symbol))
            return {"price": 255.0, "timestamp": "now"}

    stub = StubAnalysis()

    monkeypatch.setattr(
        "app.services.trading_strategies.market_analysis_service",
        stub,
    )

    result = await service._get_symbol_price("auto", "btc")

    assert result["success"] is True
    assert result["price"] == pytest.approx(255.0)
    assert stub.calls == [("binance", "BTC/USDT")]
