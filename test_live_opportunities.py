#!/usr/bin/env python3
"""
Live Opportunity Testing - Test the actual opportunity discovery endpoint
to see what's really happening in production.
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime
from typing import Dict, List, Any

async def test_live_opportunity_discovery():
    """Test the live opportunity discovery endpoint."""
    
    print("🚀 LIVE OPPORTUNITY DISCOVERY TESTING")
    print("Testing the actual opportunity discovery endpoint in production")
    
    try:
        import requests
        
        # Test the live endpoint
        base_url = "https://cryptouniverse.onrender.com"
        
        # First, get auth token
        print("\n1. Getting authentication token...")
        login_data = {
            'email': 'admin@cryptouniverse.com',
            'password': 'AdminPass123!'
        }
        
        login_response = requests.post(f'{base_url}/api/v1/auth/login', json=login_data, timeout=30)
        print(f"   Login status: {login_response.status_code}")
        
        if login_response.status_code != 200:
            print(f"   ❌ Login failed: {login_response.text}")
            return
        
        token = login_response.json().get('access_token')
        print(f"   ✅ Token received: {token[:20]}...")
        
        # Test opportunity discovery endpoint
        print("\n2. Testing opportunity discovery endpoint...")
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        
        # Test with force_refresh to get fresh data
        opportunity_data = {
            'force_refresh': True,
            'include_strategy_recommendations': True
        }
        
        print("   📞 Calling opportunity discovery endpoint...")
        start_time = datetime.now()
        
        opportunity_response = requests.post(
            f'{base_url}/api/v1/opportunities/discover', 
            headers=headers, 
            json=opportunity_data,
            timeout=60  # Give it more time
        )
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print(f"   ⏱️  Execution time: {execution_time:.2f} seconds")
        print(f"   📊 Status: {opportunity_response.status_code}")
        
        if opportunity_response.status_code == 200:
            result = opportunity_response.json()
            print(f"   ✅ SUCCESS: Opportunity discovery completed")
            
            # Analyze the response
            print(f"\n   📋 Response Analysis:")
            print(f"      Success: {result.get('success', False)}")
            print(f"      Total opportunities: {result.get('total_opportunities', 0)}")
            print(f"      Opportunities array length: {len(result.get('opportunities', []))}")
            print(f"      Strategy results: {len(result.get('strategy_results', {}))}")
            print(f"      Scan state: {result.get('scan_state', 'unknown')}")
            print(f"      Message: {result.get('message', 'No message')[:100]}...")
            
            # Check strategy results
            strategy_results = result.get('strategy_results', {})
            if strategy_results:
                print(f"\n   🎯 Strategy Results:")
                for strategy_id, strategy_data in strategy_results.items():
                    opportunities_count = len(strategy_data.get('opportunities', []))
                    print(f"      - {strategy_id}: {opportunities_count} opportunities")
            else:
                print(f"   ⚠️  No strategy results found")
            
            # Check individual opportunities
            opportunities = result.get('opportunities', [])
            if opportunities:
                print(f"\n   📈 Sample Opportunities:")
                for i, opp in enumerate(opportunities[:3]):  # Show first 3
                    print(f"      {i+1}. {opp.get('symbol', 'N/A')} - {opp.get('opportunity_type', 'N/A')} - ${opp.get('profit_potential_usd', 0)}")
            else:
                print(f"   ⚠️  No opportunities found")
            
            # Check for errors
            if 'error' in result:
                print(f"   ❌ Error in response: {result['error']}")
            
            return {
                "status": "SUCCESS",
                "execution_time": execution_time,
                "total_opportunities": result.get('total_opportunities', 0),
                "opportunities_count": len(result.get('opportunities', [])),
                "strategy_results_count": len(result.get('strategy_results', {})),
                "scan_state": result.get('scan_state', 'unknown'),
                "has_error": 'error' in result,
                "error": result.get('error') if 'error' in result else None
            }
        else:
            print(f"   ❌ FAILED: Opportunity discovery returned status {opportunity_response.status_code}")
            print(f"   Response: {opportunity_response.text[:200]}...")
            
            return {
                "status": "FAILED",
                "execution_time": execution_time,
                "status_code": opportunity_response.status_code,
                "error": opportunity_response.text
            }
            
    except Exception as e:
        print(f"💥 CRITICAL ERROR: Failed to test live opportunity discovery")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        print(f"   Traceback:")
        traceback.print_exc()
        return {
            "status": "ERROR",
            "execution_time": 0,
            "error": f"{type(e).__name__}: {str(e)}"
        }

async def test_chat_opportunity_discovery():
    """Test opportunity discovery through chat interface."""
    
    print("\n" + "="*80)
    print("3. Testing Chat Opportunity Discovery")
    print("="*80)
    
    try:
        import requests
        
        base_url = "https://cryptouniverse.onrender.com"
        
        # Get auth token
        login_data = {
            'email': 'admin@cryptouniverse.com',
            'password': 'AdminPass123!'
        }
        
        login_response = requests.post(f'{base_url}/api/v1/auth/login', json=login_data, timeout=30)
        
        if login_response.status_code != 200:
            print(f"   ❌ Login failed: {login_response.text}")
            return
        
        token = login_response.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        
        # Test chat opportunity discovery
        chat_data = {
            'message': 'Find the best opportunities now',
            'include_context': True
        }
        
        print("   📞 Calling chat opportunity discovery...")
        start_time = datetime.now()
        
        chat_response = requests.post(
            f'{base_url}/api/v1/chat/message', 
            headers=headers, 
            json=chat_data,
            timeout=60
        )
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print(f"   ⏱️  Execution time: {execution_time:.2f} seconds")
        print(f"   📊 Status: {chat_response.status_code}")
        
        if chat_response.status_code == 200:
            result = chat_response.json()
            print(f"   ✅ SUCCESS: Chat opportunity discovery completed")
            
            # Analyze the response
            print(f"\n   📋 Chat Response Analysis:")
            print(f"      Success: {result.get('success', False)}")
            print(f"      Intent: {result.get('intent', 'unknown')}")
            print(f"      Content length: {len(result.get('content', ''))}")
            print(f"      Has opportunities: {'opportunities' in result}")
            print(f"      Has strategy results: {'strategy_results' in result}")
            
            if 'opportunities' in result:
                opportunities = result['opportunities']
                print(f"      Opportunities count: {len(opportunities)}")
                
                if opportunities:
                    print(f"   📈 Sample Chat Opportunities:")
                    for i, opp in enumerate(opportunities[:3]):
                        print(f"      {i+1}. {opp.get('symbol', 'N/A')} - {opp.get('opportunity_type', 'N/A')} - ${opp.get('profit_potential_usd', 0)}")
            
            if 'strategy_results' in result:
                strategy_results = result['strategy_results']
                print(f"      Strategy results count: {len(strategy_results)}")
                
                for strategy_id, strategy_data in strategy_results.items():
                    opportunities_count = len(strategy_data.get('opportunities', []))
                    print(f"         - {strategy_id}: {opportunities_count} opportunities")
            
            # Check content for opportunity mentions
            content = result.get('content', '')
            if 'opportunity' in content.lower() or 'profit' in content.lower():
                print(f"   📝 Content mentions opportunities/profits")
            else:
                print(f"   ⚠️  Content doesn't mention opportunities/profits")
            
            return {
                "status": "SUCCESS",
                "execution_time": execution_time,
                "intent": result.get('intent', 'unknown'),
                "content_length": len(result.get('content', '')),
                "has_opportunities": 'opportunities' in result,
                "opportunities_count": len(result.get('opportunities', [])),
                "has_strategy_results": 'strategy_results' in result,
                "strategy_results_count": len(result.get('strategy_results', {}))
            }
        else:
            print(f"   ❌ FAILED: Chat opportunity discovery returned status {chat_response.status_code}")
            print(f"   Response: {chat_response.text[:200]}...")
            
            return {
                "status": "FAILED",
                "execution_time": execution_time,
                "status_code": chat_response.status_code,
                "error": chat_response.text
            }
            
    except Exception as e:
        print(f"💥 CRITICAL ERROR: Failed to test chat opportunity discovery")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        return {
            "status": "ERROR",
            "execution_time": 0,
            "error": f"{type(e).__name__}: {str(e)}"
        }

async def main():
    """Run all tests."""
    
    print("🔍 COMPREHENSIVE OPPORTUNITY DISCOVERY TESTING")
    print("Testing both direct endpoint and chat interface")
    
    # Test direct opportunity discovery
    direct_result = await test_live_opportunity_discovery()
    
    # Test chat opportunity discovery
    chat_result = await test_chat_opportunity_discovery()
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 COMPREHENSIVE TESTING SUMMARY")
    print(f"{'='*80}")
    
    print(f"Direct Endpoint: {direct_result.get('status', 'UNKNOWN')}")
    if direct_result.get('status') == 'SUCCESS':
        print(f"   - Total opportunities: {direct_result.get('total_opportunities', 0)}")
        print(f"   - Strategy results: {direct_result.get('strategy_results_count', 0)}")
        print(f"   - Execution time: {direct_result.get('execution_time', 0):.2f}s")
    
    print(f"Chat Interface: {chat_result.get('status', 'UNKNOWN')}")
    if chat_result.get('status') == 'SUCCESS':
        print(f"   - Intent: {chat_result.get('intent', 'unknown')}")
        print(f"   - Opportunities: {chat_result.get('opportunities_count', 0)}")
        print(f"   - Strategy results: {chat_result.get('strategy_results_count', 0)}")
        print(f"   - Execution time: {chat_result.get('execution_time', 0):.2f}s")
    
    # Save results
    results = {
        "direct_endpoint": direct_result,
        "chat_interface": chat_result,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(f'/workspace/live_opportunity_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to live_opportunity_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

if __name__ == "__main__":
    asyncio.run(main())