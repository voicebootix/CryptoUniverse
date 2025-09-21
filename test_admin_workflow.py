#!/usr/bin/env python3
"""
Test admin strategy access workflow to determine if greenlet error
is root cause or side effect
"""

import requests
import json

BASE_URL = 'https://cryptouniverse.onrender.com'

def test_admin_workflow():
    """Test the complete admin strategy access workflow"""

    # Get admin token
    response = requests.post(f'{BASE_URL}/api/v1/auth/login',
                            json={'email': 'admin@cryptouniverse.com',
                                  'password': 'AdminPass123!'})
    if response.status_code != 200:
        print("Failed to get admin token")
        return

    token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'}

    print('TESTING ADMIN STRATEGY ACCESS WORKFLOW')
    print('=' * 50)

    # Test 1: Check current admin portfolio
    print('\n1. Current Admin Portfolio:')
    response = requests.get(f'{BASE_URL}/api/v1/unified-strategies/portfolio', headers=headers)
    data = response.json()
    print(f'   Status: {response.status_code}')
    print(f'   Strategies Count: {len(data.get("strategies", []))}')
    print(f'   User ID: {data.get("user_id", "N/A")}')
    if 'error' in data:
        print(f'   ERROR: {data["error"]}')

    # Test 2: Check admin status
    print('\n2. Admin Status Check:')
    response = requests.get(f'{BASE_URL}/api/v1/unified-strategies/portfolio/admin-status', headers=headers)
    status_data = response.json()
    print(f'   Status: {response.status_code}')
    print(f'   Strategies Available: {status_data.get("strategies_available", 0)}')
    print(f'   Access Records: {status_data.get("access_records_count", 0)}')

    # Test 3: Try bulk grant to admin themselves
    print('\n3. Bulk Grant Admin Access:')
    response = requests.post(f'{BASE_URL}/api/v1/unified-strategies/access/bulk-grant',
                            json={'strategy_filter': 'all', 'grant_reason': 'admin_self_grant'},
                            headers=headers)
    grant_data = response.json()
    print(f'   Status: {response.status_code}')
    print(f'   Success: {grant_data.get("success", False)}')
    print(f'   Strategies Granted: {grant_data.get("total_granted", 0)}')
    if 'message' in grant_data:
        print(f'   Message: {grant_data["message"]}')

    # Test 4: Check portfolio again after grant
    print('\n4. Portfolio After Grant:')
    response = requests.get(f'{BASE_URL}/api/v1/unified-strategies/portfolio', headers=headers)
    final_data = response.json()
    print(f'   Status: {response.status_code}')
    print(f'   Strategies Count: {len(final_data.get("strategies", []))}')
    if final_data.get('strategies'):
        print(f'   First Strategy: {final_data["strategies"][0].get("name", "Unnamed")}')
        print(f'   Strategy IDs: {[s.get("strategy_id") for s in final_data["strategies"][:3]]}')

    print('\n' + '=' * 50)
    print('ANALYSIS:')

    initial_count = len(data.get("strategies", []))
    final_count = len(final_data.get("strategies", []))

    if initial_count == 0 and final_count > 0:
        print('ROOT CAUSE: Admin needed to grant themselves access first')
        print('GREENLET ERROR: Side effect from performance tracking')
    elif initial_count == final_count == 0:
        print('DEEPER ISSUE: No strategies exist or access grant failed')
    else:
        print('GREENLET ERROR: Likely the main issue preventing strategy display')

if __name__ == "__main__":
    test_admin_workflow()