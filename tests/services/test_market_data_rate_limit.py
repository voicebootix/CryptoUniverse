import json
import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///tmp/test.db")

from app.services.market_data_feeds import MarketDataFeeds


class FakeCircuitBreaker:
    def __init__(self, allow: bool = True):
        self.allow = allow
        self.failure_count = 0
        self.success_count = 0

    async def _should_try(self) -> bool:
        return self.allow

    async def _record_failure(self) -> None:
        self.failure_count += 1

    async def _record_success(self) -> None:
        self.success_count += 1


@pytest.mark.asyncio
async def test_check_rate_limit_respects_circuit_breaker(monkeypatch):
    feeds = MarketDataFeeds()
    feeds.circuit_breakers["coingecko"] = FakeCircuitBreaker(allow=False)

    allowed = await feeds._check_rate_limit("coingecko")
    assert not allowed


@pytest.mark.asyncio
async def test_check_rate_limit_counts_requests(monkeypatch):
    feeds = MarketDataFeeds()
    feeds.circuit_breakers["coingecko"] = FakeCircuitBreaker(allow=True)

    limiter = feeds.rate_limiters["coingecko"]
    limiter["requests"] = limiter["max_requests"] - 1

    assert await feeds._check_rate_limit("coingecko") is True
    assert limiter["requests"] == limiter["max_requests"]

    assert await feeds._check_rate_limit("coingecko") is False


@pytest.mark.asyncio
async def test_fallback_cached_prices_accepts_dict_payload(monkeypatch):
    feeds = MarketDataFeeds()

    class DummyRedis:
        def __init__(self, mapping):
            self.mapping = mapping

        async def get(self, key):
            return self.mapping.get(key)

    feeds.redis = DummyRedis({
        "price:BTC": {"data": {"price": 25000, "symbol": "BTC"}}
    })

    response = await feeds._fallback_cached_prices(["BTC"])

    assert response["success"] is True
    assert response["data"]["BTC"]["price"] == 25000


@pytest.mark.asyncio
async def test_fallback_cached_prices_accepts_bytes_json(monkeypatch):
    feeds = MarketDataFeeds()

    class DummyRedis:
        def __init__(self, mapping):
            self.mapping = mapping

        async def get(self, key):
            return self.mapping.get(key)

    payload = json.dumps({"data": {"price": 123, "symbol": "ETH"}}).encode()

    feeds.redis = DummyRedis({
        "price:ETH": payload
    })

    response = await feeds._fallback_cached_prices(["ETH"])

    assert response["success"] is True
    assert response["data"]["ETH"]["price"] == 123
