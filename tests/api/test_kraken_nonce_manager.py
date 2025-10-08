import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


@pytest.mark.asyncio
async def test_kraken_nonce_persists_without_redis(tmp_path, monkeypatch):
    state_path = tmp_path / "kraken_nonce_state.json"
    monkeypatch.setenv("KRAKEN_NONCE_STATE_PATH", str(state_path))

    from app.core import redis as redis_module

    async def _fail_redis():
        raise ConnectionError("redis unavailable")

    monkeypatch.setattr(redis_module, "get_redis_client", _fail_redis)

    from app.api.v1.endpoints.exchanges import KrakenNonceManager

    manager_one = KrakenNonceManager()
    first_nonce = await manager_one.get_nonce()

    assert state_path.exists()
    persisted_value = state_path.read_text()
    assert str(first_nonce) in persisted_value

    manager_two = KrakenNonceManager()
    second_nonce = await manager_two.get_nonce()

    assert second_nonce > first_nonce
