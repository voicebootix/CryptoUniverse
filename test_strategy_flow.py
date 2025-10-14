#!/usr/bin/env python3
"""
Strategy Flow Testing - Test the actual strategy provisioning and access flow
to see where it's failing in the pipeline.
"""

import requests
import json
from datetime import datetime

def test_strategy_flow():
    """Test the complete strategy flow from provisioning to opportunity discovery."""
    
    print("🔍 STRATEGY FLOW TESTING")
    print("Testing the complete flow from strategy access to opportunity discovery")
    
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
    
    # Test 1: Check user's strategy portfolio
    print("\n2. Testing user strategy portfolio...")
    try:
        portfolio_response = requests.get(
            f'{base_url}/api/v1/unified-strategies/portfolio', 
            headers=headers, 
            timeout=30
        )
        
        print(f"   Portfolio status: {portfolio_response.status_code}")
        if portfolio_response.status_code == 200:
            portfolio_data = portfolio_response.json()
            print(f"   ✅ Portfolio data received")
            print(f"   Success: {portfolio_data.get('success', False)}")
            print(f"   Active strategies: {len(portfolio_data.get('active_strategies', []))}")
            print(f"   Total strategies: {portfolio_data.get('total_strategies', 0)}")
            
            if portfolio_data.get('active_strategies'):
                print(f"   📋 Active strategies:")
                for strategy in portfolio_data['active_strategies'][:5]:  # Show first 5
                    print(f"      - {strategy.get('strategy_id', 'N/A')}: {strategy.get('name', 'N/A')}")
        else:
            print(f"   ❌ Portfolio failed: {portfolio_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Portfolio error: {e}")
    
    # Test 2: Check admin strategy access
    print("\n3. Testing admin strategy access...")
    try:
        admin_response = requests.get(
            f'{base_url}/api/v1/admin-strategy-access/admin-portfolio-status', 
            headers=headers, 
            timeout=30
        )
        
        print(f"   Admin status: {admin_response.status_code}")
        if admin_response.status_code == 200:
            admin_data = admin_response.json()
            print(f"   ✅ Admin data received")
            print(f"   Success: {admin_data.get('success', False)}")
            print(f"   Has full access: {admin_data.get('has_full_access', False)}")
            print(f"   Available strategies: {admin_data.get('available_strategies', 0)}")
            print(f"   Active strategies: {admin_data.get('active_strategies', 0)}")
        else:
            print(f"   ❌ Admin access failed: {admin_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Admin access error: {e}")
    
    # Test 3: Check marketplace strategies
    print("\n4. Testing marketplace strategies...")
    try:
        marketplace_response = requests.get(
            f'{base_url}/api/v1/strategies/marketplace', 
            headers=headers, 
            timeout=30
        )
        
        print(f"   Marketplace status: {marketplace_response.status_code}")
        if marketplace_response.status_code == 200:
            marketplace_data = marketplace_response.json()
            print(f"   ✅ Marketplace data received")
            print(f"   Success: {marketplace_data.get('success', False)}")
            print(f"   Strategies count: {len(marketplace_data.get('strategies', []))}")
            
            if marketplace_data.get('strategies'):
                print(f"   📋 Available strategies:")
                for strategy in marketplace_data['strategies'][:5]:  # Show first 5
                    print(f"      - {strategy.get('strategy_id', 'N/A')}: {strategy.get('name', 'N/A')}")
        else:
            print(f"   ❌ Marketplace failed: {marketplace_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Marketplace error: {e}")
    
    # Test 4: Check opportunity discovery with detailed logging
    print("\n5. Testing opportunity discovery with detailed analysis...")
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
            print(f"   ✅ Opportunity data received")
            print(f"   Success: {opp_data.get('success', False)}")
            print(f"   Total opportunities: {opp_data.get('total_opportunities', 0)}")
            print(f"   Opportunities array: {len(opp_data.get('opportunities', []))}")
            print(f"   Strategy results: {len(opp_data.get('strategy_results', {}))}")
            print(f"   Scan state: {opp_data.get('scan_state', 'unknown')}")
            print(f"   Message: {opp_data.get('message', 'No message')[:100]}...")
            
            # Check strategy results in detail
            strategy_results = opp_data.get('strategy_results', {})
            if strategy_results:
                print(f"   📋 Strategy results details:")
                for strategy_id, strategy_data in strategy_results.items():
                    opportunities_count = len(strategy_data.get('opportunities', []))
                    print(f"      - {strategy_id}: {opportunities_count} opportunities")
                    if 'error' in strategy_data:
                        print(f"        Error: {strategy_data['error']}")
            else:
                print(f"   ⚠️  No strategy results found")
            
            # Check for any errors in the response
            if 'error' in opp_data:
                print(f"   ❌ Error in response: {opp_data['error']}")
            
            # Check metadata for more details
            metadata = opp_data.get('metadata', {})
            if metadata:
                print(f"   📊 Metadata:")
                for key, value in metadata.items():
                    print(f"      - {key}: {value}")
        else:
            print(f"   ❌ Opportunity discovery failed: {opportunity_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Opportunity discovery error: {e}")
    
    # Test 5: Check chat strategy access
    print("\n6. Testing chat strategy access...")
    try:
        chat_data = {
            'message': 'What strategies do I have access to?',
            'include_context': True
        }
        
        chat_response = requests.post(
            f'{base_url}/api/v1/chat/message', 
            headers=headers, 
            json=chat_data,
            timeout=30
        )
        
        print(f"   Chat status: {chat_response.status_code}")
        if chat_response.status_code == 200:
            chat_data = chat_response.json()
            print(f"   ✅ Chat data received")
            print(f"   Success: {chat_data.get('success', False)}")
            print(f"   Intent: {chat_data.get('intent', 'unknown')}")
            print(f"   Content length: {len(chat_data.get('content', ''))}")
            
            # Show the actual content
            content = chat_data.get('content', '')
            print(f"   📝 Chat response content:")
            print(f"   {content[:300]}...")
        else:
            print(f"   ❌ Chat failed: {chat_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Chat error: {e}")
    
    print(f"\n{'='*80}")
    print("📊 STRATEGY FLOW ANALYSIS COMPLETE")
    print(f"{'='*80}")

if __name__ == "__main__":
    test_strategy_flow()