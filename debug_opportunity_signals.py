#!/usr/bin/env python3
"""
Debug script to check signal generation in opportunity discovery.

This script will:
1. Check what strategies the user has
2. Test signal generation for each strategy
3. Log the signal strengths to understand why opportunities are 0
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Configure minimal logging
import structlog
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger()

async def debug_opportunity_signals():
    """Debug why opportunities are returning 0."""
    
    try:
        # Import services
        from app.services.user_opportunity_discovery import user_opportunity_discovery
        from app.services.strategy_marketplace_service import strategy_marketplace_service
        from app.services.trading_strategies import trading_strategies_service
        from app.services.dynamic_asset_filter import enterprise_asset_filter
        
        # Test user ID (admin)
        user_id = "7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af"
        
        logger.info("Starting opportunity signal debugging", user_id=user_id)
        
        # Initialize services
        logger.info("Initializing services...")
        await user_opportunity_discovery.async_init()
        await strategy_marketplace_service.async_init()
        await enterprise_asset_filter.async_init()
        
        # Get user's strategies
        logger.info("Getting user strategies...")
        portfolio = await strategy_marketplace_service.get_user_strategy_portfolio(user_id)
        
        if portfolio.get("success"):
            strategies = portfolio.get("active_strategies", [])
            logger.info(f"User has {len(strategies)} active strategies")
            
            for strategy in strategies:
                logger.info(f"Strategy: {strategy.get('name')} (ID: {strategy.get('strategy_id')})")
        else:
            logger.error("Failed to get user strategies", error=portfolio.get("error"))
            return
        
        # Get discovered assets
        logger.info("Getting discovered assets...")
        discovered_assets = await enterprise_asset_filter.discover_all_assets(
            tier_limit="tier_retail"
        )
        
        total_assets = sum(len(assets) for assets in discovered_assets.values())
        logger.info(f"Discovered {total_assets} total assets across tiers")
        
        # Test specific strategy scanners with lower thresholds
        logger.info("Testing strategy scanners with debug logging...")
        
        # Patch the threshold temporarily for testing
        original_scan_method = user_opportunity_discovery._scan_spot_momentum_opportunities
        
        async def patched_scan_momentum(discovered_assets, user_profile, scan_id):
            """Patched scanner with debug logging."""
            opportunities = []
            
            # Get top symbols
            symbols = user_opportunity_discovery._get_top_symbols_by_volume(discovered_assets, limit=10)
            logger.info(f"Testing momentum on symbols: {symbols}")
            
            for symbol in symbols:
                try:
                    # Execute strategy
                    result = await trading_strategies_service.execute_strategy(
                        function="spot_momentum_strategy",
                        symbol=f"{symbol}/USDT",
                        parameters={"timeframe": "4h"},
                        user_id=user_profile.user_id,
                        simulation_mode=True
                    )
                    
                    if result.get("success"):
                        execution_result = result.get("execution_result", {})
                        signals = execution_result.get("signal", {})
                        
                        signal_strength = signals.get("strength", 0)
                        signal_confidence = signals.get("confidence", 0)
                        signal_action = signals.get("action", "HOLD")
                        
                        # LOG ALL SIGNALS regardless of strength
                        logger.info(
                            "MOMENTUM SIGNAL",
                            symbol=symbol,
                            signal_strength=signal_strength,
                            signal_confidence=signal_confidence,
                            signal_action=signal_action,
                            would_qualify_at_6=signal_strength > 6.0,
                            would_qualify_at_5=signal_strength > 5.0,
                            would_qualify_at_4=signal_strength > 4.0,
                            would_qualify_at_3=signal_strength > 3.0
                        )
                        
                except Exception as e:
                    logger.error(f"Error testing {symbol}", error=str(e))
            
            return opportunities
        
        # Temporarily replace the scanner
        user_opportunity_discovery._scan_spot_momentum_opportunities = patched_scan_momentum
        
        # Run discovery with debug logging
        logger.info("Running full opportunity discovery with debug logging...")
        discovery_result = await user_opportunity_discovery.discover_opportunities_for_user(
            user_id=user_id,
            force_refresh=True
        )
        
        logger.info(
            "Discovery completed",
            success=discovery_result.get("success"),
            opportunities_found=len(discovery_result.get("opportunities", [])),
            error=discovery_result.get("error")
        )
        
        # Log the signal strength distribution
        if discovery_result.get("success"):
            logger.info("=== SIGNAL ANALYSIS SUMMARY ===")
            logger.info("The issue appears to be that signal strengths are below the threshold of 6.0")
            logger.info("Consider lowering the threshold or adjusting the signal calculation")
        
        # Save debug results
        debug_file = f"debug_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(debug_file, 'w') as f:
            json.dump({
                "user_id": user_id,
                "strategies": strategies,
                "total_assets_discovered": total_assets,
                "discovery_result": discovery_result
            }, f, indent=2)
        
        logger.info(f"Debug results saved to {debug_file}")
        
    except Exception as e:
        logger.error("Debug script failed", error=str(e), exc_info=True)


if __name__ == "__main__":
    asyncio.run(debug_opportunity_signals())