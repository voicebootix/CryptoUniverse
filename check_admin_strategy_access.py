#!/usr/bin/env python3
"""
Check Admin Strategy Access
"""

import requests
import json
import os

def check_admin_strategy_access():
    """Check what strategies the admin user actually has access to."""
    print("🔍 CHECKING ADMIN STRATEGY ACCESS")
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
    
    try:
        response_data = response.json()
        if not response_data or 'access_token' not in response_data or not response_data['access_token']:
            print(f"❌ Invalid login response: missing or empty access_token")
            return
        token = response_data['access_token']
    except (ValueError, json.JSONDecodeError) as e:
        print(f"❌ Failed to parse login response: {e}")
        return
    
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("✅ Authentication successful")
    
    # Get admin's portfolio/strategies
    print("\n📊 Checking Admin Portfolio...")
    
    try:
        portfolio_url = f"{api_base_url.rstrip('/')}/api/v1/unified-strategies/portfolio"
        portfolio_response = requests.get(
            portfolio_url,
            headers=headers,
            timeout=60
        )
        
        if portfolio_response.status_code == 200:
            portfolio_data = portfolio_response.json()
            active_strategies = portfolio_data.get('active_strategies', [])
            
            print(f"   ✅ Portfolio loaded successfully")
            print(f"   📊 Active Strategies: {len(active_strategies)}")
            
            if active_strategies:
                print(f"   📋 Strategy Details:")
                for i, strategy in enumerate(active_strategies[:10]):  # Show first 10
                    strategy_id = strategy.get('strategy_id', 'unknown')
                    strategy_name = strategy.get('name', 'unknown')
                    print(f"      {i+1}. {strategy_id}: {strategy_name}")
                
                if len(active_strategies) > 10:
                    print(f"      ... and {len(active_strategies) - 10} more")
            else:
                print(f"   ❌ No active strategies found!")
                
                # Check if there are any strategies at all
                all_strategies = portfolio_data.get('all_strategies', [])
                print(f"   📊 All Strategies Available: {len(all_strategies)}")
                
                if all_strategies:
                    print(f"   📋 Available Strategies:")
                    for i, strategy in enumerate(all_strategies[:10]):
                        strategy_id = strategy.get('strategy_id', 'unknown')
                        strategy_name = strategy.get('name', 'unknown')
                        print(f"      {i+1}. {strategy_id}: {strategy_name}")
        else:
            print(f"   ❌ Portfolio fetch failed: {portfolio_response.status_code}")
            print(f"   Error: {portfolio_response.text[:200]}")
            
    except requests.exceptions.RequestException as e:
        print(f"   💥 Network error: {str(e)}")
    except (ValueError, json.JSONDecodeError) as e:
        print(f"   💥 JSON parsing error: {str(e)}")
    except (KeyError, ValueError) as e:
        print(f"   💥 Data access error: {str(e)}")
    except Exception as e:
        print(f"   💥 Unexpected error: {str(e)}")
        raise
    
    # Check admin strategy access endpoint
    print("\n🔑 Checking Admin Strategy Access...")
    
    try:
        access_url = f"{api_base_url.rstrip('/')}/api/v1/admin-strategy-access/admin-portfolio-status"
        access_response = requests.get(
            access_url,
            headers=headers,
            timeout=30
        )
        
        if access_response.status_code == 200:
            access_data = access_response.json()
            print(f"   ✅ Admin access endpoint working")
            print(f"   📊 Access Data: {json.dumps(access_data, indent=2)}")
        else:
            print(f"   ❌ Admin access failed: {access_response.status_code}")
            print(f"   Error: {access_response.text[:200]}")
            
    except requests.exceptions.RequestException as e:
        print(f"   💥 Network error: {str(e)}")
    except (ValueError, json.JSONDecodeError) as e:
        print(f"   💥 JSON parsing error: {str(e)}")
    except (KeyError, ValueError) as e:
        print(f"   💥 Data access error: {str(e)}")
    except Exception as e:
        print(f"   💥 Unexpected error: {str(e)}")
        raise

if __name__ == "__main__":
    check_admin_strategy_access()