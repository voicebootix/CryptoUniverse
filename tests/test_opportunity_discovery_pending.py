import asyncio
import contextlib
import os
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.services.user_opportunity_discovery import (
    UserOpportunityDiscoveryService,
    _CachedOpportunityResult,
)


@pytest.mark.asyncio
async def test_discover_returns_pending_placeholder(monkeypatch):
    service = UserOpportunityDiscoveryService()

    async def fake_get_cached_scan_entry(user_id: str) -> Any:
        return None

    async def fake_update_cached_scan_result(user_id: str, payload: dict, *, partial: bool) -> None:
        # Pretend we stored the payload successfully without touching Redis
        return None

    async def fake_execute(*args, **kwargs):
        await asyncio.sleep(0.05)
        return {"success": True, "opportunities": [{"id": "demo"}]}

    monkeypatch.setattr(service, "_get_cached_scan_entry", fake_get_cached_scan_entry)
    monkeypatch.setattr(service, "_update_cached_scan_result", fake_update_cached_scan_result)
    monkeypatch.setattr(service, "_execute_opportunity_discovery", fake_execute)
    monkeypatch.setattr(service, "_schedule_scan_cleanup", lambda *args, **kwargs: None)

    result = await service.discover_opportunities_for_user("user-test")

    assert result["success"] is True
    assert result["metadata"]["scan_state"] == "pending"
    assert result["background_scan"] is True

    # Ensure we clean up the background task to avoid warnings
    await asyncio.sleep(0)
    for task in list(service._scan_tasks.values()):
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_discover_returns_partial_cache(monkeypatch):
    service = UserOpportunityDiscoveryService()

    loop_time = asyncio.get_running_loop().time()
    cached_payload = {
        "success": True,
        "opportunities": [],
        "metadata": {
            "scan_state": "partial",
            "strategies_completed": 2,
            "total_strategies": 4,
        },
    }

    async def fake_get_cached_scan_entry(user_id: str) -> _CachedOpportunityResult:
        return _CachedOpportunityResult(
            payload=cached_payload,
            expires_at=loop_time + 60,
            partial=True,
        )

    async def fake_update_cached_scan_result(user_id: str, payload: dict, *, partial: bool) -> None:
        return None

    async def fake_execute(*args, **kwargs):
        return {"success": True, "opportunities": []}

    monkeypatch.setattr(service, "_get_cached_scan_entry", fake_get_cached_scan_entry)
    monkeypatch.setattr(service, "_update_cached_scan_result", fake_update_cached_scan_result)
    monkeypatch.setattr(service, "_execute_opportunity_discovery", fake_execute)
    monkeypatch.setattr(service, "_schedule_scan_cleanup", lambda *args, **kwargs: None)

    result = await service.discover_opportunities_for_user("user-test")

    assert result["metadata"]["scan_state"] == "partial"
    assert "message" in result["metadata"]

    for task in list(service._scan_tasks.values()):
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
