#!/usr/bin/env python3
"""
Check for duplications in the codebase
"""

import re

def check_duplications():
    """Check for function duplications."""
    
    print("🔍 CHECKING FOR DUPLICATIONS")
    print("=" * 50)
    
    # Read the trading strategies file
    with open('/workspace/app/services/trading_strategies.py', 'r') as f:
        content = f.read()
    
    # Find all function definitions
    function_pattern = r'async def (\w+)\('
    functions = re.findall(function_pattern, content)
    
    # Count occurrences
    function_counts = {}
    for func in functions:
        function_counts[func] = function_counts.get(func, 0) + 1
    
    # Find duplicates
    duplicates = {func: count for func, count in function_counts.items() if count > 1}
    
    print(f"Total functions found: {len(functions)}")
    print(f"Unique functions: {len(function_counts)}")
    print(f"Duplicated functions: {len(duplicates)}")
    
    if duplicates:
        print(f"\n❌ DUPLICATIONS FOUND:")
        for func, count in duplicates.items():
            print(f"   {func}: {count} times")
    else:
        print(f"\n✅ NO DUPLICATIONS FOUND")
    
    # Check for specific strategy functions
    strategy_functions = [
        "funding_arbitrage", "calculate_greeks", "swing_trading",
        "leverage_position", "margin_status", "options_chain",
        "basis_trade", "liquidation_price", "hedge_position",
        "algorithmic_trading", "strategy_performance"
    ]
    
    print(f"\n📊 STRATEGY FUNCTION CHECK:")
    for func in strategy_functions:
        count = function_counts.get(func, 0)
        status = "✅" if count == 1 else "❌" if count > 1 else "⚠️"
        print(f"   {status} {func}: {count} implementation(s)")
    
    return duplicates

if __name__ == "__main__":
    check_duplications()