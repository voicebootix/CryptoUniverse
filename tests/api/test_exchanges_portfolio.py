import asyncio
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.api.v1.endpoints.exchanges import (
    ApiKeyStatus,
    ExchangeStatus,
    ExchangeAPIError,
    get_user_portfolio_from_exchanges,
)


class DummyResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


@pytest.mark.asyncio
async def test_portfolio_aggregation_flags_failures(monkeypatch):
    user_id = "user-test"

    account = SimpleNamespace(
        id=uuid4(),
        exchange_name="Kraken",
        status=ExchangeStatus.ACTIVE.value,
    )
    api_key = SimpleNamespace(
        id=uuid4(),
        status=ApiKeyStatus.ACTIVE.value,
    )

    async def failing_fetch(*_args, **_kwargs):
        raise ExchangeAPIError("kraken", "Invalid nonce")

    db_mock = SimpleNamespace()

    async def execute_stub(*_args, **_kwargs):
        return DummyResult([(account, api_key)])

    db_mock.execute = execute_stub

    monkeypatch.setattr(
        "app.api.v1.endpoints.exchanges.fetch_exchange_balances",
        failing_fetch,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.exchanges.settings.PARALLEL_EXCHANGE_FETCHING",
        False,
        raising=False,
    )

    result = await get_user_portfolio_from_exchanges(user_id, db_mock)

    assert result["success"] is False
    assert result["overall_status"] == "critical"
    assert result["performance_metrics"]["failed_exchanges"] == 1
    assert result["performance_metrics"]["successful_exchanges"] == 0
    assert result["exchanges"][0]["success"] is False
