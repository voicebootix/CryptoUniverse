#!/usr/bin/env python3
"""
Strategy Audit - Comprehensive audit of all 35 strategies to identify:
1. Duplicates
2. Placeholders
3. What's actually implemented
4. Strategy ID mapping issues
"""

import requests
import json
from datetime import datetime
from collections import defaultdict

def audit_strategies():
    """Audit all 35 strategies to identify duplicates, placeholders, and implementations."""
    
    print("🔍 COMPREHENSIVE STRATEGY AUDIT")
    print("Analyzing all 35 strategies to identify duplicates, placeholders, and implementations")
    
    base_url = "https://cryptouniverse.onrender.com"
    
    # Get auth token
    print("\n1. Getting authentication token...")
    login_data = {
        'email': 'admin@cryptouniverse.com',
        'password': 'AdminPass123!'
    }
    
    login_response = requests.post(f'{base_url}/api/v1/auth/login', json=login_data, timeout=30)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    token = login_response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print(f"✅ Token received: {token[:20]}...")
    
    # Get user's strategies
    print("\n2. Getting user's strategies...")
    try:
        portfolio_response = requests.get(
            f'{base_url}/api/v1/unified-strategies/portfolio', 
            headers=headers, 
            timeout=60
        )
        
        if portfolio_response.status_code == 200:
            portfolio_data = portfolio_response.json()
            strategies = portfolio_data.get('active_strategies', [])
            print(f"✅ Retrieved {len(strategies)} strategies")
            
            # Analyze strategies
            print(f"\n3. Analyzing strategies...")
            
            # Group by name to find duplicates
            name_groups = defaultdict(list)
            id_groups = defaultdict(list)
            
            for i, strategy in enumerate(strategies):
                strategy_id = strategy.get('strategy_id', '')
                strategy_name = strategy.get('name', '')
                
                name_groups[strategy_name].append((i, strategy_id))
                id_groups[strategy_id].append((i, strategy_name))
            
            # Find duplicates by name
            print(f"\n📊 DUPLICATE ANALYSIS BY NAME:")
            duplicates_by_name = {name: items for name, items in name_groups.items() if len(items) > 1}
            if duplicates_by_name:
                for name, items in duplicates_by_name.items():
                    print(f"   🔄 DUPLICATE: '{name}' appears {len(items)} times:")
                    for idx, strategy_id in items:
                        print(f"      - Index {idx}: {strategy_id}")
            else:
                print(f"   ✅ No duplicates found by name")
            
            # Find duplicates by ID
            print(f"\n📊 DUPLICATE ANALYSIS BY ID:")
            duplicates_by_id = {strategy_id: items for strategy_id, items in id_groups.items() if len(items) > 1}
            if duplicates_by_id:
                for strategy_id, items in duplicates_by_id.items():
                    print(f"   🔄 DUPLICATE: '{strategy_id}' appears {len(items)} times:")
                    for idx, strategy_name in items:
                        print(f"      - Index {idx}: {strategy_name}")
            else:
                print(f"   ✅ No duplicates found by ID")
            
            # Categorize strategies
            print(f"\n📊 STRATEGY CATEGORIZATION:")
            
            # Known working scanners
            working_scanners = {
                "ai_risk_management": "risk_management",
                "ai_portfolio_optimization": "portfolio_optimization", 
                "ai_spot_momentum_strategy": "spot_momentum_strategy",
                "ai_statistical_arbitrage": "statistical_arbitrage",
                "ai_market_making": "market_making",
                "ai_pairs_trading": "pairs_trading",
                "ai_funding_arbitrage": "funding_arbitrage",
                "ai_spot_mean_reversion": "spot_mean_reversion",
                "ai_spot_breakout_strategy": "spot_breakout_strategy",
                "ai_scalping_strategy": "scalping_strategy",
                "ai_futures_trade": "futures_trade",
                "ai_options_trade": "options_trade"
            }
            
            # Placeholder scanners
            placeholder_scanners = {
                "ai_hedge_position": "hedge_position",
                "ai_complex_strategy": "complex_strategy"
            }
            
            # Categorize each strategy
            working_strategies = []
            placeholder_strategies = []
            unmapped_strategies = []
            uuid_strategies = []
            
            for i, strategy in enumerate(strategies):
                strategy_id = strategy.get('strategy_id', '')
                strategy_name = strategy.get('name', '')
                
                # Check if it's a UUID (placeholder)
                if len(strategy_id) == 36 and strategy_id.count('-') == 4:
                    uuid_strategies.append((i, strategy_id, strategy_name))
                # Check if it maps to working scanner
                elif strategy_id in working_scanners:
                    working_strategies.append((i, strategy_id, strategy_name))
                # Check if it maps to placeholder scanner
                elif strategy_id in placeholder_scanners:
                    placeholder_strategies.append((i, strategy_id, strategy_name))
                # Check if it can be mapped with transformations
                elif any(candidate in working_scanners for candidate in [
                    strategy_id.replace("ai_", ""),
                    f"ai_{strategy_id}",
                    strategy_id.replace("_strategy", ""),
                    strategy_id.replace("_trading", ""),
                    strategy_id.replace("_arbitrage", ""),
                    strategy_id.replace("_strategies", "")
                ]):
                    # Try to find the mapping
                    mapped = False
                    for candidate in [
                        strategy_id.replace("ai_", ""),
                        f"ai_{strategy_id}",
                        strategy_id.replace("_strategy", ""),
                        strategy_id.replace("_trading", ""),
                        strategy_id.replace("_arbitrage", ""),
                        strategy_id.replace("_strategies", "")
                    ]:
                        if candidate in working_scanners:
                            working_strategies.append((i, strategy_id, strategy_name, f"→ {candidate}"))
                            mapped = True
                            break
                    if not mapped:
                        unmapped_strategies.append((i, strategy_id, strategy_name))
                else:
                    unmapped_strategies.append((i, strategy_id, strategy_name))
            
            # Print categorization results
            print(f"\n   ✅ WORKING STRATEGIES ({len(working_strategies)}):")
            for idx, strategy_id, strategy_name, *extra in working_strategies:
                extra_info = f" {extra[0]}" if extra else ""
                print(f"      {idx:2d}. {strategy_id:40s} - {strategy_name}{extra_info}")
            
            print(f"\n   ⚠️  PLACEHOLDER STRATEGIES ({len(placeholder_strategies)}):")
            for idx, strategy_id, strategy_name in placeholder_strategies:
                print(f"      {idx:2d}. {strategy_id:40s} - {strategy_name}")
            
            print(f"\n   🔄 UUID STRATEGIES (likely placeholders) ({len(uuid_strategies)}):")
            for idx, strategy_id, strategy_name in uuid_strategies:
                print(f"      {idx:2d}. {strategy_id:40s} - {strategy_name}")
            
            print(f"\n   ❌ UNMAPPED STRATEGIES ({len(unmapped_strategies)}):")
            for idx, strategy_id, strategy_name in unmapped_strategies:
                print(f"      {idx:2d}. {strategy_id:40s} - {strategy_name}")
            
            # Summary
            print(f"\n📊 AUDIT SUMMARY:")
            print(f"   Total strategies: {len(strategies)}")
            print(f"   Working strategies: {len(working_strategies)}")
            print(f"   Placeholder strategies: {len(placeholder_strategies)}")
            print(f"   UUID strategies (placeholders): {len(uuid_strategies)}")
            print(f"   Unmapped strategies: {len(unmapped_strategies)}")
            print(f"   Duplicates by name: {len(duplicates_by_name)}")
            print(f"   Duplicates by ID: {len(duplicates_by_id)}")
            
            # Recommendations
            print(f"\n💡 RECOMMENDATIONS:")
            print(f"   1. Remove {len(uuid_strategies)} UUID-based placeholder strategies")
            print(f"   2. Implement scanners for {len(unmapped_strategies)} unmapped strategies")
            print(f"   3. Complete {len(placeholder_strategies)} placeholder implementations")
            print(f"   4. Fix {len(duplicates_by_name)} duplicate strategy names")
            print(f"   5. Focus on {len(working_strategies)} working strategies for immediate opportunities")
            
            # Save detailed audit results
            audit_results = {
                "total_strategies": len(strategies),
                "working_strategies": [{"index": idx, "id": strategy_id, "name": strategy_name, "mapping": extra[0] if extra else None} for idx, strategy_id, strategy_name, *extra in working_strategies],
                "placeholder_strategies": [{"index": idx, "id": strategy_id, "name": strategy_name} for idx, strategy_id, strategy_name in placeholder_strategies],
                "uuid_strategies": [{"index": idx, "id": strategy_id, "name": strategy_name} for idx, strategy_id, strategy_name in uuid_strategies],
                "unmapped_strategies": [{"index": idx, "id": strategy_id, "name": strategy_name} for idx, strategy_id, strategy_name in unmapped_strategies],
                "duplicates_by_name": {name: [{"index": idx, "id": strategy_id} for idx, strategy_id in items] for name, items in duplicates_by_name.items()},
                "duplicates_by_id": {strategy_id: [{"index": idx, "name": strategy_name} for idx, strategy_name in items] for strategy_id, items in duplicates_by_id.items()},
                "audit_timestamp": datetime.now().isoformat()
            }
            
            with open(f'/workspace/strategy_audit_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
                json.dump(audit_results, f, indent=2, default=str)
            
            print(f"\n💾 Detailed audit results saved to strategy_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            return audit_results
            
        else:
            print(f"❌ Portfolio failed: {portfolio_response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"💥 Portfolio error: {e}")
        return None

if __name__ == "__main__":
    audit_strategies()