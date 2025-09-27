import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.services.unified_ai_manager import (  # noqa: E402
    UnifiedAIManager,
    AIDecision,
    InterfaceType,
    OperationMode,
)


def build_manager() -> UnifiedAIManager:
    manager = UnifiedAIManager.__new__(UnifiedAIManager)  # type: ignore
    manager.active_decisions = {}
    return manager


def build_decision(**overrides) -> AIDecision:
    base = {
        "decision_id": overrides.get("decision_id", "decision-123"),
        "user_id": overrides.get("user_id", "user-1"),
        "interface": overrides.get("interface", InterfaceType.WEB_CHAT),
        "operation_mode": overrides.get("operation_mode", OperationMode.ASSISTED),
        "intent": overrides.get("intent", "trade"),
        "decision_type": overrides.get("decision_type", "trade"),
        "recommendation": overrides.get("recommendation", {}),
        "confidence": overrides.get("confidence", 0.85),
        "risk_assessment": overrides.get("risk_assessment", {}),
        "requires_approval": overrides.get("requires_approval", True),
        "auto_execute": overrides.get("auto_execute", False),
        "timestamp": overrides.get("timestamp", datetime.utcnow()),
        "context": overrides.get("context", {}),
    }
    return AIDecision(**base)


def test_build_trade_request_handles_sparse_recommendations_defaults_to_market_order():
    manager = build_manager()

    recommendation = {
        "pair": "adausdt",
        "amount": 150,
        "analysis": "Structured breakout setup",
    }
    context = {
        "action": "buy",
        "opportunity_data": {"id": "opp-1"},
    }

    decision = build_decision(recommendation=recommendation, context=context)

    trade_request = manager._build_trade_request(decision)

    assert trade_request["symbol"] == "adausdt"
    assert trade_request["action"] == "buy"
    assert trade_request["amount"] == 150
    assert trade_request["order_type"] == "market"
    assert trade_request["opportunity_data"] == {"id": "opp-1"}
    assert "simulation_mode" not in trade_request


@pytest.mark.asyncio
async def test_execute_approved_decision_retains_queue_on_failure():
    manager = build_manager()
    failing_decision = build_decision(decision_id="decision-456")
    manager.active_decisions[failing_decision.decision_id] = failing_decision

    manager._execute_ai_decision = AsyncMock(return_value={"success": False, "error": "exchange down"})  # type: ignore[attr-defined]

    result = await manager.execute_approved_decision(failing_decision.decision_id, failing_decision.user_id)

    assert result["success"] is False
    assert failing_decision.decision_id in manager.active_decisions
    manager._execute_ai_decision.assert_awaited_once_with(failing_decision)  # type: ignore[attr-defined]
