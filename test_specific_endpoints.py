#!/usr/bin/env python3
"""
Test specific endpoints that TestSprite would have tested
Based on the TestSprite API list configuration
"""

import requests
import json

def test_specific_testsprite_endpoints():
    """Test the exact endpoints TestSprite would have tested."""
    
    base_url = "https://cryptouniverse.onrender.com"
    
    print("🔍 TESTING TESTSPRITE-SPECIFIC ENDPOINTS")
    print("=" * 50)
    
    failed_tests = []
    passed_tests = []
    
    # Test 1: System Health (Should be public)
    print("\n1. Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ /health - PASSED")
            passed_tests.append("/health")
        else:
            print(f"❌ /health - FAILED ({response.status_code})")
            failed_tests.append(f"/health - {response.status_code}")
    except Exception as e:
        print(f"❌ /health - ERROR: {e}")
        failed_tests.append(f"/health - ERROR")
    
    # Test 2: API Status (Should be public according to TestSprite config)
    print("\n2. Testing API Status...")
    try:
        response = requests.get(f"{base_url}/api/v1/status", timeout=10)
        if response.status_code == 200:
            print("✅ /api/v1/status - PASSED")
            passed_tests.append("/api/v1/status")
        else:
            print(f"❌ /api/v1/status - FAILED ({response.status_code})")
            print(f"   Response: {response.text[:100]}")
            failed_tests.append(f"/api/v1/status - {response.status_code}")
    except Exception as e:
        print(f"❌ /api/v1/status - ERROR: {e}")
        failed_tests.append(f"/api/v1/status - ERROR")
    
    # Test 3: Login Endpoint (POST)
    print("\n3. Testing Login...")
    try:
        login_data = {
            "email": "test@cryptouniverse.com",
            "password": "TestPassword123!"
        }
        response = requests.post(f"{base_url}/api/v1/auth/login", json=login_data, timeout=10)
        if response.status_code == 200:
            print("✅ /api/v1/auth/login - PASSED")
            passed_tests.append("/api/v1/auth/login")
            # Extract token for authenticated tests
            token_data = response.json()
            access_token = token_data.get("access_token")
            if access_token:
                return run_authenticated_tests(base_url, access_token, failed_tests, passed_tests)
        else:
            print(f"❌ /api/v1/auth/login - FAILED ({response.status_code})")
            print(f"   Response: {response.text[:200]}")
            failed_tests.append(f"/api/v1/auth/login - {response.status_code}")
    except Exception as e:
        print(f"❌ /api/v1/auth/login - ERROR: {e}")
        failed_tests.append(f"/api/v1/auth/login - ERROR")
    
    return summarize_results(failed_tests, passed_tests)

def run_authenticated_tests(base_url, token, failed_tests, passed_tests):
    """Run tests that require authentication."""
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test authenticated endpoints from TestSprite config
    endpoints_to_test = [
        ("/api/v1/auth/me", "GET"),
        ("/api/v1/trading/portfolio", "GET"),
        ("/api/v1/trading/status", "GET"),
        ("/api/v1/market/realtime-prices", "GET"),
        ("/api/v1/exchanges/supported", "GET"),
        ("/api/v1/strategies/available", "GET"),
        ("/api/v1/credits/balance", "GET"),
    ]
    
    print(f"\n4. Testing Authenticated Endpoints with Token...")
    
    for endpoint, method in endpoints_to_test:
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            else:
                response = requests.post(f"{base_url}{endpoint}", headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                print(f"✅ {endpoint} - PASSED ({response.status_code})")
                passed_tests.append(endpoint)
            else:
                print(f"❌ {endpoint} - FAILED ({response.status_code})")
                print(f"   Response: {response.text[:100]}")
                failed_tests.append(f"{endpoint} - {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - ERROR: {e}")
            failed_tests.append(f"{endpoint} - ERROR")
    
    return summarize_results(failed_tests, passed_tests)

def summarize_results(failed_tests, passed_tests):
    """Summarize test results."""
    
    print("\n" + "=" * 50)
    print("📊 TESTSPRITE ENDPOINT ANALYSIS RESULTS")
    print("=" * 50)
    
    total_tests = len(failed_tests) + len(passed_tests)
    
    print(f"\n✅ PASSED: {len(passed_tests)}/{total_tests}")
    for test in passed_tests:
        print(f"   ✅ {test}")
    
    print(f"\n❌ FAILED: {len(failed_tests)}/{total_tests}")
    for test in failed_tests:
        print(f"   ❌ {test}")
    
    if failed_tests:
        print(f"\n🚨 CRITICAL ISSUES FOUND:")
        print("These are the actual issues TestSprite identified:")
        for i, issue in enumerate(failed_tests, 1):
            print(f"{i}. {issue}")
    
    return {
        "passed": passed_tests,
        "failed": failed_tests,
        "total": total_tests,
        "success_rate": len(passed_tests) / total_tests * 100 if total_tests > 0 else 0
    }

if __name__ == "__main__":
    results = test_specific_testsprite_endpoints()
    print(f"\n🎯 SUCCESS RATE: {results['success_rate']:.1f}%")
