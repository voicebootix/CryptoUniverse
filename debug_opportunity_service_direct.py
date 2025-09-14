#!/usr/bin/env python3
"""
Debug the opportunity discovery service directly to see where it fails
"""

import requests
import json

def debug_opportunity_service_direct():
    """Debug the opportunity discovery service step by step"""
    
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
    
    print("🔍 Debugging opportunity discovery service directly...")
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    
    # Test if there's a direct opportunity discovery endpoint
    print(f"\n1️⃣ Testing /opportunities endpoint:")
    try:
        opp_response = requests.get(f"{base_url}/opportunities", headers=headers, timeout=60)
        print(f"   Status: {opp_response.status_code}")
        
        if opp_response.status_code == 200:
            opp_data = opp_response.json()
            print(f"   Success: {opp_data.get('success')}")
            print(f"   Opportunities: {len(opp_data.get('opportunities', []))}")
        else:
            print(f"   Error: {opp_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test opportunity discovery with parameters
    print(f"\n2️⃣ Testing /opportunities with parameters:")
    try:
        params = {
            "user_id": user_id,
            "force_refresh": "true",
            "include_strategy_recommendations": "true"
        }
        
        opp_response = requests.get(f"{base_url}/opportunities", 
                                   headers=headers, 
                                   params=params,
                                   timeout=60)
        print(f"   Status: {opp_response.status_code}")
        
        if opp_response.status_code == 200:
            opp_data = opp_response.json()
            print(f"   Success: {opp_data.get('success')}")
            print(f"   Opportunities: {len(opp_data.get('opportunities', []))}")
            print(f"   Message: {opp_data.get('message', '')}")
            
            if 'error' in opp_data:
                print(f"   Error: {opp_data['error']}")
        else:
            print(f"   Error: {opp_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test POST to opportunities
    print(f"\n3️⃣ Testing POST /opportunities:")
    try:
        post_data = {
            "user_id": user_id,
            "force_refresh": True,
            "include_strategy_recommendations": True
        }
        
        opp_response = requests.post(f"{base_url}/opportunities", 
                                    headers=headers, 
                                    json=post_data,
                                    timeout=60)
        print(f"   Status: {opp_response.status_code}")
        
        if opp_response.status_code == 200:
            opp_data = opp_response.json()
            print(f"   Success: {opp_data.get('success')}")
            print(f"   Opportunities: {len(opp_data.get('opportunities', []))}")
            print(f"   Total opportunities: {opp_data.get('total_opportunities', 0)}")
            print(f"   Scan ID: {opp_data.get('scan_id', 'None')}")
            
            if 'error' in opp_data:
                print(f"   Error: {opp_data['error']}")
                
            # Check for detailed scan results
            if 'strategy_results' in opp_data:
                strategy_results = opp_data['strategy_results']
                print(f"   Strategy results: {len(strategy_results)} strategies scanned")
                
                for strategy_id, result in strategy_results.items():
                    print(f"      {strategy_id}: {result.get('opportunities_found', 0)} opportunities")
                    if result.get('error'):
                        print(f"         Error: {result['error']}")
        else:
            print(f"   Error: {opp_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test chat opportunity discovery one more time for comparison
    print(f"\n4️⃣ Testing chat opportunity discovery for comparison:")
    message_data = {
        "message": "Find me trading opportunities",
        "mode": "trading"
    }
    
    chat_response = requests.post(f"{base_url}/chat/message", 
                                 json=message_data, 
                                 headers=headers, 
                                 timeout=120)
    
    if chat_response.status_code == 200:
        chat_data = chat_response.json()
        metadata = chat_data.get('metadata', {})
        opportunities = metadata.get('opportunities', [])
        
        print(f"   Chat opportunities: {len(opportunities)}")
        print(f"   Service used: {metadata.get('service_used')}")
        
        # Check for any additional metadata that might give clues
        if 'scan_id' in metadata:
            print(f"   Scan ID: {metadata['scan_id']}")
        if 'user_tier' in metadata:
            print(f"   User tier: {metadata['user_tier']}")
        if 'strategy_count' in metadata:
            print(f"   Strategy count: {metadata['strategy_count']}")
        if 'asset_count' in metadata:
            print(f"   Asset count: {metadata['asset_count']}")
    else:
        print(f"   Chat error: {chat_response.status_code}")

if __name__ == "__main__":
    debug_opportunity_service_direct()