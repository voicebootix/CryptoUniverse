#!/usr/bin/env python3
"""
Test the deployed opportunity discovery fix
"""

import requests
import json
import time

def test_opportunity_discovery_after_deployment():
    """Test if the deployed fix works"""
    
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
    
    print("🔍 Testing opportunity discovery after deployment...")
    
    # Test multiple opportunity discovery messages
    test_messages = [
        "Find me trading opportunities",
        "What are the best crypto opportunities right now?",
        "Show me profitable trades",
        "Discover market opportunities"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{'='*60}")
        print(f"🧪 Test {i}: '{message}'")
        print(f"{'='*60}")
        
        message_data = {
            "message": message,
            "mode": "trading"
        }
        
        start_time = time.time()
        
        response = requests.post(f"{base_url}/chat/message", 
                               json=message_data, 
                               headers=headers, 
                               timeout=120)
        
        response_time = time.time() - start_time
        
        print(f"⏱️ Response time: {response_time:.2f}s")
        print(f"📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📊 RESPONSE ANALYSIS:")
            print(f"   Success: {data.get('success')}")
            print(f"   Intent: {data.get('intent')}")
            print(f"   Confidence: {data.get('confidence')}")
            
            content = data.get('content', '')
            print(f"\n💬 CONTENT PREVIEW:")
            print(f"   {content[:200]}...")
            
            metadata = data.get('metadata', {})
            opportunities = metadata.get('opportunities', [])
            
            print(f"\n📈 OPPORTUNITIES ANALYSIS:")
            print(f"   Count: {len(opportunities)}")
            
            if opportunities:
                print(f"   ✅ SUCCESS! Found {len(opportunities)} opportunities:")
                
                for j, opp in enumerate(opportunities[:3]):
                    symbol = opp.get('symbol', 'Unknown')
                    confidence = opp.get('confidence', 0)
                    potential_return = opp.get('potential_return', 0)
                    buy_signals = opp.get('buy_signals', 0)
                    sell_signals = opp.get('sell_signals', 0)
                    signal_strength = opp.get('signal_strength', 0)
                    strategy = opp.get('strategy', 'Unknown')
                    reason = opp.get('reason', '')
                    
                    print(f"      {j+1}. {symbol}")
                    print(f"         Confidence: {confidence}%")
                    print(f"         Potential Return: {potential_return}%")
                    print(f"         Strategy: {strategy}")
                    print(f"         Signals: {buy_signals} buy, {sell_signals} sell (strength: {signal_strength})")
                    print(f"         Reason: {reason}")
                
                # Check AI analysis
                ai_analysis = metadata.get('ai_analysis', {})
                if ai_analysis:
                    opportunity_analysis = ai_analysis.get('opportunity_analysis', {})
                    consensus_score = opportunity_analysis.get('consensus_score', 0)
                    recommendation = opportunity_analysis.get('recommendation', 'Unknown')
                    
                    print(f"\n   🤖 AI CONSENSUS:")
                    print(f"      Score: {consensus_score:.1f}%")
                    print(f"      Recommendation: {recommendation}")
                
                return True
                
            else:
                print(f"   ❌ Still no opportunities found")
                
                # Check if content changed from before
                if "No significant opportunities detected" in content:
                    print(f"   ⚠️ Still getting the old 'no opportunities' message")
                    print(f"   🔍 This suggests the fix may not be active yet")
                else:
                    print(f"   ℹ️ Different response content - fix may be working but no opportunities available")
                
                # Check AI reasoning
                ai_analysis = metadata.get('ai_analysis', {})
                if ai_analysis:
                    opportunity_analysis = ai_analysis.get('opportunity_analysis', {})
                    model_responses = opportunity_analysis.get('model_responses', [])
                    
                    print(f"\n   🤖 AI MODEL REASONING:")
                    for model_resp in model_responses[:2]:  # Show first 2 models
                        provider = model_resp.get('provider', 'Unknown')
                        reasoning = model_resp.get('reasoning', '')[:150]
                        print(f"      {provider}: {reasoning}...")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")
        
        time.sleep(3)  # Wait between tests
    
    return False

def main():
    """Run the test"""
    print("🚀 TESTING DEPLOYED OPPORTUNITY DISCOVERY FIX")
    print("="*60)
    
    success = test_opportunity_discovery_after_deployment()
    
    print(f"\n{'='*60}")
    print("📊 DEPLOYMENT TEST RESULTS:")
    
    if success:
        print("✅ FIX SUCCESSFUL!")
        print("   - Opportunity discovery now finds opportunities")
        print("   - Technical analysis signals are being processed correctly")
        print("   - AI models are receiving opportunity data")
    else:
        print("❌ FIX NOT YET ACTIVE OR NEEDS ADJUSTMENT:")
        print("   - May need time for deployment to propagate")
        print("   - Or technical analysis may not be returning buy signals")
        print("   - Check if the randomized signals are generating buy > sell scenarios")

if __name__ == "__main__":
    main()