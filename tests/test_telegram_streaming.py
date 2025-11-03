import os
from types import SimpleNamespace
from typing import List

import pytest
from unittest.mock import AsyncMock

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

from app.services.unified_ai_manager import UnifiedAIManager


class DummyTelegramAPI:
    def __init__(self):
        self.sent_messages: List[tuple] = []
        self.edited_messages: List[tuple] = []

    async def send_message(self, chat_id, text, parse_mode="Markdown", reply_markup=None, priority=None):
        message_id = len(self.sent_messages) + 1
        self.sent_messages.append((chat_id, text))
        return {"success": True, "message_id": message_id}

    async def edit_message_text(self, chat_id, message_id, text, parse_mode="Markdown"):
        self.edited_messages.append((chat_id, message_id, text))
        return {"success": True, "message_id": message_id}


@pytest.mark.asyncio
async def test_handle_telegram_request_streams_chunks(monkeypatch):
    telegram_api = DummyTelegramAPI()
    telegram_service = SimpleNamespace(
        telegram_api=telegram_api,
        message_router=SimpleNamespace(
            _render_unified_response=lambda payload: payload.get("content", "")
        ),
    )

    manager = UnifiedAIManager(telegram_service=telegram_service)

    async def fake_stream():
        yield {"type": "processing", "content": "Analyzing your request"}
        yield {
            "type": "progress",
            "progress": {"message": "Scanning opportunities", "percent": 25, "stage": "opportunities"},
        }
        yield {"type": "response", "content": "Top pick: BTC breakout."}
        yield {"type": "persona_enriched", "content": " Risk looks balanced.", "replaces_previous": False}
        yield {"type": "complete", "metadata": {"personality": "Alex"}}

    fake_service = SimpleNamespace(process_message=AsyncMock(return_value=fake_stream()))
    manager.chat_service = fake_service

    result = await manager.handle_telegram_request("chat-1", "user-1", "Find opportunities")

    assert result["success"] is True
    assert result.get("streamed") is True
    assert "BTC breakout" in result["response"]
    assert telegram_api.sent_messages, "expected at least one Telegram send"
    # Ensure we attempted to update the ongoing message as chunks arrived
    assert telegram_api.edited_messages, "expected streaming edits during response"


@pytest.mark.asyncio
async def test_handle_telegram_request_stream_fallback(monkeypatch):
    telegram_api = DummyTelegramAPI()
    telegram_service = SimpleNamespace(
        telegram_api=telegram_api,
        message_router=SimpleNamespace(
            _render_unified_response=lambda payload: payload.get("content", "")
        ),
    )

    manager = UnifiedAIManager(telegram_service=telegram_service)

    failing_service = SimpleNamespace(process_message=AsyncMock(side_effect=RuntimeError("stream disabled")))
    manager.chat_service = failing_service

    manager.process_user_request = AsyncMock(return_value={"success": True, "content": "Fallback answer"})

    result = await manager.handle_telegram_request("chat-2", "user-2", "status")

    assert result["success"] is True
    assert "Fallback" in result["response"]
    assert len(telegram_api.sent_messages) == 1
    manager.process_user_request.assert_awaited()


@pytest.mark.asyncio
async def test_handle_telegram_request_stream_error_chunk(monkeypatch):
    telegram_api = DummyTelegramAPI()
    telegram_service = SimpleNamespace(
        telegram_api=telegram_api,
        message_router=SimpleNamespace(
            _render_unified_response=lambda payload: payload.get("content", "")
        ),
    )

    manager = UnifiedAIManager(telegram_service=telegram_service)

    async def error_stream():
        yield {"type": "processing", "content": "Checking"}
        yield {"type": "error", "content": "Scan failed"}

    manager.chat_service = SimpleNamespace(process_message=AsyncMock(return_value=error_stream()))
    manager.process_user_request = AsyncMock()

    result = await manager.handle_telegram_request("chat-3", "user-3", "scan")

    assert result["success"] is False
    assert "Scan failed" in result["error"]
    # Should not fall back to the non-streaming pipeline once an error chunk is emitted
    manager.process_user_request.assert_not_called()
    # Error message should have been sent to the user
    assert any("Scan failed" in text for _, text in telegram_api.sent_messages)
