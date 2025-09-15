#!/usr/bin/env python3
"""
Comprehensive Marketplace Strategy Analysis

Analyze all strategies in the marketplace, their tiers, costs, and capabilities
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def analyze_marketplace():
    """Analyze all strategies in the marketplace."""
    
    print("🏪 COMPREHENSIVE MARKETPLACE STRATEGY ANALYSIS")
    print("=" * 80)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed")
        return [], {}
    
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ Authenticated successfully")
    
    # Get all marketplace strategies
    print(f"\n📊 FETCHING ALL MARKETPLACE STRATEGIES")
    print("=" * 60)
    
    response = session.get(f"{BASE_URL}/strategies/marketplace")
    
    if response.status_code != 200:
        print(f"❌ Marketplace fetch failed: {response.status_code}")
        return [], {}  # Return empty strategies and analysis to match expected tuple
    
    data = response.json()
    strategies = data.get("strategies", [])
    
    print(f"✅ Total strategies in marketplace: {len(strategies)}")
    print(f"   AI strategies: {data.get('ai_strategies_count', 0)}")
    print(f"   Community strategies: {data.get('community_strategies_count', 0)}")
    
    # Analyze each strategy
    print(f"\n📋 DETAILED STRATEGY ANALYSIS")
    print("=" * 60)
    
    strategy_analysis = {
        "by_tier": {"free": [], "basic": [], "pro": [], "enterprise": []},
        "by_category": {"spot": [], "derivatives": [], "algorithmic": [], "portfolio": []},
        "by_cost": {"free": [], "low_cost": [], "medium_cost": [], "high_cost": []},
        "total_analysis": {
            "total_strategies": len(strategies),
            "ai_strategies": 0,
            "community_strategies": 0,
            "free_strategies": 0,
            "paid_strategies": 0,
            "total_monthly_cost": 0
        }
    }
    
    for i, strategy in enumerate(strategies, 1):
        strategy_id = strategy.get("strategy_id", "unknown")
        name = strategy.get("name", "Unknown")
        category = strategy.get("category", "unknown")
        tier = strategy.get("tier", "unknown")
        monthly_cost = strategy.get("credit_cost_monthly", 0)
        execution_cost = strategy.get("credit_cost_per_execution", 0)
        is_ai = strategy.get("is_ai_strategy", False)
        risk_level = strategy.get("risk_level", "unknown")
        min_capital = strategy.get("min_capital_usd", 0)
        
        print(f"\n{i:2d}. {name}")
        print(f"    ID: {strategy_id}")
        print(f"    Category: {category}")
        print(f"    Tier: {tier}")
        print(f"    Monthly Cost: ${monthly_cost} credits")
        print(f"    Execution Cost: ${execution_cost} credits")
        print(f"    AI Strategy: {'Yes' if is_ai else 'No'}")
        print(f"    Risk Level: {risk_level}")
        print(f"    Min Capital: ${min_capital:,}")
        
        # Categorize strategies
        strategy_analysis["by_tier"][tier].append(strategy_id)
        strategy_analysis["by_category"][category].append(strategy_id)
        
        if monthly_cost == 0:
            strategy_analysis["by_cost"]["free"].append(strategy_id)
            strategy_analysis["total_analysis"]["free_strategies"] += 1
        elif monthly_cost <= 25:
            strategy_analysis["by_cost"]["low_cost"].append(strategy_id)
        elif monthly_cost <= 50:
            strategy_analysis["by_cost"]["medium_cost"].append(strategy_id)
        else:
            strategy_analysis["by_cost"]["high_cost"].append(strategy_id)
            
        if is_ai:
            strategy_analysis["total_analysis"]["ai_strategies"] += 1
        else:
            strategy_analysis["total_analysis"]["community_strategies"] += 1
            
        if monthly_cost > 0:
            strategy_analysis["total_analysis"]["paid_strategies"] += 1
            
        strategy_analysis["total_analysis"]["total_monthly_cost"] += monthly_cost
        
        # Show backtest results if available
        backtest = strategy.get("backtest_results", {})
        if backtest:
            print(f"    Backtest Return: {backtest.get('total_return', 0):.1f}%")
            print(f"    Sharpe Ratio: {backtest.get('sharpe_ratio', 0):.2f}")
            print(f"    Win Rate: {backtest.get('win_rate', 0):.1f}%")
            print(f"    Max Drawdown: {backtest.get('max_drawdown', 0):.1f}%")
    
    # Summary analysis
    print(f"\n📊 MARKETPLACE SUMMARY ANALYSIS")
    print("=" * 60)
    
    total = strategy_analysis["total_analysis"]
    print(f"Total Strategies: {total['total_strategies']}")
    print(f"AI Strategies: {total['ai_strategies']}")
    print(f"Community Strategies: {total['community_strategies']}")
    print(f"Free Strategies: {total['free_strategies']}")
    print(f"Paid Strategies: {total['paid_strategies']}")
    print(f"Total Monthly Cost (all strategies): ${total['total_monthly_cost']} credits")
    
    print(f"\n📈 BY TIER:")
    for tier, strategy_list in strategy_analysis["by_tier"].items():
        print(f"   {tier.capitalize()}: {len(strategy_list)} strategies")
    
    print(f"\n📈 BY CATEGORY:")
    for category, strategy_list in strategy_analysis["by_category"].items():
        print(f"   {category.capitalize()}: {len(strategy_list)} strategies")
    
    print(f"\n💰 BY COST:")
    for cost_tier, strategy_list in strategy_analysis["by_cost"].items():
        print(f"   {cost_tier.replace('_', ' ').title()}: {len(strategy_list)} strategies")
    
    return strategies, strategy_analysis

def test_strategy_accessibility(strategies):
    """Test strategy accessibility and credit requirements."""
    
    print(f"\n🔐 TESTING STRATEGY ACCESSIBILITY")
    print("=" * 60)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Test purchasing different tier strategies
    test_strategies = [
        {"id": "ai_risk_management", "tier": "free", "expected_cost": 0},
        {"id": "ai_spot_momentum_strategy", "tier": "free", "expected_cost": 0},
        {"id": "ai_portfolio_optimization", "tier": "free", "expected_cost": 0},
        {"id": "ai_pairs_trading", "tier": "pro", "expected_cost": 40},
        {"id": "ai_futures_trade", "tier": "pro", "expected_cost": 60},
        {"id": "ai_options_trade", "tier": "enterprise", "expected_cost": 75},
        {"id": "ai_complex_strategy", "tier": "enterprise", "expected_cost": 100}
    ]
    
    accessibility_results = []
    
    for strategy in test_strategies:
        strategy_id = strategy["id"]
        tier = strategy["tier"]
        expected_cost = strategy["expected_cost"]
        
        print(f"\n🎯 Testing: {strategy_id} ({tier} tier)")
        
        # Test purchase endpoint
        try:
            url = f"{BASE_URL}/strategies/purchase?strategy_id={strategy_id}&subscription_type=monthly"
            response = session.post(url)
            
            if response.status_code == 200:
                result = response.json()
                success = result.get("success", False)
                cost = result.get("cost", 0)
                message = result.get("message", "")
                
                print(f"   Purchase: {'✅' if success else '❌'}")
                print(f"   Cost: ${cost} credits (expected: ${expected_cost})")
                print(f"   Message: {message}")
                
                accessibility_results.append({
                    "strategy_id": strategy_id,
                    "tier": tier,
                    "accessible": success,
                    "actual_cost": cost,
                    "expected_cost": expected_cost,
                    "cost_match": cost == expected_cost
                })
            else:
                print(f"   ❌ Purchase failed: {response.status_code}")
                print(f"   Error: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Summary
    accessible_count = sum(1 for r in accessibility_results if r["accessible"])
    print(f"\n📊 ACCESSIBILITY SUMMARY:")
    print(f"   Tested strategies: {len(accessibility_results)}")
    print(f"   Accessible strategies: {accessible_count}")
    print(f"   Success rate: {accessible_count/len(accessibility_results)*100:.1f}%")
    
    return accessibility_results

def main():
    strategies, analysis = analyze_marketplace()
    accessibility = test_strategy_accessibility(strategies)
    
    print(f"\n🎯 COMPREHENSIVE MARKETPLACE ANALYSIS COMPLETE")
    print("=" * 80)
    
    return {
        "strategies": strategies,
        "analysis": analysis,
        "accessibility": accessibility
    }

if __name__ == "__main__":
    main()