import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/app")

from app.services.market_analysis_core import MarketAnalysisService


@pytest.mark.asyncio
async def test_get_exchange_price_deduplicates_inflight_requests(monkeypatch):
    service = MarketAnalysisService()

    # Prevent redis access during the test
    monkeypatch.setattr(service, "_ensure_price_redis", AsyncMock())
    monkeypatch.setattr(service, "_load_price_from_redis", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_store_price_in_redis", AsyncMock())

    calls = {"count": 0}

    async def fake_fetch(exchange_key: str, symbols):
        calls["count"] += 1
        # Yield control so the second task waits on the same in-flight request
        await asyncio.sleep(0.01)
        return {symbols[0]: {"price": 42000.0, "exchange": exchange_key}}

    monkeypatch.setattr(service, "_fetch_bulk_symbol_prices", fake_fetch)

    results = await asyncio.gather(
        service.get_exchange_price("binance", "BTC/USDT"),
        service.get_exchange_price("binance", "BTC/USDT"),
    )

    assert calls["count"] == 1
    assert results[0]["price"] == 42000.0
    assert results[1]["price"] == 42000.0

    # A subsequent call should hit the local cache without triggering a fetch
    third = await service.get_exchange_price("binance", "BTC/USDT")
    assert calls["count"] == 1
    assert third["price"] == 42000.0
