import asyncio
from datetime import datetime
from typing import Dict

import pytest

from app.services.unified_chat_service import (
    UnifiedChatService,
    ChatIntent,
    ChatSession,
    InterfaceType,
    ConversationMode,
    TradingMode,
)


@pytest.mark.asyncio
async def test_gather_opportunity_context_uses_placeholder_and_caches(monkeypatch):
    service = UnifiedChatService()
    service._redis_initialized = True
    service.redis = None

    placeholder = service._get_placeholder_opportunities("user-test", scan_id="scan-123")

    async def fake_discover(user_id: str, **kwargs):
        await asyncio.sleep(0)
        return placeholder

    async def slow_optimization(user_id: str, user_config: Dict[str, str]):
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            raise

    scheduled = False

    def record_schedule(user_id: str, user_config: Dict[str, str]) -> None:
        nonlocal scheduled
        scheduled = True

    session = ChatSession(
        session_id="session-1",
        user_id="user-test",
        interface=InterfaceType.WEB_CHAT,
        conversation_mode=ConversationMode.LIVE_TRADING,
        trading_mode=TradingMode.BALANCED,
        created_at=datetime.utcnow(),
        last_activity=datetime.utcnow(),
        context={},
        messages=[],
    )

    monkeypatch.setattr(service, "opportunity_discovery", type("_S", (), {
        "discover_opportunities_for_user": staticmethod(fake_discover)
    })())
    monkeypatch.setattr(service, "_run_portfolio_optimization", slow_optimization)
    monkeypatch.setattr(service, "_schedule_portfolio_optimization_refresh", record_schedule)

    start = asyncio.get_running_loop().time()
    context = await service._gather_context_data(
        {"intent": ChatIntent.OPPORTUNITY_DISCOVERY},
        "user-test",
        session,
        user_config={"risk_tolerance": "balanced"},
    )
    elapsed = asyncio.get_running_loop().time() - start

    assert elapsed < 1.2, "gather_context should return immediately with placeholder"
    assert context["opportunities"]["scan_state"] == "pending"
    assert scheduled is True


@pytest.mark.asyncio
async def test_streaming_generator_emits_progress_before_completion():
    service = UnifiedChatService()
    service._redis_initialized = True
    service.redis = None

    placeholder = service._get_placeholder_opportunities("user-test", scan_id="scan-progress")
    await service._cache_opportunities("user-test", placeholder, partial=True)

    async def complete_context():
        await asyncio.sleep(0.2)
        return {"opportunities": [{"id": "ready"}], "metadata": {"scan_state": "complete"}}

    context_task = asyncio.create_task(complete_context())

    events = []
    async for update in service._stream_opportunity_discovery_immediate("user-test", context_task):
        events.append(update)

    progress_events = [event for event in events if event.get("type") == "progress"]
    assert progress_events, "expected at least one progress event before completion"
    assert any("__context__" in event for event in events)
