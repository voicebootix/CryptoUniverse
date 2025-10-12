import asyncio
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

from app.services import user_opportunity_discovery as discovery_module


@pytest.mark.asyncio
async def test_portfolio_fetch_waits_for_extended_timeout(monkeypatch):
    """The production regression was caused by a 15s timeout.

    Verify the service now passes the 45s configuration all the way into
    asyncio.wait_for so the marketplace call can run long enough for the
    14-strategy portfolios that previously timed out."""

    captured = {}

    original_wait_for = discovery_module.asyncio.wait_for

    async def fake_wait_for(awaitable, timeout):
        captured["timeout"] = timeout
        return await original_wait_for(awaitable, timeout=timeout)

    async def fake_get_portfolio(user_id: str):
        await asyncio.sleep(0)
        return {"success": True, "active_strategies": [1] * 14}

    monkeypatch.setattr(discovery_module.asyncio, "wait_for", fake_wait_for)
    monkeypatch.setattr(
        discovery_module.strategy_marketplace_service,
        "get_user_strategy_portfolio",
        fake_get_portfolio,
    )

    service = discovery_module.UserOpportunityDiscoveryService()

    result = await service._get_user_portfolio_cached("user-123")

    assert result["active_strategies"], "expected the stubbed portfolio to pass through"
    assert (
        captured["timeout"] == discovery_module.PORTFOLIO_FETCH_TIMEOUT_SECONDS
    ), "the marketplace fetch should wait for the full 45 seconds"

