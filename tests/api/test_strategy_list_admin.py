"""Tests to ensure admin users see the full strategy catalog."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.v1.endpoints import auth as auth_endpoints
from app.api.v1.endpoints.auth import get_current_user, get_database
from app.middleware import auth as auth_middleware
from app.models.user import User, UserRole, UserStatus
from app.services.rate_limit import rate_limiter
from app.services.strategy_marketplace_service import strategy_marketplace_service
from main import app as fastapi_app


class _DummySession:
    async def execute(self, *_args, **_kwargs):  # pragma: no cover - unused path
        return self

    def scalar_one_or_none(self):  # pragma: no cover - unused path
        return None

    async def close(self):  # pragma: no cover - context cleanup
        return None


@pytest.fixture(autouse=True)
def disable_rate_limits(monkeypatch: pytest.MonkeyPatch):
    mock = AsyncMock(return_value=True)
    monkeypatch.setattr(rate_limiter, "check_rate_limit", mock)
    return mock


@pytest.fixture
def admin_user():
    return User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000111"),
        email="admin@cryptouniverse.com",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def override_dependencies(admin_user: User, monkeypatch: pytest.MonkeyPatch):
    async def _current_user_override():
        return admin_user

    fastapi_app.dependency_overrides[get_current_user] = _current_user_override

    async def _dummy_db():
        session = _DummySession()
        try:
            yield session
        finally:
            await session.close()

    fastapi_app.dependency_overrides[get_database] = _dummy_db

    monkeypatch.setattr(
        auth_endpoints.auth_service,
        "verify_token",
        lambda _token: {"type": "access", "sub": str(admin_user.id)},
    )

    async def _cached_user(_user_id, _db):
        return admin_user

    monkeypatch.setattr(auth_endpoints, "get_cached_user", _cached_user)

    monkeypatch.setattr(
        auth_middleware,
        "verify_access_token",
        lambda _token: {
            "sub": str(admin_user.id),
            "type": "access",
            "jti": "test-jti",
            "role": admin_user.role.value,
        },
    )

    yield

    fastapi_app.dependency_overrides.pop(get_current_user, None)
    fastapi_app.dependency_overrides.pop(get_database, None)


def _build_strategy(strategy_id: str, name: str) -> Dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "strategy_id": strategy_id,
        "name": name,
        "status": "active",
        "is_active": True,
        "total_trades": 10,
        "winning_trades": 6,
        "win_rate": 60.0,
        "total_pnl_usd": "125.5",
        "sharpe_ratio": 1.1,
        "activated_at": timestamp,
        "last_executed_at": timestamp,
    }


@pytest.mark.asyncio()
async def test_admin_list_uses_snapshot(monkeypatch: pytest.MonkeyPatch, override_dependencies):
    catalog = strategy_marketplace_service.ai_strategy_catalog
    expected_ids: List[str] = [f"ai_{key}" for key in catalog.keys()]

    degraded_portfolio = {
        "success": True,
        "active_strategies": [
            _build_strategy(strategy_id, f"Degraded {idx}")
            for idx, strategy_id in enumerate(expected_ids[:3])
        ],
        "total_strategies": 3,
    }

    admin_snapshot = {
        "success": True,
        "active_strategies": [
            _build_strategy(strategy_id, catalog[strategy_id.replace("ai_", "")]["name"])
            for strategy_id in expected_ids
        ],
        "total_strategies": len(expected_ids),
    }

    monkeypatch.setattr(
        strategy_marketplace_service,
        "get_user_strategy_portfolio",
        AsyncMock(return_value=degraded_portfolio),
    )
    monkeypatch.setattr(
        strategy_marketplace_service,
        "get_admin_portfolio_snapshot",
        AsyncMock(return_value=admin_snapshot),
    )

    async with AsyncClient(app=fastapi_app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/strategies/list",
            headers={
                "Authorization": "Bearer test-token",
                "host": "cryptouniverse.onrender.com",
            },
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(expected_ids)
    returned_ids = {item["strategy_id"] for item in data}
    for expected_id in expected_ids:
        assert expected_id in returned_ids
