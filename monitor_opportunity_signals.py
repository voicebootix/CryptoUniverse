#!/usr/bin/env python3
"""Monitor opportunity discovery signals in real-time."""

import asyncio
import json
from datetime import datetime

async def monitor_signals():
    from app.services.user_opportunity_discovery import user_opportunity_discovery
    from app.services.trading_strategies import trading_strategies_service
    
    print("🔍 Monitoring opportunity signals...")
    
    # Test symbols
    test_symbols = ["BTC", "ETH", "BNB", "SOL", "MATIC"]
    
    for symbol in test_symbols:
        try:
            result = await trading_strategies_service.execute_strategy(
                function="spot_momentum_strategy",
                symbol=f"{symbol}/USDT",
                parameters={"timeframe": "4h"},
                user_id="7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af",
                simulation_mode=True
            )
            
            if result.get("success"):
                signals = result.get("execution_result", {}).get("signal", {})
                strength = signals.get("strength", 0)
                print(f"{symbol}: Signal strength = {strength:.2f} {'✅ QUALIFIES' if strength > 4.0 else '❌ TOO LOW'}")
        except Exception as e:
            print(f"{symbol}: Error - {str(e)}")

if __name__ == "__main__":
    asyncio.run(monitor_signals())
