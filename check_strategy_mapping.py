#!/usr/bin/env python3
"""
Check Strategy ID Mapping - Compare admin strategies vs scanner mappings
"""

import requests
import json
import os

def check_strategy_mapping():
    """Check the mapping between admin strategies and scanner functions."""
    print("🔍 CHECKING STRATEGY ID MAPPING")
    print("=" * 50)
    
    # Get credentials from environment variables
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    api_base_url = os.getenv("API_BASE_URL", "https://cryptouniverse.onrender.com")
    
    if not admin_email or not admin_password:
        raise ValueError("Missing required environment variables: ADMIN_EMAIL and ADMIN_PASSWORD must be set")
    
    # Login
    login_data = {"email": admin_email, "password": admin_password}
    login_url = f"{api_base_url.rstrip('/')}/api/v1/auth/login"
    
    try:
        response = requests.post(login_url, json=login_data, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error during login: {e}")
        return
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    try:
        response_data = response.json()
        if not response_data or 'access_token' not in response_data or not response_data['access_token']:
            print(f"❌ Invalid login response: missing or empty access_token")
            return
        token = response_data['access_token']
    except (ValueError, json.JSONDecodeError) as e:
        print(f"❌ Failed to parse login response: {e}")
        return
    
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("✅ Authentication successful")
    
    # Get admin's actual strategies
    portfolio_url = f"{api_base_url.rstrip('/')}/api/v1/unified-strategies/portfolio"
    
    try:
        portfolio_response = requests.get(portfolio_url, headers=headers, timeout=60)
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error during portfolio fetch: {e}")
        return
    
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
    
    try:
        with open('strategy_mapping_analysis.json', 'w') as f:
            json.dump(results, f, indent=2)
        print("\n💾 Results saved to: strategy_mapping_analysis.json")
    except (OSError, IOError) as e:
        print(f"❌ Failed to save results: {e}")
        return
    
    return results

if __name__ == "__main__":
    check_strategy_mapping()