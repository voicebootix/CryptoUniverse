#!/usr/bin/env python3
"""
Debug using the correct API endpoints
"""

import requests
import json

def debug_correct_endpoints():
    """Debug using the actual API endpoints that exist"""
    
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
    
    print("🔍 Debugging with correct API endpoints...")
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    
    # Test the correct strategy portfolio endpoint
    print(f"\n1️⃣ Testing /strategies/my-portfolio:")
    try:
        portfolio_response = requests.get(f"{base_url}/strategies/my-portfolio", headers=headers, timeout=30)
        print(f"   Status: {portfolio_response.status_code}")
        
        if portfolio_response.status_code == 200:
            portfolio_data = portfolio_response.json()
            print(f"   Success: {portfolio_data.get('success')}")
            print(f"   Total strategies: {portfolio_data.get('total_strategies', 0)}")
            print(f"   Monthly cost: ${portfolio_data.get('total_monthly_cost', 0)}")
            
            active_strategies = portfolio_data.get('active_strategies', [])
            if active_strategies:
                print(f"   ✅ Found {len(active_strategies)} active strategies:")
                for strategy in active_strategies:
                    print(f"      - {strategy.get('name')} ({strategy.get('strategy_id')})")
            else:
                print(f"   ❌ No active strategies found")
                print(f"   Error: {portfolio_data.get('error', 'No error message')}")
        else:
            print(f"   Error: {portfolio_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test strategy marketplace
    print(f"\n2️⃣ Testing /strategies/marketplace:")
    try:
        marketplace_response = requests.get(f"{base_url}/strategies/marketplace", headers=headers, timeout=30)
        print(f"   Status: {marketplace_response.status_code}")
        
        if marketplace_response.status_code == 200:
            marketplace_data = marketplace_response.json()
            print(f"   Success: {marketplace_data.get('success')}")
            
            strategies = marketplace_data.get('strategies', [])
            print(f"   Available strategies: {len(strategies)}")
            
            free_strategies = [s for s in strategies if s.get('credit_cost_monthly', 1) == 0]
            print(f"   Free strategies: {len(free_strategies)}")
            
            if free_strategies:
                print(f"   Free strategies available:")
                for strategy in free_strategies[:5]:
                    print(f"      - {strategy.get('name')} (${strategy.get('credit_cost_monthly', 0)}/month)")
        else:
            print(f"   Error: {marketplace_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test purchasing a free strategy if none exist
    print(f"\n3️⃣ Testing strategy purchase (if needed):")
    try:
        # Try to purchase the risk management strategy (should be free)
        purchase_data = {
            "strategy_id": "ai_risk_management"
        }
        
        purchase_response = requests.post(f"{base_url}/strategies/purchase?strategy_id=ai_risk_management", 
                                        headers=headers, timeout=30)
        print(f"   Purchase status: {purchase_response.status_code}")
        
        if purchase_response.status_code == 200:
            purchase_result = purchase_response.json()
            print(f"   Purchase success: {purchase_result.get('success')}")
            print(f"   Message: {purchase_result.get('message', '')}")
        else:
            print(f"   Purchase error: {purchase_response.text}")
    except Exception as e:
        print(f"   Purchase exception: {e}")
    
    # Test opportunity discovery again
    print(f"\n4️⃣ Testing opportunity discovery after strategy check:")
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
        
        print(f"   Opportunities found: {len(opportunities)}")
        
        if opportunities:
            print(f"   ✅ SUCCESS! Found opportunities:")
            for i, opp in enumerate(opportunities[:3]):
                print(f"      {i+1}. {opp.get('symbol', 'Unknown')}: {opp.get('confidence', 0)}% confidence")
        else:
            print(f"   ❌ Still no opportunities found")
            
            # Check what the AI models are saying
            ai_analysis = metadata.get('ai_analysis', {})
            if ai_analysis:
                opp_analysis = ai_analysis.get('opportunity_analysis', {})
                model_responses = opp_analysis.get('model_responses', [])
                
                print(f"   🤖 AI model insights:")
                for model_resp in model_responses:
                    reasoning = model_resp.get('reasoning', '')
                    if 'no active trading opportunities' in reasoning.lower():
                        print(f"      {model_resp.get('provider')}: No active opportunities detected")
                    elif 'strategy' in reasoning.lower():
                        print(f"      {model_resp.get('provider')}: Mentions strategy issues")
    else:
        print(f"   Chat error: {chat_response.status_code}")

if __name__ == "__main__":
    debug_correct_endpoints()