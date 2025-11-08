"""End-to-end happy path covering login, discovery, portfolio, and chat flows."""

from __future__ import annotations

from datetime import datetime
import uuid
import types
from unittest.mock import AsyncMock

import pytest

from app.api.v1.endpoints import chat, opportunity_discovery, trading
from app.api.v1.endpoints.auth import get_current_user, get_database
from app.services.rate_limit import rate_limiter
from app.models.user import User, UserRole, UserStatus
from main import app as fastapi_app


@pytest.fixture(autouse=True)
def disable_rate_limits(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(return_value=True)
    monkeypatch.setattr(rate_limiter, "check_rate_limit", mock)
    return mock


@pytest.fixture
def auth_overrides(monkeypatch: pytest.MonkeyPatch):
    hashed_password = "$2b$12$opH8RUC1EsGbDHH.4ENAOOckmPzEZxVc3BfXM4nwceYOGGbyTMko2"
    fake_user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000101"),
        email="admin@cryptouniverse.com",
        hashed_password=hashed_password,
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        is_verified=True,
    )
    fake_user.exchange_accounts = []

    class DummyResult:
        def __init__(self, user: User):
            self._user = user

        def scalar_one_or_none(self) -> User:
            return self._user

    class DummySession:
        def __init__(self, user: User):
            self.user = user

        async def execute(self, statement):  # pragma: no cover - exercised implicitly
            return DummyResult(self.user)

        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

        async def refresh(self, _obj) -> None:
            return None

        async def close(self) -> None:
            return None

        def add(self, _obj) -> None:
            return None

    async def override_db():
        session = DummySession(fake_user)
        try:
            yield session
        finally:
            await session.close()

    fastapi_app.dependency_overrides[get_database] = override_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: fake_user

    yield {"user": fake_user}

    fastapi_app.dependency_overrides.pop(get_database, None)
    fastapi_app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def stub_opportunity_service(monkeypatch: pytest.MonkeyPatch) -> dict:
    base_opportunities = [
        {
            "strategy_id": "portfolio_optimizer",
            "strategy_name": "AI Portfolio Optimizer",
            "opportunity_type": "portfolio_optimization",
            "symbol": "BTC/USDT",
            "exchange": "demo-exchange",
            "profit_potential_usd": 1250.0,
            "confidence_score": 0.82,
            "risk_level": "balanced",
            "required_capital_usd": 5000.0,
            "estimated_timeframe": "1d",
            "entry_price": 52000.0,
            "exit_price": 53250.0,
            "metadata": {
                "strategy_used": "AI Portfolio Optimizer",
                "highlight": "Rebalance into outperforming assets",
            },
        },
        {
            "strategy_id": "risk_guardian",
            "strategy_name": "Risk Guardian",
            "opportunity_type": "risk_management",
            "symbol": "ETH/USDT",
            "exchange": "demo-exchange",
            "profit_potential_usd": 640.0,
            "confidence_score": 0.78,
            "risk_level": "conservative",
            "required_capital_usd": 2500.0,
            "estimated_timeframe": "4h",
            "entry_price": 3200.0,
            "exit_price": 3264.0,
            "metadata": {
                "strategy_used": "Risk Guardian",
                "highlight": "Trim overexposed positions",
            },
        },
    ]

    async def fake_async_init(self) -> None:  # type: ignore[override]
        self.redis = None

    async def fake_register(self, user_id: str, cache_key: str, scan_id: str) -> None:  # type: ignore[override]
        async with self._scan_lookup_lock:  # type: ignore[attr-defined]
            self._scan_lookup[scan_id] = cache_key  # type: ignore[attr-defined]
            self._user_latest_scan_key[user_id] = cache_key  # type: ignore[attr-defined]

    async def fake_discover(  # type: ignore[override]
        self,
        *,
        user_id: str,
        force_refresh: bool,
        include_strategy_recommendations: bool,
        symbols,
        asset_tiers,
        strategy_ids,
        scan_id: str,
        cache_key: str,
    ) -> dict:
        timestamp = datetime.utcnow().isoformat()
        opportunities = [
            {**opp, "discovered_at": timestamp}
            for opp in base_opportunities
        ]
        payload = {
            "scan_id": scan_id,
            "user_id": user_id,
            "opportunities": opportunities,
            "total_opportunities": len(opportunities),
            "user_profile": {"tier": "enterprise", "strategies": 2},
            "strategy_performance": {"AI Portfolio Optimizer": "+12.5%"},
            "asset_discovery": {"assets_scanned": 42},
            "strategy_recommendations": [
                {"strategy": "AI Portfolio Optimizer", "reason": "Top Sharpe"}
            ],
            "execution_time_ms": 42.0,
            "last_updated": timestamp,
        }
        await self._update_cached_scan_result(cache_key, payload, partial=False)
        return payload

    service = opportunity_discovery.user_opportunity_discovery
    monkeypatch.setattr(service, "async_init", types.MethodType(fake_async_init, service))
    monkeypatch.setattr(service, "_register_scan_lookup", types.MethodType(fake_register, service))
    monkeypatch.setattr(
        service,
        "discover_opportunities_for_user",
        types.MethodType(fake_discover, service),
    )

    return {"opportunities": base_opportunities}


@pytest.fixture
def stub_portfolio(monkeypatch: pytest.MonkeyPatch) -> dict:
    async def fake_portfolio_fetch(user_id: str, db):  # pragma: no cover - signature enforced by FastAPI
        return {
            "success": True,
            "total_value": 25000.0,
            "available_balance": 8000.0,
            "daily_pnl": 150.0,
            "total_pnl": 3200.0,
            "balances": [
                {
                    "asset": "BTC",
                    "total": 0.5,
                    "value_usd": 15000.0,
                    "change_24h_pct": 2.3,
                    "unrealized_pnl": 500.0,
                    "exchange": "demo-exchange",
                },
                {
                    "asset": "ETH",
                    "total": 2.0,
                    "value_usd": 10000.0,
                    "change_24h_pct": 1.2,
                    "unrealized_pnl": 200.0,
                    "exchange": "demo-exchange",
                },
            ],
        }

    async def fake_risk_status(user_id: str) -> dict:
        return {
            "success": True,
            "portfolio": {
                "risk_score": 4.2,
                "available_balance": 8000.0,
                "daily_pnl": 150.0,
                "total_pnl": 3200.0,
                "daily_pnl_pct": 0.6,
                "total_pnl_pct": 14.0,
                "margin_used": 0.0,
                "margin_available": 8000.0,
                "active_orders": 2,
            },
        }

    monkeypatch.setattr(
        "app.api.v1.endpoints.exchanges.get_user_portfolio_from_exchanges",
        fake_portfolio_fetch,
    )
    monkeypatch.setattr(trading.risk_service, "get_portfolio_status", fake_risk_status)

    return {"total_value": 25000.0, "available_balance": 8000.0}


@pytest.fixture
def stub_chat(monkeypatch: pytest.MonkeyPatch) -> str:
    response_text = (
        "Risk parity and adaptive rebalancing keep your portfolio aligned with market momentum."
    )

    class InMemoryChatMemory:
        def __init__(self) -> None:
            self.sessions: dict[str, dict] = {}
            self.messages: dict[str, list[dict[str, object]]] = {}

        async def create_session(
            self,
            *,
            user_id: str,
            session_type: str,
            context: dict | None = None,
            session_id: str | None = None,
        ) -> str:
            session_identifier = session_id or "test-session-123"
            self.sessions[session_identifier] = {
                "user_id": user_id,
                "session_type": session_type,
                "context": dict(context or {}),
                "is_active": True,
            }
            self.messages.setdefault(session_identifier, [])
            return session_identifier

        async def get_conversation_context(self, session_id: str) -> dict:
            session = self.sessions.get(session_id, {})
            return {"session_context": dict(session.get("context", {}))}

        async def update_session_context(self, session_id: str, updates: dict) -> bool:
            session = self.sessions.setdefault(session_id, {"context": {}})
            session.setdefault("context", {}).update(updates)
            return True

        async def add_message(
            self,
            *,
            session_id: str,
            user_id: str,
            message_type,
            content: str,
            metadata: dict | None = None,
            **_: object,
        ) -> str:
            message_id = "msg-" + str(len(self.messages.setdefault(session_id, [])) + 1)
            self.messages[session_id].append(
                {
                    "message_id": message_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "message_type": getattr(message_type, "value", str(message_type)),
                    "content": content,
                    "metadata": metadata or {},
                }
            )
            return message_id

        async def save_message(self, **kwargs) -> str:
            return await self.add_message(**kwargs)

        async def get_session_messages(self, session_id: str, limit: int) -> list[dict[str, object]]:
            return self.messages.get(session_id, [])[-limit:]

    stub_memory = InMemoryChatMemory()
    monkeypatch.setattr(chat.chat_engine, "memory_service", stub_memory)

    async def fake_process_message(
        self,
        message: str,
        user_id: str,
        session_id: str | None = None,
        **_: dict,
    ) -> dict:
        session_identifier = session_id or "test-session-123"
        return {
            "success": True,
            "session_id": session_identifier,
            "message_id": "msg-123",
            "content": response_text,
            "intent": "portfolio_recommendation",
            "confidence": 0.93,
            "metadata": {
                "strategies": ["risk parity", "adaptive rebalancing"],
            },
            "timestamp": datetime.utcnow(),
        }

    monkeypatch.setattr(
        chat.chat_engine,
        "process_message",
        types.MethodType(fake_process_message, chat.chat_engine),
    )
    return response_text


def test_full_system_flow(client, auth_overrides, stub_opportunity_service, stub_portfolio, stub_chat):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@cryptouniverse.com", "password": "AdminPass123!"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    discovery_response = client.post(
        "/api/v1/opportunities/discover",
        json={"scan_type": "comprehensive", "risk_tolerance": "balanced"},
        headers=auth_headers,
    )
    assert discovery_response.status_code == 200
    scan_id = discovery_response.json()["scan_id"]

    results_response = client.get(
        f"/api/v1/opportunities/results/{scan_id}", headers=auth_headers
    )
    assert results_response.status_code == 200
    results = results_response.json()
    assert results["total_opportunities"] == len(stub_opportunity_service["opportunities"])
    strategy_names = {item["strategy_name"] for item in results["opportunities"]}
    assert "AI Portfolio Optimizer" in strategy_names

    summary_response = client.get(
        "/api/v1/trading/portfolio/summary", headers=auth_headers
    )
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["success"] is True
    assert float(summary["total_value"]) == pytest.approx(stub_portfolio["total_value"])
    assert float(summary["available_balance"]) == pytest.approx(
        stub_portfolio["available_balance"]
    )

    chat_response = client.post(
        "/api/v1/chat/message",
        headers=auth_headers,
        json={"message": "What portfolio rebalancing strategies do you recommend?"},
    )
    assert chat_response.status_code == 200
    chat_payload = chat_response.json()
    assert chat_payload["success"] is True
    assert "risk parity" in chat_payload["content"].lower()
    assert "adaptive" in chat_payload["content"].lower()
