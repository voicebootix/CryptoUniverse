from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.api.v1.endpoints import exchanges


@pytest.mark.asyncio
async def test_get_nonce_uses_db_fallback_when_redis_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = exchanges.KrakenNonceManager()

    async def fake_init_redis() -> None:
        manager._redis = None
        if manager._lock is None:
            manager._lock = asyncio.Lock()

    monkeypatch.setattr(manager, "_init_redis", fake_init_redis)
    monkeypatch.setattr(manager, "_get_db_managed_nonce", AsyncMock(return_value=1700000000500))

    api_key = "api-key-123"
    nonce = await manager.get_nonce(api_key)

    assert nonce == 1700000000500
    manager._get_db_managed_nonce.assert_awaited_once()  # type: ignore[attr-defined]
    storage_key = manager._storage_key(api_key)
    assert manager._fallback_nonce_cache[storage_key] == nonce


@pytest.mark.asyncio
async def test_clear_key_state_resets_caches_and_deletes_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = exchanges.KrakenNonceManager()
    storage_key = manager._storage_key("api-key-abc")
    manager._fallback_nonce_cache[storage_key] = 123
    manager._local_call_counts[storage_key] = 7

    fake_redis = AsyncMock()
    manager._redis = fake_redis

    await manager.clear_key_state("api-key-abc")

    assert storage_key not in manager._fallback_nonce_cache
    assert storage_key not in manager._local_call_counts
    fake_redis.delete.assert_awaited_once_with(manager._redis_key(storage_key))


@pytest.mark.asyncio
async def test_retry_with_backoff_flags_resync_on_invalid_nonce(monkeypatch: pytest.MonkeyPatch) -> None:
    original_manager = exchanges.kraken_nonce_manager
    test_manager = exchanges.KrakenNonceManager()
    exchanges.kraken_nonce_manager = test_manager

    async def failing_call() -> None:
        raise exchanges.ExchangeAPIError("kraken", "EAPI:Invalid nonce")

    sleep_mock = AsyncMock()
    monkeypatch.setattr(exchanges.asyncio, "sleep", sleep_mock)

    try:
        with pytest.raises(exchanges.ExchangeAPIError):
            await exchanges.retry_with_backoff(failing_call, max_retries=2, base_delay=0)

        assert test_manager._force_resync is True
        sleep_mock.assert_awaited()  # ensure backoff invoked at least once
    finally:
        exchanges.kraken_nonce_manager = original_manager
