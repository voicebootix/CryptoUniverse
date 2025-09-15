#!/usr/bin/env python3
"""
Complete Marketplace Analysis - Fixed Version

Get comprehensive analysis of all marketplace strategies
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def get_complete_marketplace_data():
    """Get complete marketplace data and analyze it."""
    
    print("🏪 COMPLETE MARKETPLACE ANALYSIS")
    print("=" * 80)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed")
        return
    
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ Authenticated successfully")
    
    # Get marketplace strategies
    print(f"\n📊 MARKETPLACE STRATEGIES")
    print("=" * 60)
    
    response = session.get(f"{BASE_URL}/strategies/marketplace")
    
    if response.status_code == 200:
        marketplace_data = response.json()
        strategies = marketplace_data.get("strategies", [])
        
        print(f"✅ Total strategies: {len(strategies)}")
        print(f"   AI strategies: {marketplace_data.get('ai_strategies_count', 0)}")
        print(f"   Community strategies: {marketplace_data.get('community_strategies_count', 0)}")
        
        # Analyze each strategy in detail
        print(f"\n📋 DETAILED STRATEGY BREAKDOWN")
        print("=" * 60)
        
        tier_counts = {"free": 0, "basic": 0, "pro": 0, "enterprise": 0}
        category_counts = {"spot": 0, "derivatives": 0, "algorithmic": 0, "portfolio": 0}
        total_monthly_cost = 0
        free_strategies = []
        paid_strategies = []
        
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
            print(f"     ID: {strategy_id}")
            print(f"     Category: {category}")
            print(f"     Tier: {tier}")
            print(f"     Monthly: ${monthly_cost} credits")
            print(f"     Per execution: ${execution_cost} credits")
            print(f"     AI Strategy: {'Yes' if is_ai else 'No'}")
            print(f"     Risk: {risk_level}")
            print(f"     Min Capital: ${min_capital:,}")
            
            # Count by tier and category
            if tier in tier_counts:
                tier_counts[tier] += 1
            if category in category_counts:
                category_counts[category] += 1
            
            total_monthly_cost += monthly_cost
            
            if monthly_cost == 0:
                free_strategies.append(strategy_id)
            else:
                paid_strategies.append({"id": strategy_id, "cost": monthly_cost})
            
            # Show backtest data quality
            backtest = strategy.get("backtest_results", {})
            if backtest:
                total_return = backtest.get("total_return", 0)
                win_rate = backtest.get("win_rate", 0)
                sharpe = backtest.get("sharpe_ratio", 0)
                max_dd = backtest.get("max_drawdown", 0)
                
                print(f"     📊 Backtest: {total_return:.1f}% return, {win_rate:.1f}% win rate")
                print(f"        Sharpe: {sharpe:.2f}, Max DD: {max_dd:.1f}%")
                
                # Check if backtest data looks real or mock
                if (total_return == 156.7 and win_rate == 68.5 and sharpe == 2.14):
                    print(f"        ⚠️ IDENTICAL BACKTEST DATA - Likely mock/template")
                else:
                    print(f"        ✅ UNIQUE BACKTEST DATA - Likely real")
        
        # Summary analysis
        print(f"\n📊 MARKETPLACE SUMMARY")
        print("=" * 60)
        print(f"Total Strategies: {len(strategies)}")
        print(f"Free Strategies: {len(free_strategies)}")
        print(f"Paid Strategies: {len(paid_strategies)}")
        print(f"Total Monthly Cost (all strategies): ${total_monthly_cost} credits")
        
        print(f"\n📈 BY TIER:")
        for tier, count in tier_counts.items():
            print(f"   {tier.capitalize()}: {count} strategies")
        
        print(f"\n📈 BY CATEGORY:")
        for category, count in category_counts.items():
            print(f"   {category.capitalize()}: {count} strategies")
        
        print(f"\n💰 FREE STRATEGIES:")
        for strategy_id in free_strategies:
            print(f"   - {strategy_id}")
        
        print(f"\n💰 PAID STRATEGIES (TOP 5 BY COST):")
        paid_sorted = sorted(paid_strategies, key=lambda x: x["cost"], reverse=True)
        for strategy in paid_sorted[:5]:
            print(f"   - {strategy['id']}: ${strategy['cost']}/month")
        
    else:
        print(f"❌ Marketplace failed: {response.status_code}")
        print(f"   Error: {response.text[:200]}")
    
    # Get admin user's current portfolio
    print(f"\n👤 ADMIN USER'S CURRENT PORTFOLIO")
    print("=" * 60)
    
    response = session.get(f"{BASE_URL}/strategies/my-portfolio")
    
    if response.status_code == 200:
        portfolio_data = response.json()
        active_strategies = portfolio_data.get("active_strategies", [])
        
        print(f"✅ Admin has {len(active_strategies)} active strategies:")
        
        for strategy in active_strategies:
            strategy_id = strategy.get("strategy_id", "unknown")
            name = strategy.get("name", "Unknown")
            category = strategy.get("category", "unknown")
            monthly_cost = strategy.get("monthly_cost", 0)
            
            print(f"   - {name} ({strategy_id})")
            print(f"     Category: {category}, Cost: ${monthly_cost}/month")
    
    # Test strategy execution with correct format
    print(f"\n🔧 TESTING STRATEGY EXECUTION")
    print("=" * 60)
    
    # Test with correct function parameter
    test_payload = {
        "function": "risk_management",
        "symbol": "BTC/USDT",
        "parameters": {"analysis_type": "comprehensive"},
        "user_id": "admin"
    }
    
    print(f"Testing strategy execution with correct format...")
    
    start_time = time.time()
    response = session.post(f"{BASE_URL}/strategies/execute", json=test_payload)
    execution_time = time.time() - start_time
    
    print(f"   Status: {response.status_code}")
    print(f"   Execution time: {execution_time:.2f}s")
    
    if response.status_code == 200:
        data = response.json()
        success = data.get("success", False)
        
        print(f"   Success: {success}")
        
        if success:
            print(f"   ✅ STRATEGY EXECUTION WORKING!")
            
            # Analyze execution result
            execution_result = data.get("execution_result", {})
            print(f"   Execution result keys: {list(execution_result.keys())}")
            
            # Look for real data in risk management
            if "risk_management_analysis" in execution_result:
                risk_analysis = execution_result["risk_management_analysis"]
                portfolio_metrics = risk_analysis.get("portfolio_risk_metrics", {})
                
                print(f"   📊 Risk Metrics Found:")
                print(f"      VaR 1d: ${portfolio_metrics.get('portfolio_var_1d_95', 0):,.2f}")
                print(f"      VaR 1w: ${portfolio_metrics.get('portfolio_var_1w_95', 0):,.2f}")
                print(f"      Sharpe Ratio: {portfolio_metrics.get('sharpe_ratio_portfolio', 0):.2f}")
                
                if portfolio_metrics.get('portfolio_var_1d_95', 0) > 0:
                    print(f"      🎉 REAL RISK CALCULATIONS!")
                else:
                    print(f"      ⚠️ Zero risk values - may be calculation issue")
        else:
            error = data.get("error", "Unknown error")
            print(f"   ❌ Execution failed: {error}")
    
    elif response.status_code == 422:
        error_data = response.json()
        print(f"   ⚠️ Validation error: {error_data}")
    else:
        print(f"   ❌ Request failed: {response.text[:100]}")

if __name__ == "__main__":
    get_complete_marketplace_data()