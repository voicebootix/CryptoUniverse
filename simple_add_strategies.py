#!/usr/bin/env python3
"""
Simple script to add sample strategies to Redis for testing My Trading Strategies dashboard.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def add_sample_data():
    """Add sample strategy data to Redis."""
    print("Adding sample strategy data to Redis...")

    try:
        from app.core.redis import get_redis_client

        # Get Redis client
        redis = await get_redis_client()
        if not redis:
            print("ERROR: Redis not available")
            return

        print("SUCCESS: Connected to Redis")

        # Admin user ID (assuming ID 1 for admin)
        user_id = "1"

        # Sample strategies
        strategies = ["ai_risk_management", "ai_portfolio_optimization", "ai_spot_momentum_strategy"]

        # Add strategies to user's portfolio
        for strategy_id in strategies:
            await redis.sadd(f"user_strategies:{user_id}", strategy_id)
            print(f"Added strategy: {strategy_id}")

        # Add portfolio summary
        summary_data = {
            "total_strategies": "3",
            "active_strategies": "3",
            "total_pnl_usd": "4291.50",
            "total_pnl_percentage": "0.085",
            "monthly_credit_cost": "5",
            "welcome_strategies": "2",
            "purchased_strategies": "1",
            "profit_potential_remaining": "5708.50",
            "profit_potential_used": "4291.50"
        }

        summary_key = f"portfolio_summary:{user_id}"
        await redis.hset(summary_key, mapping=summary_data)
        print("Added portfolio summary")

        # Verify data was added
        user_strategies = await redis.smembers(f"user_strategies:{user_id}")
        print(f"Verification: Found {len(user_strategies)} strategies in Redis")

        print("SUCCESS: Sample data added to Redis!")
        print("Now visit the My Trading Strategies dashboard to see real data")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(add_sample_data())