#!/usr/bin/env python3
"""
Check Strategy ID Mapping - Compare admin strategies vs scanner mappings
"""

import requests
import json

def check_strategy_mapping():
    """Check the mapping between admin strategies and scanner functions."""
    print("🔍 CHECKING STRATEGY ID MAPPING")
    print("=" * 50)
    
    # Login
    login_data = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
    response = requests.post("https://cryptouniverse.onrender.com/api/v1/auth/login", json=login_data, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("✅ Authentication successful")
    
    # Get admin's actual strategies
    portfolio_response = requests.get(
        "https://cryptouniverse.onrender.com/api/v1/unified-strategies/portfolio",
        headers=headers,
        timeout=60
    )
    
    if portfolio_response.status_code != 200:
        print(f"❌ Portfolio fetch failed: {portfolio_response.status_code}")
        return
    
    portfolio_data = portfolio_response.json()
    admin_strategies = portfolio_data.get('active_strategies', [])
    
    print(f"\n📊 ADMIN'S ACTUAL STRATEGIES ({len(admin_strategies)}):")
    admin_strategy_ids = []
    for strategy in admin_strategies:
        strategy_id = strategy.get('strategy_id', '')
        strategy_name = strategy.get('name', '')
        print(f"   - {strategy_id}: {strategy_name}")
        admin_strategy_ids.append(strategy_id)
    
    # Define scanner mappings
    scanner_mappings = {
        "risk_management": "ai_risk_management",
        "portfolio_optimization": "ai_portfolio_optimization", 
        "spot_momentum_strategy": "ai_spot_momentum_strategy",
        "spot_mean_reversion": "ai_spot_mean_reversion",
        "spot_breakout_strategy": "ai_spot_breakout_strategy",
        "scalping_strategy": "ai_scalping_strategy",
        "pairs_trading": "ai_pairs_trading",
        "statistical_arbitrage": "ai_statistical_arbitrage",
        "market_making": "ai_market_making",
        "futures_trade": "ai_futures_trade",
        "options_trade": "ai_options_trade",
        "funding_arbitrage": "ai_funding_arbitrage",
        "hedge_position": "ai_hedge_position",
        "complex_strategy": "ai_complex_strategy"
    }
    
    print(f"\n📊 SCANNER MAPPINGS ({len(scanner_mappings)}):")
    for scanner_id, expected_strategy_id in scanner_mappings.items():
        print(f"   - {scanner_id} -> {expected_strategy_id}")
    
    # Check mapping status
    print(f"\n🔍 MAPPING ANALYSIS:")
    
    mapped_strategies = []
    unmapped_strategies = []
    missing_strategies = []
    
    # Check which admin strategies are mapped
    for strategy_id in admin_strategy_ids:
        if strategy_id in scanner_mappings.values():
            mapped_strategies.append(strategy_id)
        else:
            unmapped_strategies.append(strategy_id)
    
    # Check which scanner mappings are missing
    for scanner_id, expected_strategy_id in scanner_mappings.items():
        if expected_strategy_id not in admin_strategy_ids:
            missing_strategies.append((scanner_id, expected_strategy_id))
    
    print(f"\n✅ MAPPED STRATEGIES ({len(mapped_strategies)}):")
    for strategy_id in mapped_strategies:
        print(f"   - {strategy_id}")
    
    print(f"\n❌ UNMAPPED STRATEGIES ({len(unmapped_strategies)}):")
    for strategy_id in unmapped_strategies:
        print(f"   - {strategy_id}")
    
    print(f"\n⚠️  MISSING STRATEGIES ({len(missing_strategies)}):")
    for scanner_id, expected_strategy_id in missing_strategies:
        print(f"   - {scanner_id} expects {expected_strategy_id}")
    
    # Summary
    mapping_rate = (len(mapped_strategies) / len(admin_strategy_ids)) * 100 if admin_strategy_ids else 0
    print(f"\n📈 MAPPING RATE: {mapping_rate:.1f}% ({len(mapped_strategies)}/{len(admin_strategy_ids)})")
    
    if mapping_rate >= 80:
        print("🎉 EXCELLENT: Most strategies are properly mapped!")
    elif mapping_rate >= 50:
        print("✅ GOOD: Half the strategies are mapped!")
    elif mapping_rate >= 25:
        print("⚠️  PARTIAL: Some strategies are mapped!")
    else:
        print("❌ POOR: Most strategies are not mapped!")
    
    # Save results
    results = {
        "admin_strategies": admin_strategy_ids,
        "scanner_mappings": scanner_mappings,
        "mapped_strategies": mapped_strategies,
        "unmapped_strategies": unmapped_strategies,
        "missing_strategies": missing_strategies,
        "mapping_rate": mapping_rate
    }
    
    with open('strategy_mapping_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: strategy_mapping_analysis.json")
    
    return results

if __name__ == "__main__":
    check_strategy_mapping()