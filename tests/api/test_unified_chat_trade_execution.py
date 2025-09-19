"""Integration-style tests for unified chat trade execution paths."""

import os
import sys
from pathlib import Path
import uuid
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.services.unified_chat_service import (  # pylint: disable=import-error
    ConversationMode,
    UnifiedChatService,
)


@pytest.fixture
def unified_service() -> UnifiedChatService:
    """Create a unified chat service with patched dependencies."""
    service = UnifiedChatService()

    service.market_analysis.analyze_trade_opportunity = AsyncMock(
        return_value={"analysis": "ok"}
    )
    service.ai_consensus.validate_trade_decision = AsyncMock(
        return_value={"approved": True}
    )
    service.trade_executor.validate_trade = AsyncMock(return_value={"valid": True})
    service.trade_executor.execute_trade = AsyncMock(
        return_value={"success": True, "trade_id": "live-trade"}
    )
    service.paper_trading.execute_paper_trade = AsyncMock(
        return_value={
            "success": True,
            "paper_trade": {"trade_id": "paper-trade"},
            "message": "paper ok",
        }
    )
    service._initiate_trade_monitoring = AsyncMock(
        return_value={"monitoring_active": True, "trade_id": "live-trade"}
    )

    return service


@pytest.mark.asyncio
async def test_live_trade_uses_simulation_false(unified_service: UnifiedChatService):
    """Ensure live trades call executor with simulation disabled when user opts in."""
    unified_service._get_user_simulation_mode = AsyncMock(return_value=False)

    result = await unified_service._execute_trade_with_validation(
        trade_params={
            "symbol": "BTCUSDT",
            "action": "buy",
            "quantity": 0.01,
            "order_type": "market",
        },
        user_id=str(uuid.uuid4()),
        conversation_mode=ConversationMode.LIVE_TRADING,
        context_data={"market_data": {"current_price": 50000}},
    )

    unified_service.trade_executor.execute_trade.assert_awaited_once()
    exec_args = unified_service.trade_executor.execute_trade.call_args.args
    assert exec_args[2] is False
    assert result["success"] is True


@pytest.mark.asyncio
async def test_live_trade_uses_simulation_true(unified_service: UnifiedChatService):
    """Ensure simulation-enabled users execute through the simulator flag."""
    unified_service._get_user_simulation_mode = AsyncMock(return_value=True)

    await unified_service._execute_trade_with_validation(
        trade_params={
            "symbol": "ETHUSDT",
            "action": "sell",
            "quantity": 0.02,
            "order_type": "limit",
        },
        user_id=str(uuid.uuid4()),
        conversation_mode=ConversationMode.LIVE_TRADING,
        context_data={"market_data": {"current_price": 3200}},
    )

    unified_service.trade_executor.execute_trade.assert_awaited_once()
    exec_args = unified_service.trade_executor.execute_trade.call_args.args
    assert exec_args[2] is True


@pytest.mark.asyncio
async def test_paper_trading_mode_uses_paper_engine(unified_service: UnifiedChatService):
    """Paper trading conversations should delegate to the paper engine."""
    unified_service._get_user_simulation_mode = AsyncMock(return_value=False)

    result = await unified_service._execute_trade_with_validation(
        trade_params={
            "symbol": "SOLUSDT",
            "action": "buy",
            "quantity": 5,
            "order_type": "market",
        },
        user_id=str(uuid.uuid4()),
        conversation_mode=ConversationMode.PAPER_TRADING,
        context_data={"market_data": {"current_price": 100}},
    )

    unified_service.paper_trading.execute_paper_trade.assert_awaited_once()
    unified_service.trade_executor.execute_trade.assert_not_awaited()
    unified_service._get_user_simulation_mode.assert_not_awaited()
    assert result["execution_details"]["paper_trade"]["trade_id"] == "paper-trade"
