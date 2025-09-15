
# Direct Redis provisioning script
import asyncio
from app.core.redis import get_redis_client

async def provision_all_strategies():
    redis = await get_redis_client()
    if redis:
        # Add all strategies to admin user
        for strategy_id in ['ai_futures_trade', 'ai_options_trade', 'ai_perpetual_trade', 'ai_leverage_position', 'ai_complex_strategy', 'ai_margin_status', 'ai_funding_arbitrage', 'ai_basis_trade', 'ai_options_chain', 'ai_calculate_greeks', 'ai_liquidation_price', 'ai_hedge_position', 'ai_spot_momentum_strategy', 'ai_spot_mean_reversion', 'ai_spot_breakout_strategy', 'ai_algorithmic_trading', 'ai_pairs_trading', 'ai_statistical_arbitrage', 'ai_market_making', 'ai_scalping_strategy', 'ai_swing_trading', 'ai_position_management', 'ai_risk_management', 'ai_portfolio_optimization', 'ai_strategy_performance']:
            await redis.sadd("user_strategies:ADMIN_USER_ID", strategy_id)
        
        print("✅ All strategies provisioned in Redis")
    else:
        print("❌ Redis not available")

# Run: python -c "import asyncio; asyncio.run(provision_all_strategies())"
