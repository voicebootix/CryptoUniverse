import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.services.unified_ai_manager import (
    InterfaceType,
    unified_ai_manager,
)
from app.services.ai_chat_engine import ChatIntent, enhanced_chat_engine as chat_engine


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
