import os
import types
import uuid
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///tmp/test.db")

from types import SimpleNamespace

from app.services.exchange_universe_service import (
    ExchangeUniverseService,
    _UserAssetPreferences,
)


class DummyAccount:
    def __init__(self, exchange_name: str, allowed_symbols=None):
        self.exchange_name = exchange_name
        self.allowed_symbols = allowed_symbols or []


@pytest.fixture
def exchange_service(monkeypatch):
    service = ExchangeUniverseService()

    async def noop_store(*args, **kwargs):
        return None

    async def noop_read(*args, **kwargs):
        return None

    async def noop_ensure(*args, **kwargs):
        return None

    monkeypatch.setattr(service, "_store_in_redis", noop_store)
    monkeypatch.setattr(service, "_read_from_redis", noop_read)
    monkeypatch.setattr(service, "_ensure_redis", noop_ensure)
    monkeypatch.setattr(service, "_get_user_asset_preferences", AsyncMock(return_value=None))

    class StubFilter:
        VOLUME_TIERS = (
            SimpleNamespace(name="tier_institutional", priority=1),
            SimpleNamespace(name="tier_professional", priority=3),
            SimpleNamespace(name="tier_retail", priority=4),
            SimpleNamespace(name="tier_any", priority=99),
        )

        async def get_assets_for_symbol_list(self, symbols):  # pragma: no cover - default noop
            return {}

    async def get_filter():
        return StubFilter()

    monkeypatch.setattr(service, "_get_asset_filter", get_filter)

    return service


def _bind(method, instance):
    return types.MethodType(method, instance)


@pytest.mark.asyncio
async def test_get_user_exchanges_prefers_cached_accounts(exchange_service):
    user_id = str(uuid.uuid4())

    async def first_fetch(self, _user_id):
        assert _user_id == user_id
        return [
            DummyAccount("binance"),
            DummyAccount("kraken"),
        ]

    exchange_service._fetch_exchange_accounts = _bind(first_fetch, exchange_service)

    exchanges = await exchange_service.get_user_exchanges(user_id)
    assert exchanges == ["binance", "kraken"]

    async def fail_fetch(self, _user_id):  # pragma: no cover - guard against extra DB hits
        raise AssertionError("exchange roster should be served from cache")

    exchange_service._fetch_exchange_accounts = _bind(fail_fetch, exchange_service)

    cached = await exchange_service.get_user_exchanges(user_id)
    assert cached == exchanges


@pytest.mark.asyncio
async def test_get_symbol_universe_uses_allowed_symbols(exchange_service, monkeypatch):
    user_id = str(uuid.uuid4())

    async def fetch_accounts(self, _user_id):
        return [
            DummyAccount("binance", ["btc", "eth", "sol"]),
            DummyAccount("kraken", ["ada"]),
        ]

    exchange_service._fetch_exchange_accounts = _bind(fetch_accounts, exchange_service)

    symbols = await exchange_service.get_symbol_universe(user_id, None, ["binance", "kraken"])
    assert set(symbols) == {"BTC", "ETH", "SOL", "ADA"}


@pytest.mark.asyncio
async def test_get_symbol_universe_falls_back_when_empty(exchange_service, monkeypatch):
    user_id = str(uuid.uuid4())

    async def fetch_accounts(self, _user_id):
        return [DummyAccount("binance")]

    async def fallback(self, limit, min_tier):
        assert min_tier == "tier_retail"
        return ["X", "Y", "Z"][: limit or 3]

    exchange_service._fetch_exchange_accounts = _bind(fetch_accounts, exchange_service)
    exchange_service._fallback_symbols = _bind(fallback, exchange_service)

    symbols = await exchange_service.get_symbol_universe(user_id, None, ["binance"], limit=2)
    assert symbols == ["X", "Y"]


@pytest.mark.asyncio
async def test_get_symbol_universe_respects_user_asset_preferences(exchange_service, monkeypatch):
    user_id = str(uuid.uuid4())

    async def fetch_accounts(self, _user_id):
        return [
            DummyAccount("binance", ["btc", "sol", "doge", "lowcap"]),
        ]

    class PrefFilter:
        VOLUME_TIERS = (
            SimpleNamespace(name="tier_institutional", priority=1),
            SimpleNamespace(name="tier_enterprise", priority=2),
            SimpleNamespace(name="tier_professional", priority=3),
            SimpleNamespace(name="tier_retail", priority=4),
            SimpleNamespace(name="tier_micro", priority=6),
            SimpleNamespace(name="tier_any", priority=99),
        )

        async def get_assets_for_symbol_list(self, symbols):
            return {
                "BTC": SimpleNamespace(tier="tier_institutional", volume_24h_usd=1_500_000_000),
                "SOL": SimpleNamespace(tier="tier_professional", volume_24h_usd=350_000_000),
                "DOGE": SimpleNamespace(tier="tier_retail", volume_24h_usd=150_000_000),
                "LOWCAP": SimpleNamespace(tier="tier_micro", volume_24h_usd=500_000),
            }

    async def prefs(_user_id):
        return _UserAssetPreferences(max_tier="tier_professional", symbol_limit=3)

    async def get_filter():
        return PrefFilter()

    exchange_service._fetch_exchange_accounts = _bind(fetch_accounts, exchange_service)
    exchange_service._get_user_asset_preferences = AsyncMock(side_effect=prefs)
    monkeypatch.setattr(exchange_service, "_get_asset_filter", get_filter)

    symbols = await exchange_service.get_symbol_universe(user_id, None, ["binance"])

    assert symbols == ["BTC", "SOL"]
    assert "LOWCAP" not in symbols
    assert len(symbols) <= 3
