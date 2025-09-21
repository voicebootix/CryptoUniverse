#!/usr/bin/env python3
"""
Targeted test to isolate the greenlet_spawn error
Test each component individually to find the exact source
"""

import asyncio
import requests
import json

BASE_URL = "https://cryptouniverse.onrender.com"

def get_admin_token():
    """Get admin token"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login",
                           json={"email": "admin@cryptouniverse.com",
                                "password": "AdminPass123!"})
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def test_component(endpoint, description):
    """Test a specific component"""
    print(f"\nTesting: {description}")
    print(f"   Endpoint: {endpoint}")

    token = get_admin_token()
    if not token:
        print("   Could not get auth token")
        return

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(f"{BASE_URL}{endpoint}",
                              headers=headers,
                              timeout=30)

        if response.status_code == 200:
            data = response.json()

            # Check for greenlet error
            if 'metadata' in data and 'error' in data['metadata']:
                if 'greenlet_spawn' in str(data['metadata']['error']):
                    print(f"   GREENLET ERROR FOUND: {data['metadata']['error']}")
                    return 'greenlet_error'
                else:
                    print(f"   Other error: {data['metadata']['error']}")
                    return 'other_error'
            elif 'error' in data:
                print(f"   Error in response: {data['error']}")
                return 'error'
            else:
                print(f"   Success: {len(str(data))} chars response")
                return 'success'
        else:
            print(f"   HTTP {response.status_code}: {response.text[:100]}")
            return 'http_error'

    except requests.exceptions.Timeout:
        print("   TIMEOUT (30s+)")
        return 'timeout'
    except Exception as e:
        print(f"   Exception: {str(e)}")
        return 'exception'

def main():
    """Run targeted tests"""
    print("GREENLET SPAWN ERROR ANALYSIS")
    print("=" * 50)

    # Test different endpoints to isolate the issue
    tests = [
        ("/api/v1/unified-strategies/health", "Health Endpoint"),
        ("/api/v1/unified-strategies/portfolio", "Portfolio Endpoint (Full)"),
        ("/api/v1/unified-strategies/portfolio/admin-status", "Admin Status"),
        ("/api/v1/strategies/marketplace", "Marketplace Endpoint"),
    ]

    results = {}

    for endpoint, description in tests:
        result = test_component(endpoint, description)
        results[description] = result

    print(f"\n" + "=" * 50)
    print("ANALYSIS RESULTS")
    print("=" * 50)

    for test, result in results.items():
        icon = "TARGET" if result == 'greenlet_error' else "SUCCESS" if result == 'success' else "FAIL"
        print(f"{icon} {test}: {result}")

    # Find the source
    greenlet_sources = [test for test, result in results.items() if result == 'greenlet_error']
    success_endpoints = [test for test, result in results.items() if result == 'success']

    if greenlet_sources:
        print(f"\nGREENLET ERROR SOURCES:")
        for source in greenlet_sources:
            print(f"   - {source}")

    if success_endpoints:
        print(f"\nWORKING ENDPOINTS:")
        for endpoint in success_endpoints:
            print(f"   - {endpoint}")

if __name__ == "__main__":
    main()