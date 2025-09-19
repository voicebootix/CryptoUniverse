"""
Unit tests for atomic paper trading reset functionality.

Tests race condition protection and concurrent operation serialization
as requested by CodeRabbit code review.
"""

import asyncio
import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.services.paper_trading_engine import PaperTradingEngine


class TestPaperTradingAtomicReset:
    """Test atomic reset operations and race condition protection."""

    @pytest.fixture
    async def engine(self):
        """Create paper trading engine with mocked Redis."""
        engine = PaperTradingEngine()
        engine.redis = AsyncMock()
        return engine

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return "test_user_123"

    @pytest.fixture
    def initial_portfolio(self, user_id):
        """Expected initial portfolio state after reset."""
        return {
            "user_id": user_id,
            "cash_balance": 10000.0,
            "total_value": 10000.0,
            "positions": [],
            "trade_history": [],
            "performance_metrics": {
                "total_trades": 0,
                "winning_trades": 0,
                "total_profit_loss": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "average_trade": 0.0,
                "win_rate": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0
            },
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }

    async def test_atomic_reset_success(self, engine, user_id):
        """Test successful atomic reset using Lua script."""
        # Mock successful Lua script execution
        engine.redis.eval.return_value = {"ok": "SUCCESS", "msg": "Portfolio reset atomically"}

        result = await engine.reset_paper_trading_account(user_id)

        assert result["success"] is True
        assert "atomic operation" in result["message"]
        assert result["virtual_portfolio"]["cash_balance"] == 10000.0
        assert result["virtual_portfolio"]["total_value"] == 10000.0

        # Verify Lua script was called with correct parameters
        engine.redis.eval.assert_called_once()
        call_args = engine.redis.eval.call_args
        assert "paper_portfolio:" + user_id in call_args[0]
        assert "paper_portfolio_lock:" + user_id in call_args[0]

    async def test_atomic_reset_lock_conflict(self, engine, user_id):
        """Test reset when another operation holds the lock."""
        # Mock lock conflict from Lua script
        engine.redis.eval.return_value = {"err": "LOCK_FAILED", "msg": "Another reset operation is in progress"}

        result = await engine.reset_paper_trading_account(user_id)

        assert result["success"] is False
        assert "Another reset operation is in progress" in result["error"]

    async def test_atomic_reset_fallback_on_lua_error(self, engine, user_id):
        """Test fallback to distributed lock when Lua script fails."""
        # Mock Lua script failure
        engine.redis.eval.side_effect = Exception("Lua scripting not supported")

        # Mock successful distributed lock fallback
        engine.redis.set.return_value = True  # Lock acquired
        engine.redis.delete.return_value = None  # Delete operations succeed

        # Mock setup_paper_trading_account for fallback
        engine.setup_paper_trading_account = AsyncMock(return_value={
            "success": True,
            "portfolio": {"cash_balance": 10000.0, "total_value": 10000.0}
        })

        result = await engine.reset_paper_trading_account(user_id)

        assert result["success"] is True
        assert "distributed lock" in result["message"]

        # Verify fallback methods were called
        engine.redis.set.assert_called_once()
        engine.setup_paper_trading_account.assert_called_once_with(user_id)

    async def test_distributed_lock_acquisition_failure(self, engine, user_id):
        """Test distributed lock fallback when lock cannot be acquired."""
        # Mock Lua script failure
        engine.redis.eval.side_effect = Exception("Lua scripting not supported")

        # Mock lock acquisition failure
        engine.redis.set.return_value = False

        result = await engine.reset_paper_trading_account(user_id)

        assert result["success"] is False
        assert "Another reset operation is in progress" in result["error"]

    @pytest.mark.asyncio
    async def test_concurrent_reset_operations_serialization(self, engine, user_id):
        """
        Test that concurrent reset requests are properly serialized.
        This is the key test requested by CodeRabbit.
        """
        reset_count = 0
        reset_results = []

        async def mock_eval(*args, **kwargs):
            nonlocal reset_count
            reset_count += 1

            # Simulate that only one operation gets the lock
            if reset_count == 1:
                # First request gets the lock and succeeds
                await asyncio.sleep(0.1)  # Simulate some processing time
                return {"ok": "SUCCESS", "msg": "Portfolio reset atomically"}
            else:
                # Other requests fail to get the lock
                return {"err": "LOCK_FAILED", "msg": "Another reset operation is in progress"}

        engine.redis.eval.side_effect = mock_eval

        # Spawn 5 concurrent reset operations
        tasks = []
        for i in range(5):
            task = asyncio.create_task(engine.reset_paper_trading_account(user_id))
            tasks.append(task)

        # Wait for all operations to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assertions for serialization
        successful_resets = [r for r in results if isinstance(r, dict) and r.get("success") is True]
        failed_resets = [r for r in results if isinstance(r, dict) and r.get("success") is False]

        # Exactly one should succeed, others should fail with lock conflict
        assert len(successful_resets) == 1, "Exactly one reset should succeed"
        assert len(failed_resets) == 4, "Four resets should fail due to lock conflicts"

        # Verify the successful reset has correct state
        successful_result = successful_resets[0]
        assert "atomic operation" in successful_result["message"]
        assert successful_result["virtual_portfolio"]["cash_balance"] == 10000.0

        # Verify failed resets have correct error messages
        for failed_result in failed_resets:
            assert "Another reset operation is in progress" in failed_result["error"]

    async def test_lock_cleanup_on_exception(self, engine, user_id):
        """Test that locks are properly cleaned up even when exceptions occur."""
        # Mock Lua script failure to trigger fallback
        engine.redis.eval.side_effect = Exception("Lua scripting not supported")

        # Mock successful lock acquisition
        engine.redis.set.return_value = True

        # Mock exception during reset operation
        engine.setup_paper_trading_account = AsyncMock(side_effect=Exception("Database error"))

        # Mock delete for lock cleanup
        engine.redis.delete = AsyncMock()

        # Execute reset (should fail but clean up lock)
        result = await engine.reset_paper_trading_account(user_id)

        assert result["success"] is False

        # Verify lock cleanup was attempted even after exception
        lock_key = f"paper_portfolio_lock:{user_id}"
        delete_calls = [call for call in engine.redis.delete.call_args_list
                       if lock_key in str(call)]
        assert len(delete_calls) >= 1, "Lock should be cleaned up after exception"

    async def test_idempotent_reset_behavior(self, engine, user_id):
        """Test that reset operations are idempotent."""
        # Mock successful Lua script execution
        engine.redis.eval.return_value = {"ok": "SUCCESS", "msg": "Portfolio reset atomically"}

        # Perform two consecutive resets
        result1 = await engine.reset_paper_trading_account(user_id)
        result2 = await engine.reset_paper_trading_account(user_id)

        # Both should succeed with identical results
        assert result1["success"] is True
        assert result2["success"] is True

        # Final states should be identical (idempotent)
        assert result1["virtual_portfolio"]["cash_balance"] == result2["virtual_portfolio"]["cash_balance"]
        assert result1["virtual_portfolio"]["total_value"] == result2["virtual_portfolio"]["total_value"]
        assert result1["virtual_portfolio"]["positions"] == result2["virtual_portfolio"]["positions"]

    async def test_redis_unavailable_handling(self, engine, user_id):
        """Test graceful handling when Redis is unavailable."""
        # Set Redis to None to simulate unavailability
        engine.redis = None

        result = await engine.reset_paper_trading_account(user_id)

        assert result["success"] is False
        assert "Paper trading storage unavailable" in result["error"]

    @pytest.mark.asyncio
    async def test_stress_test_concurrent_operations(self, engine, user_id):
        """Stress test with many concurrent operations to ensure robustness."""
        operation_count = 0
        max_concurrent_success = 1

        async def mock_eval_stress(*args, **kwargs):
            nonlocal operation_count
            operation_count += 1

            # Only allow one success per batch
            if operation_count <= max_concurrent_success:
                await asyncio.sleep(0.05)  # Short processing time
                return {"ok": "SUCCESS", "msg": "Portfolio reset atomically"}
            else:
                return {"err": "LOCK_FAILED", "msg": "Another reset operation is in progress"}

        engine.redis.eval.side_effect = mock_eval_stress

        # Spawn 20 concurrent operations (stress test)
        tasks = [
            asyncio.create_task(engine.reset_paper_trading_account(user_id))
            for _ in range(20)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify exactly one success and rest are properly handled
        successful_count = sum(1 for r in results
                             if isinstance(r, dict) and r.get("success") is True)
        failed_count = sum(1 for r in results
                          if isinstance(r, dict) and r.get("success") is False)

        assert successful_count == 1, "Exactly one operation should succeed under stress"
        assert failed_count == 19, "All other operations should fail gracefully"
        assert successful_count + failed_count == 20, "All operations should complete"


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_paper_trading_atomic_reset.py -v
    pytest.main([__file__, "-v"])