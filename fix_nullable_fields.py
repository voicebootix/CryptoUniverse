#!/usr/bin/env python3
"""
Fix for nullable numeric fields in opportunity scanners
"""

print("=== NULLABLE FIELDS FIX ===\n")

# Find all the lines that need fixing
fixes_needed = [
    {
        "file": "/workspace/app/services/user_opportunity_discovery.py",
        "line": 949,
        "current": 'profit_potential_usd=float(risk_mgmt.get("take_profit", 100))',
        "fixed": 'profit_potential_usd=float(risk_mgmt.get("take_profit") or 100)'
    },
    {
        "file": "/workspace/app/services/user_opportunity_discovery.py", 
        "line": 955,
        "current": 'exit_price=float(risk_mgmt.get("take_profit_price", 0)) if risk_mgmt.get("take_profit_price") else None',
        "fixed": 'exit_price=float(risk_mgmt.get("take_profit_price") or 0) if risk_mgmt.get("take_profit_price") is not None else None'
    }
]

print("Files and lines that need to be fixed:")
for fix in fixes_needed:
    print(f"\nFile: {fix['file']}")
    print(f"Line: {fix['line']}")
    print(f"Current: {fix['current']}")
    print(f"Fixed:   {fix['fixed']}")

print("\n\nLet's also check for similar patterns in other scanners...")

# Other scanners that might have the same issue
scanners = [
    "_scan_spot_mean_reversion_opportunities",
    "_scan_spot_breakout_opportunities", 
    "_scan_scalping_opportunities",
    "_scan_pairs_trading_opportunities",
    "_scan_statistical_arbitrage_opportunities",
    "_scan_market_making_opportunities",
    "_scan_futures_trading_opportunities",
    "_scan_options_trading_opportunities"
]

print("\nOther scanners to check:")
for scanner in scanners:
    print(f"  - {scanner}")