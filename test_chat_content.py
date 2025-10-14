#!/usr/bin/env python3
"""
Test Chat Content - Get the actual chat response content to see what's being generated
"""

import requests
import json
from datetime import datetime

def test_chat_content():
    """Get the actual chat response content."""
    
    print("🔍 CHAT CONTENT ANALYSIS")
    print("Getting the actual chat response to see what's being generated")
    
    try:
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
            print(f"\n📝 ACTUAL CHAT RESPONSE CONTENT:")
            print("="*80)
            print(content)
            print("="*80)
            
            # Analyze the content
            print(f"\n📋 CONTENT ANALYSIS:")
            print(f"   Length: {len(content)} characters")
            print(f"   Mentions 'opportunity': {'opportunity' in content.lower()}")
            print(f"   Mentions 'profit': {'profit' in content.lower()}")
            print(f"   Mentions 'trading': {'trading' in content.lower()}")
            print(f"   Mentions 'portfolio': {'portfolio' in content.lower()}")
            print(f"   Mentions 'optimization': {'optimization' in content.lower()}")
            print(f"   Mentions 'strategy': {'strategy' in content.lower()}")
            print(f"   Mentions 'risk': {'risk' in content.lower()}")
            print(f"   Mentions 'investment': {'investment' in content.lower()}")
            
            # Check if it's a template response
            template_indicators = [
                "Based on your risk tolerance",
                "optimization metrics",
                "balanced strategy",
                "diversification",
                "rebalancing",
                "moderate risk tolerance",
                "medium-term investment horizon"
            ]
            
            template_count = sum(1 for indicator in template_indicators if indicator in content)
            print(f"\n🎭 TEMPLATE ANALYSIS:")
            print(f"   Template indicators found: {template_count}/{len(template_indicators)}")
            print(f"   Likely template response: {'YES' if template_count > 3 else 'NO'}")
            
            # Save the full response
            with open(f'/workspace/chat_response_content_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            print(f"\n💾 Full response saved to chat_response_content_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            return result
        else:
            print(f"❌ FAILED: Chat response returned status {chat_response.status_code}")
            print(f"Response: {chat_response.text}")
            return None
            
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return None

if __name__ == "__main__":
    test_chat_content()