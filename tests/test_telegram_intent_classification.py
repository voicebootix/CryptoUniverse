import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.services.unified_ai_manager import (
    InterfaceType,
    unified_ai_manager,
)
from app.services.ai_chat_engine import ChatIntent, enhanced_chat_engine as chat_engine
from app.services.conversation.response_templates import ResponseTemplates


@pytest.mark.asyncio
async def test_greeting_intent_not_overridden_by_general_query(monkeypatch):
    async def fake_classify(message: str, context=None):  # pragma: no cover - signature compatibility
        return ChatIntent.GENERAL_QUERY

    monkeypatch.setattr(chat_engine, "_classify_intent", fake_classify, raising=False)

    result = await unified_ai_manager._classify_unified_intent(
        "Hi",
        InterfaceType.TELEGRAM,
        context={},
        state=None,
    )

    assert result.intent == "greeting"
    assert result.confidence >= 0.6


@pytest.mark.asyncio
async def test_general_query_retained_when_no_keywords(monkeypatch):
    async def fake_classify(message: str, context=None):  # pragma: no cover - signature compatibility
        return ChatIntent.GENERAL_QUERY

    monkeypatch.setattr(chat_engine, "_classify_intent", fake_classify, raising=False)

    result = await unified_ai_manager._classify_unified_intent(
        "What's on the agenda?",
        InterfaceType.TELEGRAM,
        context={},
        state=None,
    )

    assert result.intent == "general_query"
    assert result.confidence >= 0.35


class _PassthroughPersona:
    def apply(self, text: str, state=None, intent=None):  # pragma: no cover - simple passthrough
        return text


class _DummyState:
    risk_profile = "balanced"
    portfolio = {"total_value": 0}
    opportunities = []
    trading_mode = "balanced"
    credit = type("Credit", (), {  # pragma: no cover - simple struct
        "available_credits": 0,
        "profit_potential_usd": 0.0,
        "credit_to_usd_ratio": 1.0,
        "tier": "standard",
    })()
    strategies = type("Strategies", (), {
        "active": [],
        "marketplace_highlights": [],
    })()

    def summarize_holdings(self, limit: int = 3):  # pragma: no cover - unused helper
        return []

    @property
    def portfolio_value(self) -> float:  # pragma: no cover - deterministic
        return float(self.portfolio.get("total_value", 0))


@pytest.mark.asyncio
async def test_opportunity_routing_uses_user_discovery(monkeypatch):
    manager = unified_ai_manager

    class DummyDiscovery:
        def __init__(self):
            self.init_calls = 0
            self.calls = []

        async def async_init(self):
            self.init_calls += 1

        async def discover_opportunities_for_user(
            self,
            user_id: str,
            *,
            force_refresh: bool = False,
            include_strategy_recommendations: bool = True,
        ) -> dict:
            self.calls.append((user_id, force_refresh, include_strategy_recommendations))
            return {
                "success": True,
                "scan_state": "complete",
                "opportunities": [
                    {
                        "symbol": "BTC",
                        "direction": "long",
                        "win_probability": 0.62,
                        "risk_level": "medium",
                    }
                ],
            }

    dummy = DummyDiscovery()
    monkeypatch.setattr(manager, "opportunity_discovery", dummy, raising=False)

    async def fail_market(*args, **kwargs):  # pragma: no cover - ensures legacy path unused
        raise AssertionError("market_inefficiency_scanner should not be called")

    monkeypatch.setattr(manager.market_analysis, "market_inefficiency_scanner", fail_market, raising=False)

    result = await manager._route_to_service(
        "opportunity_discovery",
        "Run an opportunity scan",
        "user-123",
        context={},
        state=None,
    )

    assert dummy.init_calls == 1
    assert dummy.calls == [("user-123", False, False)]
    assert result["service"] == "opportunity_discovery"
    assert result["result"]["opportunities"]


def test_opportunity_response_returns_scan_message():
    templates = ResponseTemplates(persona=_PassthroughPersona())
    state = _DummyState()
    payload = {
        "message": "Opportunity scan started. Analyzing 3 strategies for opportunities...",
        "scan_state": "pending",
        "opportunities": [],
    }

    render = templates.render(
        intent="opportunity_discovery",
        request="Opportunity scan",
        recommendation={},
        service_result={
            "service": "opportunity_discovery",
            "method": "discover_opportunities_for_user",
            "result": payload,
        },
        state=state,
        ai_analysis=None,
        interface="telegram",
        requires_approval=False,
    )

    assert "Opportunity scan started" in render.content
    assert "update you" in render.content
    assert render.metadata["scan_state"] == "pending"
