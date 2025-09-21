#!/usr/bin/env python3
"""
Quick fix for marketplace timeout issue
Add timeout to pricing loader to prevent hanging
"""

import sys
import os

# Read the marketplace service file
marketplace_file = "app/services/strategy_marketplace_service.py"

try:
    with open(marketplace_file, 'r') as f:
        content = f.read()

    # Add timeout to ensure_pricing_loaded method
    timeout_fix = '''    async def ensure_pricing_loaded(self):
        """Ensure strategy pricing is loaded from admin settings with timeout."""
        if self.strategy_pricing is None:
            try:
                # Add timeout to prevent hanging
                import asyncio
                await asyncio.wait_for(
                    self._load_dynamic_strategy_pricing(),
                    timeout=5.0  # 5 second timeout
                )
            except asyncio.TimeoutError:
                logger.warning("Pricing loading timed out, using fallback")
                # Use fallback pricing immediately
                fallback_pricing = {
                    "futures_trade": 50, "options_trade": 45, "perpetual_trade": 40,
                    "leverage_position": 35, "complex_strategy": 60, "margin_status": 15,
                    "funding_arbitrage": 30, "basis_trade": 25, "options_chain": 20,
                    "calculate_greeks": 15, "liquidation_price": 10, "hedge_position": 25,
                    "spot_momentum_strategy": 30, "spot_breakout_strategy": 25,
                    "algorithmic_trading": 35, "pairs_trading": 30, "statistical_arbitrage": 40,
                    "scalping_strategy": 20, "swing_trading": 25, "position_management": 15,
                    "risk_management": 20, "portfolio_optimization": 35, "strategy_performance": 10,
                    "spot_mean_reversion": 20, "market_making": 25
                }
                self.strategy_pricing = fallback_pricing'''

    # Replace the ensure_pricing_loaded method
    old_method = '''    async def ensure_pricing_loaded(self):
        """Ensure strategy pricing is loaded from admin settings."""
        if self.strategy_pricing is None:
            await self._load_dynamic_strategy_pricing()'''

    if old_method in content:
        content = content.replace(old_method, timeout_fix)

        # Write back the fixed content
        with open(marketplace_file, 'w') as f:
            f.write(content)

        print("✅ Applied marketplace timeout fix")
        print("📝 Added 5-second timeout to pricing loader")
    else:
        print("❌ Could not find the method to replace")

except Exception as e:
    print(f"❌ Error applying fix: {e}")