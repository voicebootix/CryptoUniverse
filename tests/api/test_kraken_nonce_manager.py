import asyncio
import os
import time
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.api.v1.endpoints.exchanges import KrakenNonceManager


@pytest.mark.asyncio
async def test_nonce_manager_uses_positional_eval(monkeypatch):
    manager = KrakenNonceManager()
    manager._redis = AsyncMock()
    manager._redis.eval = AsyncMock(return_value="123456")
    manager._lock = asyncio.Lock()
    manager._server_time_offset = 0
    manager._last_time_sync = time.time()

    monkeypatch.setattr(manager, "_init_redis", AsyncMock())
    monkeypatch.setattr(manager, "_sync_server_time", AsyncMock(return_value=True))

    result = await manager.get_nonce()

    assert result == 123456
    eval_args, eval_kwargs = manager._redis.eval.await_args
    assert eval_kwargs == {}
    assert "redis.call" in eval_args[0]
    assert eval_args[1] == 1
    assert eval_args[2] == manager._nonce_key
    assert eval_args[4] == "3600"
