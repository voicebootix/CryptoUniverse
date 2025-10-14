#!/usr/bin/env python3
"""
Enterprise Strategy Fixes - Comprehensive Solution
"""

import requests
import json
import asyncio
import time
import os

def test_opportunity_discovery():
    """Test the opportunity discovery endpoint to see if it works now."""
    print("🔍 TESTING OPPORTUNITY DISCOVERY")
    print("=" * 50)
    
    # Get credentials from environment variables
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    api_base_url = os.getenv("API_BASE_URL", "https://cryptouniverse.onrender.com")
    
    if not admin_email or not admin_password:
        raise ValueError("Missing required environment variables: ADMIN_EMAIL and ADMIN_PASSWORD must be set")
    
    # Login
    login_data = {"email": admin_email, "password": admin_password}
    login_url = f"{api_base_url.rstrip('/')}/api/v1/auth/login"
    
    try:
        response = requests.post(login_url, json=login_data, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error during login: {e}")
        return
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("✅ Authentication successful")
    
    # Test opportunity discovery
    print("\n🧪 Testing Opportunity Discovery...")
    
    discovery_data = {
        "message": "Find the best opportunities now",
        "user_id": "admin_user_id"
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            "https://cryptouniverse.onrender.com/api/v1/opportunities/discover",
            json=discovery_data,
            headers=headers,
            timeout=60
        )
        
        execution_time = time.time() - start_time
        
        print(f"   Status: {response.status_code} ({execution_time:.1f}s)")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ SUCCESS: {result.get('message', 'Opportunity discovery initiated')}")
            
            # Check scan status
            scan_id = result.get('scan_id')
            if scan_id:
                print(f"   📊 Scan ID: {scan_id}")
                
                # Wait a bit and check status
                time.sleep(5)
                
                status_response = requests.get(
                    f"https://cryptouniverse.onrender.com/api/v1/opportunities/status/{scan_id}",
                    headers=headers,
                    timeout=30
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"   📈 Scan Status: {status_data.get('status', 'unknown')}")
                    print(f"   📊 Progress: {status_data.get('progress', 0)}%")
                    print(f"   🎯 Opportunities Found: {status_data.get('total_opportunities', 0)}")
                    
                    # Get results if available
                    if status_data.get('status') == 'completed':
                        results_response = requests.get(
                            f"https://cryptouniverse.onrender.com/api/v1/opportunities/results/{scan_id}",
                            headers=headers,
                            timeout=30
                        )
                        
                        if results_response.status_code == 200:
                            results_data = results_response.json()
                            opportunities = results_data.get('opportunities', [])
                            print(f"   🎯 Total Opportunities: {len(opportunities)}")
                            
                            # Group by strategy
                            strategy_counts = {}
                            for opp in opportunities:
                                strategy = opp.get('strategy_id', 'unknown')
                                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
                            
                            print(f"   📋 Opportunities by Strategy:")
                            for strategy, count in strategy_counts.items():
                                print(f"      - {strategy}: {count} opportunities")
                else:
                    print(f"   ❌ Status check failed: {status_response.status_code}")
            else:
                print(f"   ⚠️  No scan ID returned")
        else:
            print(f"   ❌ FAILED: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Error Detail: {error_detail}")
            except (ValueError, json.JSONDecodeError) as e:
                print(f"   Raw Response: {response.text[:200]} (JSON decode error: {e})")
                
    except requests.exceptions.Timeout:
        execution_time = time.time() - start_time
        print(f"   ⏰ TIMEOUT ({execution_time:.1f}s)")
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"   💥 EXCEPTION ({execution_time:.1f}s): {str(e)}")

if __name__ == "__main__":
    test_opportunity_discovery()