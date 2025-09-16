#!/usr/bin/env python3
"""
Test opportunity discovery now to see if it's working
"""

import requests
import json

def test_opportunity_discovery_now():
    """Test if opportunity discovery is working now"""
    
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
    
    print("🔍 Testing opportunity discovery now...")
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    
    # Test opportunity discovery endpoint
    print(f"\n1️⃣ Testing /opportunities/discover:")
    try:
        discover_data = {
            "force_refresh": True,
            "include_strategy_recommendations": True
        }
        
        discover_response = requests.post(f"{base_url}/opportunities/discover", 
                                        headers=headers, 
                                        json=discover_data,
                                        timeout=120)
        
        print(f"   Status: {discover_response.status_code}")
        
        if discover_response.status_code == 200:
            discover_result = discover_response.json()
            print(f"   Success: {discover_result.get('success')}")
            print(f"   Total opportunities: {discover_result.get('total_opportunities', 0)}")
            print(f"   Execution time: {discover_result.get('execution_time_ms', 0):.2f}ms")
            
            if discover_result.get('error'):
                print(f"   Error: {discover_result['error']}")
            
            # Check user profile
            user_profile = discover_result.get('user_profile', {})
            if user_profile:
                print(f"   User profile:")
                print(f"      Active strategies: {user_profile.get('active_strategies', 0)}")
                print(f"      User tier: {user_profile.get('user_tier', 'Unknown')}")
                print(f"      Monthly cost: ${user_profile.get('monthly_strategy_cost', 0)}")
            
            # Check opportunities
            opportunities = discover_result.get('opportunities', [])
            if opportunities:
                print(f"   ✅ Found {len(opportunities)} opportunities:")
                for i, opp in enumerate(opportunities[:5]):
                    print(f"      {i+1}. {opp.get('symbol')} on {opp.get('exchange')}")
                    print(f"         Strategy: {opp.get('strategy_name')}")
                    print(f"         Profit: ${opp.get('profit_potential_usd', 0):.2f}")
                    print(f"         Confidence: {opp.get('confidence_score', 0):.1f}%")
            else:
                print(f"   ❌ No opportunities found")
                
                # Check asset discovery details
                asset_discovery = discover_result.get('asset_discovery', {})
                if asset_discovery:
                    print(f"   Asset discovery:")
                    print(f"      Total assets: {asset_discovery.get('total_assets_scanned', 0)}")
                    print(f"      Asset tiers: {asset_discovery.get('asset_tiers', [])}")
                    print(f"      Max tier: {asset_discovery.get('max_tier_accessed', 'Unknown')}")
        else:
            print(f"   Error: {discover_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test chat opportunity discovery
    print(f"\n2️⃣ Testing chat opportunity discovery:")
    try:
        message_data = {
            "message": "Find me trading opportunities",
            "mode": "trading"
        }
        
        chat_response = requests.post(f"{base_url}/chat/message", 
                                     json=message_data, 
                                     headers=headers, 
                                     timeout=120)
        
        print(f"   Status: {chat_response.status_code}")
        
        if chat_response.status_code == 200:
            chat_data = chat_response.json()
            print(f"   Success: {chat_data.get('success')}")
            print(f"   Intent: {chat_data.get('intent')}")
            
            metadata = chat_data.get('metadata', {})
            opportunities = metadata.get('opportunities', [])
            print(f"   Opportunities found: {len(opportunities)}")
            
            if opportunities:
                print(f"   ✅ Chat found opportunities:")
                for i, opp in enumerate(opportunities[:3]):
                    print(f"      {i+1}. {opp.get('symbol', 'Unknown')}: {opp.get('confidence', 0)}% confidence")
            else:
                print(f"   ❌ Chat found no opportunities")
                
                # Check what the AI is saying
                ai_analysis = metadata.get('ai_analysis', {})
                if ai_analysis:
                    opp_analysis = ai_analysis.get('opportunity_analysis', {})
                    if opp_analysis:
                        print(f"   AI consensus score: {opp_analysis.get('consensus_score', 0):.1f}")
                        print(f"   AI recommendation: {opp_analysis.get('recommendation', 'Unknown')}")
        else:
            print(f"   Error: {chat_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")

if __name__ == "__main__":
    test_opportunity_discovery_now()