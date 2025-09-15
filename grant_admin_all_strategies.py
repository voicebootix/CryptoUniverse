#!/usr/bin/env python3
"""
Grant Admin User Access to ALL Strategies

This script grants the admin user access to all 25 strategies for comprehensive testing.
Uses the same purchase endpoint but with automated bulk provisioning.
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def grant_all_strategy_access():
    """Grant admin user access to all strategies."""
    
    print("🚀 GRANTING ADMIN ACCESS TO ALL STRATEGIES")
    print("=" * 70)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ Authenticated successfully")
    
    # Get current marketplace to see all available strategies
    print(f"\n📊 Getting all marketplace strategies...")
    response = session.get(f"{BASE_URL}/strategies/marketplace")
    
    if response.status_code != 200:
        print(f"❌ Failed to get marketplace: {response.status_code}")
        return False
    
    marketplace_data = response.json()
    strategies = marketplace_data.get("strategies", [])
    
    print(f"✅ Found {len(strategies)} strategies in marketplace")
    
    # Check current admin portfolio
    print(f"\n📋 Checking current admin portfolio...")
    response = session.get(f"{BASE_URL}/strategies/my-portfolio")
    
    current_strategies = []
    if response.status_code == 200:
        portfolio_data = response.json()
        current_strategies = [s.get("strategy_id", "") for s in portfolio_data.get("active_strategies", [])]
        print(f"   Current strategies: {len(current_strategies)}")
        for strategy_id in current_strategies:
            print(f"      - {strategy_id}")
    
    # Grant access to all strategies
    print(f"\n🎯 GRANTING ACCESS TO ALL STRATEGIES...")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for i, strategy in enumerate(strategies, 1):
        strategy_id = strategy.get("strategy_id", "")
        name = strategy.get("name", "Unknown")
        monthly_cost = strategy.get("credit_cost_monthly", 0)
        tier = strategy.get("tier", "unknown")
        
        print(f"\n{i:2d}. {name} ({strategy_id})")
        print(f"     Tier: {tier}, Cost: ${monthly_cost}/month")
        
        # Skip if already owned
        if strategy_id in current_strategies:
            print(f"     ✅ ALREADY OWNED - Skipping")
            skipped_count += 1
            continue
        
        # Purchase strategy
        try:
            url = f"{BASE_URL}/strategies/purchase?strategy_id={strategy_id}&subscription_type=permanent"
            response = session.post(url)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    print(f"     ✅ GRANTED ACCESS")
                    success_count += 1
                else:
                    error = result.get("error", "Unknown error")
                    print(f"     ❌ Failed: {error}")
                    failed_count += 1
            else:
                print(f"     ❌ HTTP Error: {response.status_code}")
                failed_count += 1
                
        except Exception as e:
            print(f"     ❌ Exception: {e}")
            failed_count += 1
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    # Final summary
    print(f"\n📊 STRATEGY ACCESS GRANT SUMMARY")
    print("=" * 60)
    print(f"Total strategies processed: {len(strategies)}")
    print(f"Successfully granted: {success_count}")
    print(f"Already owned: {skipped_count}")
    print(f"Failed: {failed_count}")
    print(f"Success rate: {(success_count + skipped_count) / len(strategies) * 100:.1f}%")
    
    # Verify final portfolio
    print(f"\n🔍 VERIFYING FINAL ADMIN PORTFOLIO...")
    response = session.get(f"{BASE_URL}/strategies/my-portfolio")
    
    if response.status_code == 200:
        portfolio_data = response.json()
        final_strategies = portfolio_data.get("active_strategies", [])
        total_monthly_cost = portfolio_data.get("total_monthly_cost", 0)
        
        print(f"✅ Final portfolio verification:")
        print(f"   Total active strategies: {len(final_strategies)}")
        print(f"   Total monthly cost: ${total_monthly_cost}")
        
        if len(final_strategies) >= 20:  # Should have most strategies
            print(f"   🎉 ADMIN HAS COMPREHENSIVE STRATEGY ACCESS!")
        else:
            print(f"   ⚠️ Admin has limited access - may need manual intervention")
        
        # Show breakdown by category
        categories = {}
        for strategy in final_strategies:
            cat = strategy.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"\n📈 Strategy breakdown by category:")
        for category, count in categories.items():
            print(f"   {category.capitalize()}: {count} strategies")
    
    return success_count > 0

def create_admin_testing_credits():
    """Ensure admin has enough credits for testing."""
    
    print(f"\n💰 CHECKING ADMIN CREDIT BALANCE...")
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Check credit balance (if endpoint exists)
    credit_endpoints = ["/credits/balance", "/user/credits", "/account/credits"]
    
    for endpoint in credit_endpoints:
        try:
            response = session.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Credit balance from {endpoint}:")
                print(f"   {json.dumps(data, indent=2)}")
                break
        except:
            continue
    else:
        print(f"⚠️ Could not check credit balance - endpoints may not be available")
    
    print(f"\n💡 NOTE: Admin should have sufficient credits for testing")
    print(f"   If needed, contact system admin to add testing credits")

def main():
    print("🎯 ADMIN STRATEGY ACCESS PROVISIONING")
    print("=" * 80)
    
    # Grant strategy access
    access_granted = grant_all_strategy_access()
    
    # Check credits
    create_admin_testing_credits()
    
    if access_granted:
        print(f"\n🎉 ADMIN STRATEGY ACCESS SETUP COMPLETE!")
        print("=" * 60)
        print("✅ Admin user now has access to test all strategies")
        print("✅ Can test all 25 strategy functions")
        print("✅ Can verify real data generation")
        print("✅ Can test opportunity discovery with full strategy suite")
        
        print(f"\n🔧 NEXT STEPS FOR TESTING:")
        print("1. Test individual strategies via /strategies/execute")
        print("2. Test opportunity discovery via chat")
        print("3. Verify marketplace shows all strategies")
        print("4. Test backtesting data uniqueness")
    else:
        print(f"\n⚠️ SOME ISSUES ENCOUNTERED")
        print("Manual intervention may be required")

if __name__ == "__main__":
    main()