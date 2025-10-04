import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.api.v1.endpoints.telegram import _process_natural_language
from app.services.unified_ai_manager import InterfaceType as UnifiedInterfaceType


@pytest.mark.asyncio
async def test_telegram_natural_language_routes_through_unified_manager():
    connection = SimpleNamespace(
        user_id="user-123",
        telegram_chat_id="chat-456",
        telegram_username="alpha",
        id="conn-789",
        last_active_at=None,
    )

    prompts = [
        "How can you help me?",
        "What strategies do I have?",
        "Show me opportunities today",
    ]

    persona_responses = [
        "Here's how I support you day to day: I monitor risk, signal flow, and cash positioning so nothing slips.",
        "Right now you're running assisted trading with no autonomous strategies deployed—I can line up options whenever you're ready.",
        "I just reviewed 238 active setups and shortlisted three that align with your balanced profile.",
    ]

    ai_side_effects = [
        {"success": True, "action": "recommendation", "content": persona_responses[0], "confidence": 0.91},
        {"success": True, "action": "recommendation", "content": persona_responses[1], "confidence": 0.87},
        {"success": True, "action": "recommendation", "content": persona_responses[2], "confidence": 0.9},
    ]

    persona_manager = SimpleNamespace(process_user_request=AsyncMock(side_effect=ai_side_effects))

    with patch(
        "app.api.v1.endpoints.telegram.get_unified_persona_pipeline",
        return_value=(persona_manager, UnifiedInterfaceType),
    ):
        outputs = []
        for prompt in prompts:
            outputs.append(await _process_natural_language(connection, prompt, None))

    # Ensure the unified manager handled each prompt and produced the persona responses
    assert outputs == persona_responses

    # Confirm the persona tone remains narrative (no bullet characters) and context was forwarded properly
    mocked_manager = persona_manager.process_user_request
    for idx, call in enumerate(mocked_manager.await_args_list):
        kwargs = call.kwargs
        assert kwargs["interface"] == UnifiedInterfaceType.TELEGRAM
        assert kwargs["context"]["chat_id"] == connection.telegram_chat_id
        assert "•" not in outputs[idx]
