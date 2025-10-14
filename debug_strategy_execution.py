#!/usr/bin/env python3
"""
Debug Strategy Execution - Find out why strategy execution fails
when the user clearly has 35 strategies.
"""

import requests
import json
from datetime import datetime

def debug_strategy_execution():
    """Debug why strategy execution fails despite having 35 strategies."""
    
    print("🔍 DEBUGGING STRATEGY EXECUTION")
    print("Finding out why strategy execution fails despite having 35 strategies")
    
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
    
    # Test 1: Check opportunity discovery with detailed logging
    print("\n2. Testing opportunity discovery with detailed analysis...")
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
            print(f"   Scan state: {opp_data.get('scan_state', 'unknown')}")
            print(f"   Message: {opp_data.get('message', 'No message')[:100]}...")
            
            # Check user profile
            if 'user_profile' in opp_data:
                user_profile = opp_data['user_profile']
                print(f"   📊 User profile:")
                print(f"      Active strategies: {user_profile.get('active_strategies', 0)}")
                print(f"      User tier: {user_profile.get('user_tier', 'unknown')}")
                print(f"      Monthly cost: {user_profile.get('monthly_strategy_cost', 0)}")
                print(f"      Strategy fingerprint: {user_profile.get('strategy_fingerprint', 'unknown')}")
            
            # Check signal analysis
            if 'signal_analysis' in opp_data:
                signal_analysis = opp_data['signal_analysis']
                print(f"   📊 Signal analysis:")
                print(f"      Total signals analyzed: {signal_analysis.get('total_signals_analyzed', 0)}")
                print(f"      Signals by strength: {signal_analysis.get('signals_by_strength', {})}")
            
            # Check threshold transparency
            if 'threshold_transparency' in opp_data:
                threshold = opp_data['threshold_transparency']
                print(f"   📊 Threshold transparency:")
                print(f"      Message: {threshold.get('message', 'No message')}")
                print(f"      Recommendation: {threshold.get('recommendation', 'No recommendation')}")
            
            # Check strategy performance
            if 'strategy_performance' in opp_data:
                strategy_perf = opp_data['strategy_performance']
                print(f"   📊 Strategy performance:")
                for key, value in strategy_perf.items():
                    print(f"      {key}: {value}")
            
            # Check asset discovery
            if 'asset_discovery' in opp_data:
                asset_discovery = opp_data['asset_discovery']
                print(f"   📊 Asset discovery:")
                for key, value in asset_discovery.items():
                    print(f"      {key}: {value}")
            
            # Check execution time
            if 'execution_time_ms' in opp_data:
                print(f"   ⏱️  Execution time: {opp_data['execution_time_ms']}ms")
            
            # Check metadata
            if 'metadata' in opp_data:
                metadata = opp_data['metadata']
                print(f"   📋 Metadata:")
                for key, value in metadata.items():
                    print(f"      {key}: {value}")
            
            # Save full response for analysis
            with open(f'/workspace/opportunity_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
                json.dump(opp_data, f, indent=2, default=str)
            
            print(f"   💾 Full response saved to opportunity_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
        else:
            print(f"   ❌ Opportunity discovery failed: {opportunity_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Opportunity discovery error: {e}")
    
    # Test 2: Check chat opportunity discovery
    print("\n3. Testing chat opportunity discovery...")
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
            print(f"   ✅ Chat data received")
            print(f"   Success: {chat_data.get('success', False)}")
            print(f"   Intent: {chat_data.get('intent', 'unknown')}")
            print(f"   Content length: {len(chat_data.get('content', ''))}")
            
            # Check context for opportunity data
            context = chat_data.get('context', {})
            if 'opportunities' in context:
                opp_context = context['opportunities']
                print(f"   📊 Opportunities context:")
                print(f"      Success: {opp_context.get('success', False)}")
                print(f"      Total opportunities: {opp_context.get('total_opportunities', 0)}")
                print(f"      Strategy results: {len(opp_context.get('strategy_results', {}))}")
                
                # Check user profile in context
                if 'user_profile' in opp_context:
                    user_profile = opp_context['user_profile']
                    print(f"      User profile:")
                    print(f"         Active strategies: {user_profile.get('active_strategies', 0)}")
                    print(f"         User tier: {user_profile.get('user_tier', 'unknown')}")
            
            # Show content snippet
            content = chat_data.get('content', '')
            print(f"   📝 Content snippet: {content[:200]}...")
            
        else:
            print(f"   ❌ Chat failed: {chat_response.text[:200]}")
    except Exception as e:
        print(f"   💥 Chat error: {e}")
    
    print(f"\n{'='*80}")
    print("📊 STRATEGY EXECUTION DEBUGGING COMPLETE")
    print(f"{'='*80}")
    print("Key findings:")
    print("1. Admin has 35 strategies (not 5, not 14)")
    print("2. Portfolio service works (returns 35 strategies)")
    print("3. Opportunity discovery returns 0 opportunities")
    print("4. Need to find why strategy execution fails")

if __name__ == "__main__":
    debug_strategy_execution()