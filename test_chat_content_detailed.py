#!/usr/bin/env python3
"""
Detailed Chat Content Analysis - Get the full chat response to understand the flow
"""

import requests
import json
from datetime import datetime

def test_chat_content_detailed():
    """Get detailed chat response content."""
    
    print("🔍 DETAILED CHAT CONTENT ANALYSIS")
    print("Getting the full chat response to understand the flow")
    
    base_url = "https://cryptouniverse.onrender.com"
    
    # Get auth token
    login_data = {
        'email': 'admin@cryptouniverse.com',
        'password': 'AdminPass123!'
    }
    
    login_response = requests.post(f'{base_url}/api/v1/auth/login', json=login_data, timeout=30)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    token = login_response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # Test chat opportunity discovery
    chat_data = {
        'message': 'Find the best opportunities now',
        'include_context': True
    }
    
    print("📞 Calling chat opportunity discovery...")
    chat_response = requests.post(
        f'{base_url}/api/v1/chat/message', 
        headers=headers, 
        json=chat_data,
        timeout=60
    )
    
    if chat_response.status_code == 200:
        result = chat_response.json()
        
        print(f"✅ SUCCESS: Chat response received")
        print(f"📊 Response keys: {list(result.keys())}")
        
        # Show the actual content
        content = result.get('content', '')
        print(f"\n📝 FULL CHAT RESPONSE CONTENT:")
        print("="*100)
        print(content)
        print("="*100)
        
        # Analyze the content for specific patterns
        print(f"\n📋 CONTENT PATTERN ANALYSIS:")
        
        # Check for portfolio optimization patterns
        portfolio_patterns = [
            "portfolio optimization",
            "rebalancing",
            "asset allocation",
            "risk tolerance",
            "moderate risk",
            "balanced approach",
            "strategic portfolio",
            "optimization metrics"
        ]
        
        portfolio_matches = [pattern for pattern in portfolio_patterns if pattern.lower() in content.lower()]
        print(f"   Portfolio optimization patterns found: {len(portfolio_matches)}/{len(portfolio_patterns)}")
        print(f"   Matches: {portfolio_matches}")
        
        # Check for opportunity-specific patterns
        opportunity_patterns = [
            "trading opportunities",
            "profit potential",
            "buy signal",
            "sell signal",
            "momentum",
            "breakout",
            "arbitrage",
            "scalping",
            "market making"
        ]
        
        opportunity_matches = [pattern for pattern in opportunity_patterns if pattern.lower() in content.lower()]
        print(f"   Trading opportunity patterns found: {len(opportunity_matches)}/{len(opportunity_patterns)}")
        print(f"   Matches: {opportunity_matches}")
        
        # Check for strategy-specific patterns
        strategy_patterns = [
            "spot momentum",
            "mean reversion",
            "breakout strategy",
            "pairs trading",
            "statistical arbitrage",
            "funding arbitrage",
            "futures trading",
            "options trading"
        ]
        
        strategy_matches = [pattern for pattern in strategy_patterns if pattern.lower() in content.lower()]
        print(f"   Strategy-specific patterns found: {len(strategy_matches)}/{len(strategy_patterns)}")
        print(f"   Matches: {strategy_matches}")
        
        # Check for template/fallback patterns
        template_patterns = [
            "based on your risk tolerance",
            "optimization metrics",
            "balanced strategy",
            "diversification",
            "moderate risk tolerance",
            "medium-term investment horizon",
            "strategic portfolio manager",
            "model-based forecasts"
        ]
        
        template_matches = [pattern for pattern in template_patterns if pattern.lower() in content.lower()]
        print(f"   Template/fallback patterns found: {len(template_matches)}/{len(template_patterns)}")
        print(f"   Matches: {template_matches}")
        
        # Determine the response type
        print(f"\n🎭 RESPONSE TYPE ANALYSIS:")
        if len(portfolio_matches) > 3 and len(opportunity_matches) < 2:
            print(f"   📊 LIKELY: Portfolio optimization fallback response")
            print(f"   💡 This suggests the system fell back to portfolio optimization only")
        elif len(strategy_matches) > 2:
            print(f"   🎯 LIKELY: Multi-strategy opportunity response")
            print(f"   💡 This suggests multiple strategies are working")
        elif len(template_matches) > 3:
            print(f"   🎭 LIKELY: Template/placeholder response")
            print(f"   💡 This suggests the system is using fallback content")
        else:
            print(f"   ❓ UNKNOWN: Mixed or unclear response type")
        
        # Check context data
        context = result.get('context', {})
        if context:
            print(f"\n📊 CONTEXT DATA:")
            for key, value in context.items():
                if isinstance(value, dict):
                    print(f"   {key}: {list(value.keys())}")
                else:
                    print(f"   {key}: {value}")
        
        # Check metadata
        metadata = result.get('metadata', {})
        if metadata:
            print(f"\n📋 METADATA:")
            for key, value in metadata.items():
                print(f"   {key}: {value}")
        
        # Save the full response
        with open(f'/workspace/detailed_chat_response_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n💾 Full response saved to detailed_chat_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        return result
    else:
        print(f"❌ FAILED: Chat response returned status {chat_response.status_code}")
        print(f"Response: {chat_response.text}")
        return None

if __name__ == "__main__":
    test_chat_content_detailed()