import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
# NOTE:
# The production application uses PostgreSQL via the asyncpg driver.  Our test
# suite swaps the database URL to an on-disk SQLite database powered by
# aiosqlite so tests can run without provisioning PostgreSQL.  The async driver
# must therefore be installed in dev/test environments.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.services.unified_chat_service import ChatIntent, UnifiedChatService


def test_unified_chat_service_initializes_key_attributes():
    service = UnifiedChatService()

    assert hasattr(service, "personalities")
    assert hasattr(service, "intent_patterns")


@pytest.mark.asyncio
async def test_trade_execution_pipeline_builds_structured_request():
    service = UnifiedChatService()

    service.market_analysis.analyze_trade_opportunity = AsyncMock(
        return_value={"opportunity": True}
    )
    service.ai_consensus.validate_trade_decision = AsyncMock(
        return_value={"approved": True}
    )

    original_validate_trade = service.trade_executor.validate_trade

    async def _wrapped_validate(trade_request, user_id):
        return await original_validate_trade(trade_request, user_id)

    service.trade_executor.validate_trade = AsyncMock(side_effect=_wrapped_validate)

    service.trade_executor.execute_trade = AsyncMock(
        return_value={
            "success": True,
            "trade_id": "trade-123",
            "simulation_result": {"order_id": "SIM-001", "status": "FILLED"},
        }
    )

    service._initiate_trade_monitoring = AsyncMock(
        return_value={"monitoring_active": True}
    )

    trade_params = {
        "symbol": "BTCUSDT",
        "action": "buy",
        "amount": 0.25,
        "order_type": "market",
        "simulation_mode": True,
    }

    result = await service._execute_trade_with_validation(trade_params, "user-123")

    assert result["success"] is True
    service.trade_executor.validate_trade.assert_awaited_once()
    service.trade_executor.execute_trade.assert_awaited_once()

    execution_call = service.trade_executor.execute_trade.await_args
    trade_request_arg, user_id_arg, simulation_mode_arg = execution_call.args

    assert user_id_arg == "user-123"
    assert simulation_mode_arg is True
    assert isinstance(trade_request_arg, dict)
    assert trade_request_arg["symbol"] == "BTCUSDT"
    assert trade_request_arg["action"].upper() == "BUY"
    assert trade_request_arg.get("side", trade_request_arg["action"].lower()) == "buy"
    quantity = trade_request_arg.get("quantity")
    if quantity is not None:
        assert quantity == pytest.approx(0.25)
    else:
        position_size = trade_request_arg.get("position_size_usd")
        amount_field = trade_request_arg.get("amount")
        if position_size is not None:
            assert position_size == pytest.approx(0.25)
        else:
            assert amount_field == pytest.approx(0.25)
    assert trade_request_arg["order_type"].upper() == "MARKET"


@pytest.mark.asyncio
async def test_rebalancing_normalizes_and_executes_structured_trades():
    service = UnifiedChatService()

    service.trade_executor.validate_trade = AsyncMock(
        return_value={
            "valid": True,
            "trade_request": {
                "symbol": "ETHUSDT",
                "action": "BUY",
                "side": "buy",
                "quantity": 2.0,
                "order_type": "LIMIT",
            },
        }
    )

    service.trade_executor.execute_trade = AsyncMock(
        return_value={
            "success": True,
            "trade_id": "trade-456",
        }
    )

    rebalance_analysis = {
        "recommended_trades": [
            {
                "symbol": "ethusdt",
                "action": "buy",
                "amount": "2",
                "order_type": "limit",
                "simulation_mode": "false",
            }
        ]
    }

    result = await service._execute_rebalancing(rebalance_analysis, "user-abc")

    service.trade_executor.validate_trade.assert_awaited_once()
    service.trade_executor.execute_trade.assert_awaited_once()

    validation_call = service.trade_executor.validate_trade.await_args
    validation_request_arg, validation_user_arg = validation_call.args

    assert validation_user_arg == "user-abc"
    assert validation_request_arg["symbol"] == "ethusdt"
    assert validation_request_arg["action"] == "buy"

    execution_call = service.trade_executor.execute_trade.await_args
    exec_request_arg, exec_user_arg, exec_simulation_mode = execution_call.args

    assert exec_user_arg == "user-abc"
    assert exec_simulation_mode is False
    assert exec_request_arg["symbol"] == "ETHUSDT"
    assert exec_request_arg["action"] == "BUY"
    assert exec_request_arg["side"] == "buy"
    assert exec_request_arg["quantity"] == 2.0
    assert exec_request_arg["order_type"] == "LIMIT"

    assert result["success"] is True
    assert result["trades_executed"] == 1
    assert result["trades_failed"] == 0


def test_opportunity_prompt_uses_fractional_weights_and_trade_values():
    service = UnifiedChatService()

    context = {
        "opportunities": {
            "opportunities": [
                {
                    "strategy_name": "AI Portfolio Optimization - Core",
                    "symbol": "BTCUSDT",
                    "confidence_score": 0.82,
                    "profit_potential_usd": 1250,
                    "required_capital_usd": 1500,
                    "metadata": {
                        "strategy": "core_balanced",
                        "amount": "15%",
                        "target_weight": "15%",
                        "weight_change": "0.5%",
                        "trade_value_usd": 1500,
                    },
                }
            ],
            "user_profile": {"risk_profile": "balanced"},
        }
    }

    prompt = service._build_response_prompt(
        "Show me portfolio optimization opportunities",
        ChatIntent.OPPORTUNITY_DISCOVERY,
        context,
    )

    assert "Allocation Target: 15.0% of portfolio" in prompt
    assert "Weight Change: 0.5%" in prompt
    assert "Trade Size: ≈ $1,500.00" in prompt
