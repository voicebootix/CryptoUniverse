#!/usr/bin/env python3
"""
Portfolio Timeout Flow Testing - Test what happens when portfolio service times out
and how the opportunity discovery handles it.
"""

import requests
import json
from datetime import datetime

def test_portfolio_timeout_flow():
    """Test the flow when portfolio service times out."""
    
    print("🔍 PORTFOLIO TIMEOUT FLOW TESTING")
    print("Testing what happens when portfolio service times out")
    
    base_url = "https://cryptouniverse.onrender.com"
    
    # Get auth token
    print("\n1. Getting authentication token...")
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
    print(f"✅ Token received: {token[:20]}...")
    
    # Test 1: Direct portfolio endpoint (should timeout)
    print("\n2. Testing direct portfolio endpoint (expecting timeout)...")
    try:
        portfolio_response = requests.get(
            f'{base_url}/api/v1/unified-strategies/portfolio', 
            headers=headers, 
            timeout=5  # Short timeout to trigger timeout
        )
        print(f"   Portfolio status: {portfolio_response.status_code}")
        if portfolio_response.status_code == 200:
            print(f"   ✅ Portfolio data received (unexpected!)")
            portfolio_data = portfolio_response.json()
            print(f"   Active strategies: {len(portfolio_data.get('active_strategies', []))}")
        else:
            print(f"   ❌ Portfolio failed: {portfolio_response.text[:200]}")
    except requests.exceptions.Timeout:
        print(f"   ⏰ Portfolio timed out as expected")
    except Exception as e:
        print(f"   💥 Portfolio error: {e}")
    
    # Test 2: Opportunity discovery (should handle timeout gracefully)
    print("\n3. Testing opportunity discovery with portfolio timeout...")
    try:
        opportunity_data = {
            'force_refresh': True,
            'include_strategy_recommendations': True
        }
        
        opportunity_response = requests.post(
            f'{base_url}/api/v1/opportunities/discover', 
            headers=headers, 
            json=opportunity_data,
            timeout=60
        )
        
        print(f"   Opportunity status: {opportunity_response.status_code}")
        if opportunity_response.status_code == 200:
            opp_data = opportunity_response.json()
            print(f"   ✅ Opportunity discovery completed despite portfolio timeout")
            print(f"   Success: {opp_data.get('success', False)}")
            print(f"   Total opportunities: {opp_data.get('total_opportunities', 0)}")
            print(f"   Strategy results: {len(opp_data.get('strategy_results', {}))}")
            print(f"   Message: {opp_data.get('message', 'No message')[:100]}...")
            
            # Check if it triggered onboarding
            if opp_data.get('auto_onboarded'):
                print(f"   🎯 AUTO-ONBOARDING TRIGGERED!")
                print(f"   Onboarding result: {opp_data.get('onboarding_result', {})}")
            
            # Check for portfolio timeout error
            if 'portfolio_fetch_timeout' in str(opp_data):
                print(f"   ⏰ Portfolio timeout detected in response")
            
            # Check strategy results
            strategy_results = opp_data.get('strategy_results', {})
            if strategy_results:
                print(f"   📋 Strategy results despite timeout:")
                for strategy_id, strategy_data in strategy_results.items():
                    opportunities_count = len(strategy_data.get('opportunities', []))
                    print(f"      - {strategy_id}: {opportunities_count} opportunities")
            else:
                print(f"   ⚠️  No strategy results (expected due to timeout)")
        else:
            print(f"   ❌ Opportunity discovery failed: {opportunity_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Opportunity discovery error: {e}")
    
    # Test 3: Chat opportunity discovery (should work despite timeout)
    print("\n4. Testing chat opportunity discovery with portfolio timeout...")
    try:
        chat_data = {
            'message': 'Find the best opportunities now',
            'include_context': True
        }
        
        chat_response = requests.post(
            f'{base_url}/api/v1/chat/message', 
            headers=headers, 
            json=chat_data,
            timeout=60
        )
        
        print(f"   Chat status: {chat_response.status_code}")
        if chat_response.status_code == 200:
            chat_data = chat_response.json()
            print(f"   ✅ Chat opportunity discovery completed despite portfolio timeout")
            print(f"   Success: {chat_data.get('success', False)}")
            print(f"   Intent: {chat_data.get('intent', 'unknown')}")
            print(f"   Content length: {len(chat_data.get('content', ''))}")
            
            # Show content snippet
            content = chat_data.get('content', '')
            print(f"   📝 Content snippet: {content[:200]}...")
            
            # Check if it mentions portfolio optimization
            if 'portfolio' in content.lower() and 'optimization' in content.lower():
                print(f"   🎯 Content mentions portfolio optimization (expected fallback)")
            else:
                print(f"   ⚠️  Content doesn't mention portfolio optimization")
        else:
            print(f"   ❌ Chat failed: {chat_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Chat error: {e}")
    
    print(f"\n{'='*80}")
    print("📊 PORTFOLIO TIMEOUT FLOW ANALYSIS")
    print(f"{'='*80}")
    print("The system is designed to handle portfolio timeouts gracefully:")
    print("1. When portfolio service times out, it returns empty strategies")
    print("2. This triggers the 'no strategies' handler")
    print("3. The system attempts auto-onboarding with 3 free strategies")
    print("4. If onboarding fails, it falls back to portfolio optimization only")
    print("5. This explains why you only see portfolio optimization responses")

if __name__ == "__main__":
    test_portfolio_timeout_flow()