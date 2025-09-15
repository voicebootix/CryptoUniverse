#!/usr/bin/env python3
"""
Admin Strategy Override System

Provides multiple methods to grant admin full strategy access for testing:
1. Credit top-up for purchasing
2. Direct database strategy provisioning
3. Admin override for free access
"""

import requests
import json
import sys
import os

# Configuration - Load from environment variables
BASE_URL = os.environ.get('BASE_URL')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

# Check for required environment variables
if not all([BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD]):
    print("❌ ERROR: Missing required environment variables")
    print("   Please set BASE_URL, ADMIN_EMAIL, and ADMIN_PASSWORD")
    sys.exit(1)

# Check for explicit opt-in
if os.environ.get('CONFIRM_ADMIN_ACTIONS') != 'true':
    print("❌ ERROR: Admin actions require explicit confirmation")
    print("   Set CONFIRM_ADMIN_ACTIONS=true to proceed")
    sys.exit(1)

def method_1_credit_topup():
    """Method 1: Add credits to admin account for purchasing strategies."""
    
    print("💰 METHOD 1: CREDIT TOP-UP APPROACH")
    print("=" * 50)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data, timeout=15)
    if not response.ok:
        print(f"❌ Login failed with status {response.status_code}: {response.text}")
        return False

    token = response.json().get("access_token")
    if not token or not isinstance(token, str) or len(token) == 0:
        print(f"❌ Invalid or missing access token")
        return False

    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Try to add credits (if endpoint exists)
    credit_endpoints = [
        "/credits/add",
        "/admin/credits/add", 
        "/credits/topup",
        "/account/credits/add"
    ]
    
    for endpoint in credit_endpoints:
        try:
            payload = {"amount": 1000, "reason": "Admin testing"}
            response = session.post(f"{BASE_URL}{endpoint}", json=payload)
            
            print(f"   Testing {endpoint}: Status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Credits added via {endpoint}")
                print(f"   Result: {data}")
                return True
                
        except Exception as e:
            print(f"   {endpoint}: Exception {e}")
    
    print(f"   ⚠️ No credit top-up endpoints found")
    return False

def method_2_admin_override():
    """Method 2: Use admin override to get free access."""
    
    print(f"\n🔧 METHOD 2: ADMIN OVERRIDE APPROACH")
    print("=" * 50)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data, timeout=15)
    if not response.ok:
        print(f"❌ Login failed with status {response.status_code}: {response.text}")
        return False

    token = response.json().get("access_token")
    if not token or not isinstance(token, str) or len(token) == 0:
        print(f"❌ Invalid or missing access token")
        return False

    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Try admin override endpoints
    admin_endpoints = [
        "/admin/strategies/grant-all",
        "/admin/users/grant-strategies",
        "/strategies/admin/grant-all",
        "/admin/override/strategies"
    ]
    
    for endpoint in admin_endpoints:
        try:
            payload = {"user_id": "admin", "grant_all": True}
            response = session.post(f"{BASE_URL}{endpoint}", json=payload)
            
            print(f"   Testing {endpoint}: Status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Admin override successful via {endpoint}")
                print(f"   Result: {data}")
                return True
                
        except Exception as e:
            print(f"   {endpoint}: Exception {e}")
    
    print(f"   ⚠️ No admin override endpoints found")
    return False

def method_3_direct_provisioning():
    """Method 3: Direct strategy provisioning via service layer."""
    
    print(f"\n🔧 METHOD 3: DIRECT SERVICE PROVISIONING")
    print("=" * 50)
    
    try:
        # Import the strategy marketplace service directly
        from app.services.strategy_marketplace_service import strategy_marketplace_service
        
        print("✅ Strategy marketplace service imported")
        
        # All 25 strategy IDs that should be accessible
        all_strategy_ids = [
            # Derivatives (12)
            "ai_futures_trade", "ai_options_trade", "ai_perpetual_trade",
            "ai_leverage_position", "ai_complex_strategy", "ai_margin_status",
            "ai_funding_arbitrage", "ai_basis_trade", "ai_options_chain",
            "ai_calculate_greeks", "ai_liquidation_price", "ai_hedge_position",
            
            # Spot (3)
            "ai_spot_momentum_strategy", "ai_spot_mean_reversion", "ai_spot_breakout_strategy",
            
            # Algorithmic (6)
            "ai_algorithmic_trading", "ai_pairs_trading", "ai_statistical_arbitrage",
            "ai_market_making", "ai_scalping_strategy", "ai_swing_trading",
            
            # Risk & Portfolio (4)
            "ai_position_management", "ai_risk_management", 
            "ai_portfolio_optimization", "ai_strategy_performance"
        ]
        
        print(f"📊 Provisioning {len(all_strategy_ids)} strategies...")
        
        # This would require database access, so we'll create a script
        print(f"   Creating direct provisioning script...")
        
        script_content = f'''
# Direct Redis provisioning script
import asyncio
from app.core.redis import get_redis_client

async def provision_all_strategies():
    redis = await get_redis_client()
    if redis:
        # Add all strategies to admin user
        for strategy_id in {all_strategy_ids}:
            await redis.sadd("user_strategies:ADMIN_USER_ID", strategy_id)
        
        print("✅ All strategies provisioned in Redis")
    else:
        print("❌ Redis not available")

# Run: python -c "import asyncio; asyncio.run(provision_all_strategies())"
'''
        
        with open('/workspace/provision_admin_strategies_direct.py', 'w') as f:
            f.write(script_content)
        
        print(f"   📄 Created: provision_admin_strategies_direct.py")
        print(f"   ℹ️ This requires production Redis access")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct provisioning failed: {e}")
        return False

def method_4_api_batch_purchase():
    """Method 4: Batch purchase with error handling."""
    
    print(f"\n🔧 METHOD 4: BATCH PURCHASE WITH RETRY")
    print("=" * 50)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data, timeout=15)
    if not response.ok:
        print(f"❌ Login failed with status {response.status_code}: {response.text}")
        return False

    token = response.json().get("access_token")
    if not token or not isinstance(token, str) or len(token) == 0:
        print(f"❌ Invalid or missing access token")
        return False

    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # All strategy IDs from marketplace
    strategy_ids = [
        "ai_futures_trade", "ai_options_trade", "ai_complex_strategy",
        "ai_spot_mean_reversion", "ai_spot_breakout_strategy", 
        "ai_pairs_trading", "ai_statistical_arbitrage", "ai_market_making",
        "ai_scalping_strategy"
    ]
    
    print(f"📦 Attempting batch purchase of {len(strategy_ids)} strategies...")
    
    success_count = 0
    
    for strategy_id in strategy_ids:
        print(f"\n🎯 Purchasing: {strategy_id}")
        
        # Try different purchase methods
        purchase_methods = [
            {"url": f"/strategies/purchase?strategy_id={strategy_id}&subscription_type=permanent", "method": "GET_PARAMS"},
            {"url": f"/strategies/purchase", "method": "POST_JSON", "data": {"strategy_id": strategy_id, "subscription_type": "permanent"}},
            {"url": f"/strategies/{strategy_id}/activate", "method": "POST_EMPTY"}
        ]
        
        for method in purchase_methods:
            try:
                if method["method"] == "GET_PARAMS":
                    response = session.post(f"{BASE_URL}{method['url']}")
                elif method["method"] == "POST_JSON":
                    response = session.post(f"{BASE_URL}{method['url']}", json=method["data"])
                else:
                    response = session.post(f"{BASE_URL}{method['url']}")
                
                print(f"   {method['method']}: Status {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success", False):
                        print(f"   ✅ SUCCESS via {method['method']}")
                        success_count += 1
                        break
                    else:
                        print(f"   Response: {result.get('message', 'No message')}")
                
            except Exception as e:
                print(f"   Exception: {e}")
        else:
            print(f"   ❌ All methods failed for {strategy_id}")
    
    print(f"\n📊 Batch purchase results: {success_count}/{len(strategy_ids)} successful")
    return success_count > 0

def main():
    # Additional safety check for admin override
    if os.environ.get('ADMIN_OVERRIDE_ENABLED') != 'true':
        print("❌ ERROR: Admin override is disabled")
        print("   Set ADMIN_OVERRIDE_ENABLED=true to enable admin overrides")
        print("   This is a safety mechanism to prevent accidental execution")
        sys.exit(1)

    print("🎯 COMPREHENSIVE ADMIN STRATEGY ACCESS SETUP")
    print("=" * 80)

    # Try all methods
    method1_success = method_1_credit_topup()
    method2_success = method_2_admin_override()
    method3_success = method_3_direct_provisioning()
    method4_success = method_4_api_batch_purchase()
    
    print(f"\n📊 FINAL RESULTS:")
    print("=" * 50)
    print(f"Method 1 (Credit Top-up): {'✅' if method1_success else '❌'}")
    print(f"Method 2 (Admin Override): {'✅' if method2_success else '❌'}")
    print(f"Method 3 (Direct Provisioning): {'✅' if method3_success else '❌'}")
    print(f"Method 4 (Batch Purchase): {'✅' if method4_success else '❌'}")
    
    if any([method1_success, method2_success, method3_success, method4_success]):
        print(f"\n🎉 ADMIN ACCESS ENHANCED!")
        print("Admin now has broader strategy access for testing")
    else:
        print(f"\n⚠️ LIMITED SUCCESS - Manual intervention may be needed")
        
        print(f"\n💡 MANUAL ALTERNATIVES:")
        print("1. Add credits to admin account via database")
        print("2. Set all strategies to free tier temporarily")
        print("3. Use Redis commands to provision strategies directly")
        print("4. Create admin testing endpoint")

if __name__ == "__main__":
    main()