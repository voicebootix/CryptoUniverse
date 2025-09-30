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

    context["user_config"] = {
        "risk_tolerance": "balanced",
        "investment_amount": 25000,
        "time_horizon": "medium_term",
        "investment_objectives": ["growth"],
        "constraints": [],
    }
    context["allowed_symbols"] = ["BTCUSDT"]
    context["portfolio_optimization"] = {
        "primary_strategy": "risk_parity",
        "strategies": [
            {
                "strategy": "risk_parity",
                "expected_return": 0.15,
                "expected_volatility": 0.09,
                "sharpe_ratio": 1.2,
                "confidence": 0.85,
                "result": {"weights": {"BTCUSDT": 0.15}},
                "suggested_trades": [
                    {
                        "symbol": "BTCUSDT",
                        "action": "buy",
                        "notional_value": 1500,
                        "quantity": 0.05,
                        "target_weight": 0.15,
                        "weight_change": 0.005,
                        "reference_price": 30000,
                    }
                ],
            }
        ],
    }

    prompt = service._build_response_prompt(
        "Show me portfolio optimization opportunities",
        ChatIntent.OPPORTUNITY_DISCOVERY,
        context,
    )

    assert "Expected annual return" in prompt
    assert "Target Allocation: 15.0%" in prompt
    assert "Suggested Trade Size: ≈ $1,500.00" in prompt


def test_profile_parser_extracts_amount_and_constraints():
    service = UnifiedChatService()

    message = "I can invest $20k, avoid leverage and DOGE, but otherwise flexible"
    updates = service._parse_investor_profile_response(
        message,
        list(service.INVESTOR_PROFILE_FIELDS),
    )

    assert updates.get("investment_amount") == pytest.approx(20000.0)
    constraints = updates.get("constraints")
    assert constraints is not None
    assert "no_leverage" in constraints


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


@pytest.mark.asyncio
async def test_strategy_guidance_requires_investor_profile_before_response():
    service = UnifiedChatService()

    # Avoid hitting external systems during the test
    service.memory_service.create_session = AsyncMock(return_value="session-test")
    service.memory_service.update_session_context = AsyncMock(return_value=True)
    service._analyze_intent_unified = AsyncMock(
        return_value={
            "intent": ChatIntent.OPPORTUNITY_DISCOVERY,
            "confidence": 0.88,
            "requires_action": False,
            "entities": {},
        }
    )
    service._gather_context_data = AsyncMock()
    service._generate_complete_response = AsyncMock()

    user_id = str(uuid.uuid4())

    first_response = await service.process_message(
        message="Find me the best opportunities",
        user_id=user_id,
        conversation_mode=ConversationMode.LIVE_TRADING,
    )

    assert first_response["success"] is False
    assert first_response["requires_action"] is True
    assert "risk tolerance" in first_response["content"].lower()
    service._generate_complete_response.assert_not_awaited()

    session_id = first_response["session_id"]
    pending_context = service.sessions[session_id].context
    assert "awaiting_profile_fields" in pending_context

    second_prompt = await service.process_message(
        message="I'm conservative with a long-term horizon focused on income",
        user_id=user_id,
        session_id=session_id,
        conversation_mode=ConversationMode.LIVE_TRADING,
    )

    assert second_prompt["success"] is False
    assert second_prompt.get("requires_action") is True
    assert "capital you want the plan to manage" in second_prompt["content"].lower()

    final_ack = await service.process_message(
        message="I can invest $15,000 and have no constraints",
        user_id=user_id,
        session_id=session_id,
        conversation_mode=ConversationMode.LIVE_TRADING,
    )

    assert final_ack["success"] is True
    assert final_ack.get("metadata", {}).get("preference_update") is True

    assert "awaiting_profile_fields" not in service.sessions[session_id].context

    stored_config = await service._get_user_config(user_id)
    assert stored_config.get("risk_tolerance") == "conservative"
    assert stored_config.get("time_horizon") == "long_term"
    assert stored_config.get("investment_amount") == pytest.approx(15000.0)
    assert stored_config.get("constraints") == []
    assert stored_config.get("investment_objectives") == ["income"]

    service._generate_complete_response.reset_mock()
    service._check_requirements = AsyncMock(
        return_value={
            "allowed": True,
            "message": "All checks passed",
            "user_config": {
                "risk_tolerance": "conservative",
                "investment_amount": 15000.0,
                "time_horizon": "long_term",
                "investment_objectives": ["income"],
                "constraints": [],
                "trading_mode": TradingMode.CONSERVATIVE.value,
                "operation_mode": "assisted",
            },
        },
    )

    service._gather_context_data.reset_mock()
    service._gather_context_data.return_value = {
        "opportunities": {"opportunities": [], "user_profile": {}},
        "user_config": {
            "risk_tolerance": "conservative",
            "investment_amount": 15000.0,
            "time_horizon": "long_term",
            "investment_objectives": ["income"],
            "constraints": [],
        },
    }

    service._generate_complete_response.return_value = {"success": True, "content": "ready"}

    final_response = await service.process_message(
        message="Find me the best opportunities",
        user_id=user_id,
        session_id=session_id,
        conversation_mode=ConversationMode.LIVE_TRADING,
    )

    assert final_response["success"] is True
    service._generate_complete_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_opportunity_prompts_reflect_profile_differences():
    service = UnifiedChatService()

    service.memory_service.create_session = AsyncMock(return_value="session-pref")
    service.memory_service.update_session_context = AsyncMock(return_value=True)
    service._save_conversation = AsyncMock(return_value=None)

    conservative_config = {
        "risk_tolerance": "conservative",
        "investment_amount": 20000.0,
        "time_horizon": "long_term",
        "investment_objectives": ["income"],
        "constraints": [],
        "trading_mode": TradingMode.CONSERVATIVE.value,
        "operation_mode": "assisted",
    }
    aggressive_config = {
        "risk_tolerance": "aggressive",
        "investment_amount": 5000.0,
        "time_horizon": "short_term",
        "investment_objectives": ["growth"],
        "constraints": ["no_leverage"],
        "trading_mode": TradingMode.AGGRESSIVE.value,
        "operation_mode": "assisted",
    }

    base_opportunities = [
        {
            "strategy_name": "AI Portfolio Optimization - Core",
            "symbol": "BTCUSDT",
            "confidence_score": 0.9,
            "profit_potential_usd": 1200,
            "metadata": {
                "risk_level": "low",
                "time_horizon": "long_term",
                "objective": "income",
                "amount": "10%",
            },
        },
        {
            "strategy_name": "High Beta Momentum",
            "symbol": "DOGEUSDT",
            "confidence_score": 0.75,
            "profit_potential_usd": 2500,
            "metadata": {
                "risk_level": "high",
                "time_horizon": "short_term",
                "objective": "growth",
                "amount": "8%",
            },
        },
    ]

    async def gather_context_side_effect(*args, **kwargs):
        user_config = kwargs.get("user_config") or {}
        risk = user_config.get("risk_tolerance", "balanced")
        if risk == "conservative":
            allowed = ["BTCUSDT"]
            strategy_tag = "risk_parity"
        else:
            allowed = ["BTCUSDT", "DOGEUSDT"]
            strategy_tag = "kelly_criterion"

        return {
            "opportunities": {
                "opportunities": list(base_opportunities),
                "user_profile": {"risk_profile": user_config.get("risk_tolerance", "balanced")},
            },
            "user_config": user_config,
            "allowed_symbols": allowed,
            "portfolio_optimization": {
                "primary_strategy": strategy_tag,
                "strategies": [
                    {
                        "strategy": strategy_tag,
                        "expected_return": 0.12 if risk == "conservative" else 0.25,
                        "expected_volatility": 0.06 if risk == "conservative" else 0.2,
                        "sharpe_ratio": 1.3,
                        "confidence": 0.8,
                        "result": {"weights": {symbol: 0.5 for symbol in allowed}},
                        "suggested_trades": [],
                    }
                ],
            },
        }

    service._analyze_intent_unified = AsyncMock(
        return_value={
            "intent": ChatIntent.OPPORTUNITY_DISCOVERY,
            "confidence": 0.95,
            "requires_action": False,
            "entities": {},
        }
    )

    service._check_requirements = AsyncMock(
        side_effect=[
            {
                "allowed": True,
                "message": "All checks passed",
                "user_config": conservative_config,
            },
            {
                "allowed": True,
                "message": "All checks passed",
                "user_config": aggressive_config,
            },
        ]
    )

    service._gather_context_data = AsyncMock(side_effect=gather_context_side_effect)
    service.chat_ai.generate_response = AsyncMock(
        return_value={"success": True, "content": "ok", "elapsed_time": 0.1}
    )

    conservative_response = await service.process_message(
        message="Share personalized opportunities",
        user_id="profile-user",
        conversation_mode=ConversationMode.LIVE_TRADING,
    )
    assert conservative_response["success"] is True

    conservative_prompt = service.chat_ai.generate_response.await_args_list[0].kwargs["prompt"]
    assert "BTCUSDT" in conservative_prompt
    assert "DOGEUSDT" not in conservative_prompt
    assert "risk tolerance conservative" in conservative_prompt.lower()

    aggressive_response = await service.process_message(
        message="Share personalized opportunities",
        user_id="profile-user",
        session_id=conservative_response["session_id"],
        conversation_mode=ConversationMode.LIVE_TRADING,
    )
    assert aggressive_response["success"] is True

    aggressive_prompt = service.chat_ai.generate_response.await_args_list[1].kwargs["prompt"]
    assert "DOGEUSDT" in aggressive_prompt
    assert "risk tolerance aggressive" in aggressive_prompt.lower()
