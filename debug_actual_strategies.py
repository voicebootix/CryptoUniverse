#!/usr/bin/env python3
"""
Debug what strategies are actually available
"""

import requests
import json

def debug_actual_strategies():
    """Debug what strategies are actually available"""
    
    base_url = "https://cryptouniverse.onrender.com/api/v1"
    
    # Login
    login_data = {
        "email": "admin@cryptouniverse.com", 
        "password": "AdminPass123!"
    }
    
    response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=30)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 Debugging actual available strategies...")
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    
    # Get marketplace strategies
    print(f"\n1️⃣ All marketplace strategies:")
    try:
        response = requests.get(f"{base_url}/strategies/marketplace", headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            strategies = data.get('strategies', [])
            
            print(f"   Found {len(strategies)} strategies:")
            for i, strategy in enumerate(strategies):
                name = strategy.get('name', 'Unknown')
                strategy_id = strategy.get('strategy_id', 'Unknown')
                cost = strategy.get('credit_cost_monthly', 0)
                is_ai = strategy.get('is_ai_strategy', False)
                category = strategy.get('category', 'Unknown')
                
                print(f"      {i+1}. {name}")
                print(f"         ID: {strategy_id}")
                print(f"         Cost: ${cost}/month")
                print(f"         AI Strategy: {is_ai}")
                print(f"         Category: {category}")
                print()
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Get user's active strategies again to see the exact IDs
    print(f"\n2️⃣ User's active strategies (detailed):")
    try:
        response = requests.get(f"{base_url}/strategies/my-portfolio", headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            active_strategies = data.get('active_strategies', [])
            
            print(f"   User has {len(active_strategies)} active strategies:")
            for i, strategy in enumerate(active_strategies):
                name = strategy.get('name', 'Unknown')
                strategy_id = strategy.get('strategy_id', 'Unknown')
                category = strategy.get('category', 'Unknown')
                monthly_cost = strategy.get('monthly_cost', 0)
                
                print(f"      {i+1}. {name}")
                print(f"         ID: {strategy_id}")
                print(f"         Category: {category}")
                print(f"         Monthly cost: ${monthly_cost}")
                
                # Extract the function name that would be used
                if strategy_id.startswith("ai_"):
                    strategy_func = strategy_id.replace("ai_", "")
                    print(f"         Function name: {strategy_func}")
                print()
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Check what the opportunity discovery scanners are actually looking for
    print(f"\n3️⃣ Opportunity discovery scanner mapping:")
    
    # From the code, these are the scanners defined
    scanner_mapping = {
        "risk_management": "_scan_risk_management_opportunities",
        "portfolio_optimization": "_scan_portfolio_optimization_opportunities",
        "spot_momentum_strategy": "_scan_spot_momentum_opportunities",
        "spot_mean_reversion": "_scan_spot_mean_reversion_opportunities",
        "spot_breakout_strategy": "_scan_spot_breakout_opportunities",
        "scalping_strategy": "_scan_scalping_opportunities",
        "pairs_trading": "_scan_pairs_trading_opportunities",
        "statistical_arbitrage": "_scan_statistical_arbitrage_opportunities",
        "market_making": "_scan_market_making_opportunities",
        "futures_trade": "_scan_futures_trading_opportunities",
        "options_trade": "_scan_options_trading_opportunities",
        "funding_arbitrage": "_scan_funding_arbitrage_opportunities",
        "hedge_position": "_scan_hedge_opportunities",
        "complex_strategy": "_scan_complex_strategy_opportunities"
    }
    
    print(f"   Scanners defined in opportunity discovery service:")
    for func_name, scanner_method in scanner_mapping.items():
        print(f"      {func_name} → {scanner_method}")
    
    print(f"\n4️⃣ Analysis:")
    print(f"   The opportunity discovery service expects strategy function names like:")
    print(f"   - risk_management")
    print(f"   - portfolio_optimization") 
    print(f"   - spot_momentum_strategy")
    print(f"   ")
    print(f"   But the user's actual active strategies have IDs like:")
    print(f"   - ai_risk_management")
    print(f"   - ai_portfolio_optimization")
    print(f"   - ai_spot_momentum_strategy")
    print(f"   ")
    print(f"   The opportunity discovery service strips 'ai_' prefix to get function names.")
    print(f"   So the issue might be that the strategy service methods don't exist")
    print(f"   or have different names than expected.")

if __name__ == "__main__":
    debug_actual_strategies()