#!/usr/bin/env python3
"""
Simple debug to check what's happening with user strategies
"""

import requests
import json

def debug_user_simple():
    """Simple debug of user and strategy status"""
    
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
    user_data = response.json()
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 Simple user and strategy debug...")
    print(f"✅ Login successful")
    print(f"📧 User: {user_data.get('user', {}).get('email', 'Unknown')}")
    print(f"🆔 User ID: {user_data.get('user', {}).get('id', 'Unknown')}")
    
    # Test opportunity discovery directly to see the error
    print(f"\n🔍 Testing opportunity discovery to see actual error:")
    
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
        
        print(f"✅ Chat response received")
        print(f"🎯 Intent: {chat_data.get('intent')}")
        print(f"🔧 Service used: {metadata.get('service_used')}")
        print(f"📈 Opportunities: {len(metadata.get('opportunities', []))}")
        
        # Check if there's any error info in AI analysis
        ai_analysis = metadata.get('ai_analysis', {})
        if ai_analysis:
            opp_analysis = ai_analysis.get('opportunity_analysis', {})
            
            # Look for clues in model responses
            model_responses = opp_analysis.get('model_responses', [])
            for model_resp in model_responses:
                reasoning = model_resp.get('reasoning', '')
                if 'no active trading opportunities' in reasoning.lower():
                    print(f"🤖 {model_resp.get('provider')}: Says no active opportunities")
                if 'strategy' in reasoning.lower():
                    print(f"🤖 {model_resp.get('provider')}: Mentions strategies")
                if 'onboard' in reasoning.lower():
                    print(f"🤖 {model_resp.get('provider')}: Mentions onboarding")
        
        # Check if there are any other clues in metadata
        if 'auto_onboarded' in metadata:
            print(f"🎯 Auto onboarding attempted: {metadata.get('auto_onboarded')}")
        
        if 'onboarding_result' in metadata:
            print(f"🎯 Onboarding result: {metadata.get('onboarding_result')}")
            
        if 'user_tier' in metadata:
            print(f"👤 User tier: {metadata.get('user_tier')}")
            
        if 'strategy_count' in metadata:
            print(f"📊 Strategy count: {metadata.get('strategy_count')}")
    
    else:
        print(f"❌ Chat response failed: {chat_response.status_code}")
        print(f"   Error: {chat_response.text}")

if __name__ == "__main__":
    debug_user_simple()