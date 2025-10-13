#!/usr/bin/env python3
"""
Debug Strategy Access - Find out why admin only sees 5 strategies instead of 14
and why strategy execution fails.
"""

import requests
import json
from datetime import datetime

def debug_strategy_access():
    """Debug why admin only sees 5 strategies instead of 14."""
    
    print("🔍 DEBUGGING STRATEGY ACCESS")
    print("Finding out why admin only sees 5 strategies instead of 14")
    
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
    
    # Test 1: Check admin strategy access endpoint
    print("\n2. Testing admin strategy access endpoint...")
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
            print(f"   Current strategies: {admin_data.get('current_strategies', 0)}")
            print(f"   Total available strategies: {admin_data.get('total_available_strategies', 0)}")
        else:
            print(f"   ❌ Admin access failed: {admin_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Admin access error: {e}")
    
    # Test 2: Check marketplace strategies
    print("\n3. Testing marketplace strategies...")
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
                print(f"   📋 All available strategies:")
                for i, strategy in enumerate(marketplace_data['strategies']):
                    print(f"      {i+1:2d}. {strategy.get('strategy_id', 'N/A'):30s} - {strategy.get('name', 'N/A')}")
        else:
            print(f"   ❌ Marketplace failed: {marketplace_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Marketplace error: {e}")
    
    # Test 3: Check user portfolio (with longer timeout)
    print("\n4. Testing user portfolio with longer timeout...")
    try:
        portfolio_response = requests.get(
            f'{base_url}/api/v1/unified-strategies/portfolio', 
            headers=headers, 
            timeout=60  # Longer timeout
        )
        
        print(f"   Portfolio status: {portfolio_response.status_code}")
        if portfolio_response.status_code == 200:
            portfolio_data = portfolio_response.json()
            print(f"   ✅ Portfolio data received")
            print(f"   Success: {portfolio_data.get('success', False)}")
            print(f"   Active strategies: {len(portfolio_data.get('active_strategies', []))}")
            print(f"   Total strategies: {portfolio_data.get('total_strategies', 0)}")
            
            if portfolio_data.get('active_strategies'):
                print(f"   📋 User's active strategies:")
                for i, strategy in enumerate(portfolio_data['active_strategies']):
                    print(f"      {i+1:2d}. {strategy.get('strategy_id', 'N/A'):30s} - {strategy.get('name', 'N/A')}")
        else:
            print(f"   ❌ Portfolio failed: {portfolio_response.text[:200]}")
    except requests.exceptions.Timeout:
        print(f"   ⏰ Portfolio timed out after 60 seconds")
    except Exception as e:
        print(f"   💥 Portfolio error: {e}")
    
    # Test 4: Check what strategies the chat system thinks user has
    print("\n5. Testing chat strategy access...")
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
            
            # Show the actual content
            content = chat_data.get('content', '')
            print(f"   📝 Chat response content:")
            print(f"   {content[:500]}...")
            
            # Check context for strategy data
            context = chat_data.get('context', {})
            if 'user_config' in context:
                user_config = context['user_config']
                print(f"   📊 User config from context:")
                for key, value in user_config.items():
                    print(f"      {key}: {value}")
        else:
            print(f"   ❌ Chat failed: {chat_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Chat error: {e}")
    
    # Test 5: Check opportunity discovery context
    print("\n6. Testing opportunity discovery context...")
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
            print(f"   Strategy results: {len(opp_data.get('strategy_results', {}))}")
            
            # Check user profile in opportunities response
            if 'user_profile' in opp_data:
                user_profile = opp_data['user_profile']
                print(f"   📊 User profile from opportunities:")
                print(f"      Active strategies: {user_profile.get('active_strategies', 0)}")
                print(f"      User tier: {user_profile.get('user_tier', 'unknown')}")
                print(f"      Monthly cost: {user_profile.get('monthly_strategy_cost', 0)}")
            
            # Check strategy results
            strategy_results = opp_data.get('strategy_results', {})
            if strategy_results:
                print(f"   📋 Strategy results:")
                for strategy_id, strategy_data in strategy_results.items():
                    opportunities_count = len(strategy_data.get('opportunities', []))
                    print(f"      - {strategy_id}: {opportunities_count} opportunities")
            else:
                print(f"   ⚠️  No strategy results found")
        else:
            print(f"   ❌ Opportunity discovery failed: {opportunity_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Opportunity discovery error: {e}")
    
    print(f"\n{'='*80}")
    print("📊 STRATEGY ACCESS DEBUGGING COMPLETE")
    print(f"{'='*80}")
    print("This will help identify:")
    print("1. How many strategies admin actually has access to")
    print("2. Why only 5 strategies are shown in chat")
    print("3. Why strategy execution fails in opportunity discovery")

if __name__ == "__main__":
    debug_strategy_access()