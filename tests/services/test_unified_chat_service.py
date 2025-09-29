import os
from datetime import datetime
from pathlib import Path
import sys
import uuid
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

from app.services.unified_chat_service import (
    ChatIntent,
    ChatSession,
    ConversationMode,
    InterfaceType,
    TradingMode,
    UnifiedChatService,
)


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
    assert trade_request_arg["action"] == "BUY"
    assert trade_request_arg["side"] == "buy"
    quantity = trade_request_arg.get("quantity")
    if quantity is not None:
        assert quantity == pytest.approx(0.25)
    else:
        assert trade_request_arg.get("position_size_usd") == pytest.approx(0.25)
    assert trade_request_arg["order_type"] == "MARKET"


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
            "simulation_result": {
                "quantity": 1.95,
                "execution_price": 2050.0,
            },
        }
    )

    rebalance_analysis = {
        "recommended_trades": [
            {
                "symbol": "ethusdt",
                "action": "buy",
                "amount": "4000",
                "reference_price": "2000",
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
    assert validation_request_arg["position_size_usd"] == 4000.0
    assert validation_request_arg["quantity"] == 2.0

    execution_call = service.trade_executor.execute_trade.await_args
    exec_request_arg, exec_user_arg, exec_simulation_mode = execution_call.args

    assert exec_user_arg == "user-abc"
    assert exec_simulation_mode is False
    assert exec_request_arg["symbol"] == "ETHUSDT"
    assert exec_request_arg["action"] == "BUY"
    assert exec_request_arg["side"] == "buy"
    assert exec_request_arg["quantity"] == 2.0
    assert exec_request_arg["order_type"] == "LIMIT"
    assert exec_request_arg["position_size_usd"] == 4000.0
    assert exec_request_arg["reference_price"] == 2000.0
    assert exec_request_arg["price"] == 2000.0

    assert result["success"] is True
    assert result["trades_executed"] == 1
    assert result["trades_failed"] == 0

    execution_metadata = result["results"][0]["rebalance_execution"]
    assert execution_metadata["requested_notional_usd"] == 4000.0
    assert execution_metadata["requested_quantity"] == 2.0
    assert execution_metadata["simulation_mode"] is False
    assert execution_metadata["filled_quantity"] == pytest.approx(1.95)
    assert execution_metadata["fill_price"] == pytest.approx(2050.0)
    assert execution_metadata["filled_value_usd"] == pytest.approx(1.95 * 2050.0)


@pytest.mark.asyncio
async def test_strategy_management_prefetches_portfolio_once():
    service = UnifiedChatService()

    portfolio_payload = {
        "success": True,
        "active_strategies": [
            {"id": "alpha", "name": "Alpha Momentum"}
        ],
        "total_strategies": 1,
    }
    marketplace_payload = {
        "strategies": [
            {"id": "beta", "name": "Beta Mean Reversion"}
        ]
    }

    service.strategy_marketplace.get_user_strategy_portfolio = AsyncMock(
        return_value=portfolio_payload
    )
    service.strategy_marketplace.get_marketplace_strategies = AsyncMock(
        return_value=marketplace_payload
    )

    service._analyze_intent_unified = AsyncMock(
        return_value={
            "intent": ChatIntent.STRATEGY_MANAGEMENT,
            "confidence": 0.92,
            "requires_action": False,
            "entities": {},
        }
    )

    expected_response = {"success": True, "content": "ok"}
    service._generate_complete_response = AsyncMock(return_value=expected_response)

    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    conversation_mode = ConversationMode.PAPER_TRADING

    service.sessions[session_id] = ChatSession(
        session_id=session_id,
        user_id=user_id,
        interface=InterfaceType.WEB_CHAT,
        conversation_mode=conversation_mode,
        trading_mode=TradingMode.BALANCED,
        created_at=datetime.utcnow(),
        last_activity=datetime.utcnow(),
        context={
            "interface": InterfaceType.WEB_CHAT.value,
            "conversation_mode": conversation_mode.value,
            "trading_mode": TradingMode.BALANCED.value,
        },
        messages=[],
    )

    result = await service.process_message(
        message="Show my strategies",
        user_id=user_id,
        session_id=session_id,
        conversation_mode=conversation_mode,
    )

    assert result == expected_response
    service.strategy_marketplace.get_user_strategy_portfolio.assert_awaited_once()
    service.strategy_marketplace.get_marketplace_strategies.assert_awaited_once()

    _, _, _, context_arg = service._generate_complete_response.await_args.args
    assert context_arg["user_strategies"] is portfolio_payload
    assert context_arg["marketplace_strategies"] is marketplace_payload
