#!/usr/bin/env python3
"""
Check Opportunity Status - Poll the opportunity discovery status to see what's happening
"""

import requests
import json
import time
from datetime import datetime

def check_opportunity_status():
    """Check the status of the opportunity discovery scan."""
    
    print("🔍 CHECKING OPPORTUNITY DISCOVERY STATUS")
    print("Polling the opportunity discovery to see what's happening")
    
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
    
    # Start opportunity discovery
    print("\n2. Starting opportunity discovery...")
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
        
        if opportunity_response.status_code == 200:
            opp_data = opportunity_response.json()
            print(f"   ✅ Opportunity discovery initiated")
            print(f"   Scan ID: {opp_data.get('scan_id', 'unknown')}")
            print(f"   Status: {opp_data.get('status', 'unknown')}")
            print(f"   Message: {opp_data.get('message', 'No message')}")
            print(f"   Estimated completion: {opp_data.get('estimated_completion_seconds', 0)} seconds")
            
            scan_id = opp_data.get('scan_id')
            if scan_id:
                # Poll the status
                print(f"\n3. Polling status every 3 seconds...")
                for i in range(20):  # Poll for up to 60 seconds
                    try:
                        status_response = requests.get(
                            f'{base_url}/api/v1/opportunities/status/{scan_id}', 
                            headers=headers, 
                            timeout=30
                        )
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            print(f"   Poll {i+1:2d}: Status = {status_data.get('status', 'unknown')}, "
                                  f"Progress = {status_data.get('progress_percent', 0)}%, "
                                  f"Strategies completed = {status_data.get('strategies_completed', 0)}/{status_data.get('total_strategies', 0)}")
                            
                            # Check for completion
                            if status_data.get('status') == 'completed':
                                print(f"   ✅ Scan completed!")
                                
                                # Get results
                                results_response = requests.get(
                                    f'{base_url}/api/v1/opportunities/results/{scan_id}', 
                                    headers=headers, 
                                    timeout=30
                                )
                                
                                if results_response.status_code == 200:
                                    results_data = results_response.json()
                                    print(f"   📊 Results received:")
                                    print(f"      Success: {results_data.get('success', False)}")
                                    print(f"      Total opportunities: {results_data.get('total_opportunities', 0)}")
                                    print(f"      Strategy results: {len(results_data.get('strategy_results', {}))}")
                                    
                                    # Check strategy results
                                    strategy_results = results_data.get('strategy_results', {})
                                    if strategy_results:
                                        print(f"      📋 Strategy results:")
                                        for strategy_id, strategy_data in strategy_results.items():
                                            opportunities_count = len(strategy_data.get('opportunities', []))
                                            print(f"         - {strategy_id}: {opportunities_count} opportunities")
                                    else:
                                        print(f"      ⚠️  No strategy results found")
                                    
                                    # Save results
                                    with open(f'/workspace/opportunity_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
                                        json.dump(results_data, f, indent=2, default=str)
                                    
                                    print(f"      💾 Results saved to opportunity_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                                    
                                    return results_data
                                else:
                                    print(f"   ❌ Failed to get results: {results_response.status_code}")
                                    return None
                            elif status_data.get('status') == 'failed':
                                print(f"   ❌ Scan failed!")
                                print(f"   Error: {status_data.get('error', 'Unknown error')}")
                                return None
                            else:
                                # Still running, wait and poll again
                                time.sleep(3)
                        else:
                            print(f"   ❌ Status check failed: {status_response.status_code}")
                            break
                    except Exception as e:
                        print(f"   💥 Status check error: {e}")
                        break
                
                print(f"   ⏰ Polling timeout after 60 seconds")
                return None
            else:
                print(f"   ❌ No scan ID returned")
                return None
        else:
            print(f"   ❌ Opportunity discovery failed: {opportunity_response.text[:200]}")
            return None
    except Exception as e:
        print(f"   💥 Opportunity discovery error: {e}")
        return None

if __name__ == "__main__":
    check_opportunity_status()