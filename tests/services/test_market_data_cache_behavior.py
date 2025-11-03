import copy
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///tmp/test.db")

from app.services.market_data_feeds import MarketDataFeeds


@pytest.mark.asyncio
async def test_real_time_price_marks_live_cache_metadata(monkeypatch):
    feeds = MarketDataFeeds()
    feeds.redis = None

    async def no_cache(*_, **__):
        return None

    async def allow(*_, **__):
        return True

    async def noop(*_, **__):
        return None

    live_payload = {
        "success": True,
        "data": {
            "symbol": "BTC",
            "price": 11000.0,
            "timestamp": "2025-10-27T00:00:00",
            "source": "coingecko",
        },
        "metadata": {"source": "coingecko"},
    }

    monkeypatch.setattr(feeds, "_get_cached_response", no_cache)
    monkeypatch.setattr(feeds, "_check_rate_limit", allow)
    monkeypatch.setattr(feeds, "_handle_api_success", noop)
    monkeypatch.setattr(feeds, "_handle_api_failure", noop)
    monkeypatch.setattr(feeds, "_schedule_supabase_sync", lambda *args, **kwargs: None)

    async def fetch_success(_symbol: str):
        return copy.deepcopy(live_payload)

    monkeypatch.setattr(feeds, "_fetch_coingecko_price", fetch_success)
    monkeypatch.setattr(feeds, "_fetch_cryptocompare_price", fetch_success)
    monkeypatch.setattr(feeds, "_fetch_alpha_vantage_price", fetch_success)
    monkeypatch.setattr(feeds, "_fetch_finnhub_price", fetch_success)
    monkeypatch.setattr(feeds, "_fetch_coincap_price", fetch_success)

    result = await feeds.get_real_time_price("BTC")

    assert result["success"] is True
    metadata = result.get("metadata", {})
    assert metadata.get("served_from") == "live"
    assert metadata.get("cache_origin") == "coingecko"
    assert metadata.get("cache_ttl") == feeds.cache_ttl["price"]


@pytest.mark.asyncio
async def test_real_time_price_degrades_to_cached_payload(monkeypatch):
    feeds = MarketDataFeeds()
    feeds.redis = None

    cached_payload = {
        "success": True,
        "data": {
            "symbol": "BTC",
            "price": 12345.0,
            "timestamp": "2025-10-27T00:00:00",
            "source": "coingecko",
        },
        "metadata": {
            "source": "coingecko",
            "cached_at": (datetime.utcnow() - timedelta(minutes=4)).isoformat(),
        },
    }

    prepared_cached = feeds._prepare_cache_payload(cached_payload, "price")

    cache_sequence = [None, copy.deepcopy(prepared_cached)]

    async def sequenced_cache(_cache_key: str, ttl_key: str = "price"):
        value = cache_sequence.pop(0)
        if value is None:
            return None
        return feeds._apply_cache_metadata(copy.deepcopy(value), ttl_key)

    async def allow(*_, **__):
        return True

    async def noop(*_, **__):
        return None

    async def failing_fetch(_symbol: str):
        return {"success": False, "error": "unavailable"}

    monkeypatch.setattr(feeds, "_get_cached_response", sequenced_cache)
    monkeypatch.setattr(feeds, "_check_rate_limit", allow)
    monkeypatch.setattr(feeds, "_handle_api_success", noop)
    monkeypatch.setattr(feeds, "_handle_api_failure", noop)
    monkeypatch.setattr(feeds, "_schedule_supabase_sync", lambda *args, **kwargs: None)
    monkeypatch.setattr(feeds, "_fetch_coingecko_price", failing_fetch)
    monkeypatch.setattr(feeds, "_fetch_cryptocompare_price", failing_fetch)
    monkeypatch.setattr(feeds, "_fetch_alpha_vantage_price", failing_fetch)
    monkeypatch.setattr(feeds, "_fetch_finnhub_price", failing_fetch)
    monkeypatch.setattr(feeds, "_fetch_coincap_price", failing_fetch)

    result = await feeds.get_real_time_price("BTC")

    assert result["success"] is True
    metadata = result.get("metadata", {})
    assert metadata.get("served_from") == "cache"
    assert metadata.get("cache_degraded") is True
    assert metadata.get("stale") is True
    assert result["data"]["price"] == 12345.0
