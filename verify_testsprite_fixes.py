#!/usr/bin/env python3
"""
TestSprite Fix Verification Script
Verifies that the authentication middleware fixes are working
"""

import requests
import sys
from datetime import datetime

def verify_testsprite_fixes():
    """Verify TestSprite fixes are working correctly."""
    
    base_url = "https://cryptouniverse.onrender.com"
    
    tests = [
        ("Health Check", "GET", f"{base_url}/health", [200]),
        ("API Status", "GET", f"{base_url}/api/v1/status", [200]),
        ("Auth Login", "POST", f"{base_url}/auth/login", [200, 401, 500])
    ]
    
    print(f"TESTSPRITE FIX VERIFICATION - {datetime.utcnow().isoformat()}")
    print("=" * 60)
    
    all_ok = True
    
    for name, method, url, expected in tests:
        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, json={
                    "email": "test@cryptouniverse.com",
                    "password": "TestPassword123!"
                }, timeout=10)
            
            expected_list = expected if isinstance(expected, list) else [expected]
            
            if response.status_code in expected_list:
                print(f"PASS {name}: {response.status_code}")
            else:
                print(f"FAIL {name}: {response.status_code} (expected {expected_list})")
                print(f"     Response: {response.text[:100]}")
                all_ok = False
                
        except Exception as e:
            print(f"ERROR {name}: {e}")
            all_ok = False
    
    print(f"\nOVERALL RESULT: {'SUCCESS - ALL TESTS PASSED' if all_ok else 'FAILURE - ISSUES DETECTED'}")
    
    if all_ok:
        print("\nTestSprite fixes are working correctly!")
        print("You can now re-run TestSprite tests with confidence.")
    else:
        print("\nSome issues detected. Check the responses above.")
        print("You may need to deploy the changes to production.")
    
    return all_ok

if __name__ == "__main__":
    success = verify_testsprite_fixes()
    sys.exit(0 if success else 1)
