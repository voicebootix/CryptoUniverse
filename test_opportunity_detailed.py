#!/usr/bin/env python3
"""
Detailed test to see exactly what's happening in opportunity discovery
"""

import requests
import json

def test_opportunity_discovery_detailed():
    """Test opportunity discovery with detailed logging"""
    
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
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 Testing opportunity discovery with detailed analysis...")
    
    # Test technical analysis first
    print("\n1️⃣ Testing technical analysis directly:")
    tech_response = requests.post(f"{base_url}/market/technical-analysis", 
                                 json={"symbols": ["BTC", "ETH", "SOL"]},
                                 headers=headers, timeout=60)
    
    if tech_response.status_code == 200:
        tech_data = tech_response.json()
        print(f"   ✅ Technical analysis success: {tech_data.get('success')}")
        
        if tech_data.get('success'):
            analysis_data = tech_data.get('data', {})
            print(f"   📊 Analysis data keys: {list(analysis_data.keys())}")
            
            for symbol, data in analysis_data.items():
                signals = data.get('signals', {})
                buy_signals = signals.get('buy', 0)
                sell_signals = signals.get('sell', 0)
                print(f"   {symbol}: {buy_signals} buy, {sell_signals} sell")
                
                # Check if this should create an opportunity
                should_create = (buy_signals >= sell_signals and buy_signals > 0) or (buy_signals > 0 and sell_signals == 0)
                print(f"      Should create opportunity: {should_create}")
    else:
        print(f"   ❌ Technical analysis failed: {tech_response.status_code}")
    
    # Test chat opportunity discovery
    print("\n2️⃣ Testing chat opportunity discovery:")
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
        print(f"   ✅ Chat response success: {chat_data.get('success')}")
        print(f"   🎯 Intent: {chat_data.get('intent')}")
        
        metadata = chat_data.get('metadata', {})
        opportunities = metadata.get('opportunities', [])
        service_used = metadata.get('service_used')
        
        print(f"   🔧 Service used: {service_used}")
        print(f"   📈 Opportunities found: {len(opportunities)}")
        
        if opportunities:
            print(f"   ✅ SUCCESS! Found opportunities:")
            for i, opp in enumerate(opportunities):
                print(f"      {i+1}. {opp}")
        else:
            print(f"   ❌ No opportunities found")
            
            # Check AI analysis for clues
            ai_analysis = metadata.get('ai_analysis', {})
            if ai_analysis:
                opp_analysis = ai_analysis.get('opportunity_analysis', {})
                model_responses = opp_analysis.get('model_responses', [])
                
                print(f"   🤖 AI model responses:")
                for model_resp in model_responses:
                    provider = model_resp.get('provider')
                    reasoning = model_resp.get('reasoning', '')[:100]
                    print(f"      {provider}: {reasoning}...")
    else:
        print(f"   ❌ Chat response failed: {chat_response.status_code}")

if __name__ == "__main__":
    test_opportunity_discovery_detailed()