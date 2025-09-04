#!/usr/bin/env python3
"""
Comprehensive TestSprite Failure Analysis
Test ALL endpoints that TestSprite would have tested based on the API configuration
"""

import requests
import json
import time
from typing import Dict, List, Tuple

def load_testsprite_config():
    """Load the TestSprite API configuration."""
    try:
        with open('CryptoUniverse_TestSprite_API_List.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Could not load TestSprite config: {e}")
        return None

def test_all_public_endpoints(config: Dict) -> Tuple[List, List]:
    """Test all public (non-auth required) endpoints."""
    base_url = config['base_url']
    failed_tests = []
    passed_tests = []
    
    print("🔍 TESTING ALL PUBLIC ENDPOINTS")
    print("=" * 60)
    
    for endpoint in config['endpoints']:
        if not endpoint.get('auth_required', True):  # Test public endpoints
            method = endpoint['method']
            path = endpoint['path']
            expected_status = endpoint.get('expected_status', 200)
            
            # Handle path prefix for API endpoints
            if path.startswith('/api/v1/'):
                full_url = f"{base_url}{path[8:]}"  # Remove /api/v1 since base_url includes it
            elif path.startswith('/'):
                full_url = f"https://cryptouniverse.onrender.com{path}"
            else:
                full_url = f"{base_url}/{path}"
            
            print(f"\n📍 Testing: {endpoint['name']}")
            print(f"   URL: {full_url}")
            print(f"   Method: {method}")
            print(f"   Expected: {expected_status}")
            
            try:
                if method.upper() == 'GET':
                    response = requests.get(full_url, timeout=10)
                elif method.upper() == 'POST':
                    # Use test data from endpoint config if available
                    test_data = endpoint.get('body', {})
                    response = requests.post(full_url, json=test_data, timeout=10)
                else:
                    print(f"   ⚠️  Unsupported method: {method}")
                    continue
                
                if response.status_code == expected_status:
                    print(f"   ✅ PASSED ({response.status_code})")
                    passed_tests.append({
                        'name': endpoint['name'],
                        'path': path,
                        'method': method,
                        'status': response.status_code
                    })
                else:
                    print(f"   ❌ FAILED ({response.status_code}, expected {expected_status})")
                    print(f"   Response: {response.text[:150]}")
                    failed_tests.append({
                        'name': endpoint['name'],
                        'path': path,
                        'method': method,
                        'status': response.status_code,
                        'expected': expected_status,
                        'response': response.text[:200]
                    })
                    
            except Exception as e:
                print(f"   ❌ ERROR: {str(e)}")
                failed_tests.append({
                    'name': endpoint['name'],
                    'path': path,
                    'method': method,
                    'status': 'ERROR',
                    'expected': expected_status,
                    'response': str(e)
                })
    
    return passed_tests, failed_tests

def attempt_login_and_test_protected(config: Dict) -> Tuple[List, List, str]:
    """Attempt login and test protected endpoints."""
    base_url = config['base_url']
    auth = config['authentication']
    
    print(f"\n🔐 ATTEMPTING LOGIN FOR PROTECTED ENDPOINT TESTING")
    print("=" * 60)
    
    # Try to login
    login_url = f"{base_url}/auth/login"
    login_data = auth['test_credentials']
    
    access_token = None
    login_failed_tests = []
    login_passed_tests = []
    
    try:
        print(f"🔑 Logging in with: {login_data['email']}")
        response = requests.post(login_url, json=login_data, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            print(f"✅ Login successful - got access token")
            login_passed_tests.append({
                'name': 'Login',
                'path': '/auth/login',
                'method': 'POST',
                'status': 200
            })
        else:
            print(f"❌ Login failed ({response.status_code})")
            print(f"   Response: {response.text[:200]}")
            login_failed_tests.append({
                'name': 'Login',
                'path': '/auth/login', 
                'method': 'POST',
                'status': response.status_code,
                'response': response.text[:200]
            })
            
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        login_failed_tests.append({
            'name': 'Login',
            'path': '/auth/login',
            'method': 'POST', 
            'status': 'ERROR',
            'response': str(e)
        })
    
    # Test protected endpoints if we have a token
    if access_token:
        print(f"\n🛡️  TESTING PROTECTED ENDPOINTS")
        print("=" * 60)
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        protected_endpoints = [
            ("/auth/me", "GET"),
            ("/trading/portfolio", "GET"),
            ("/trading/status", "GET"),
            ("/market/realtime-prices", "GET"),
            ("/exchanges/supported", "GET"),
            ("/strategies/available", "GET"),
            ("/credits/balance", "GET"),
            ("/chat/message", "POST"),
        ]
        
        for path, method in protected_endpoints:
            full_url = f"{base_url}{path}"
            print(f"\n📍 Testing protected: {path}")
            
            try:
                if method == "GET":
                    response = requests.get(full_url, headers=headers, timeout=10)
                else:
                    test_data = {"message": "Hello AI", "session_id": "test123"} if "chat" in path else {}
                    response = requests.post(full_url, headers=headers, json=test_data, timeout=10)
                
                if response.status_code in [200, 201]:
                    print(f"   ✅ PASSED ({response.status_code})")
                    login_passed_tests.append({
                        'name': f'Protected {path}',
                        'path': path,
                        'method': method,
                        'status': response.status_code
                    })
                else:
                    print(f"   ❌ FAILED ({response.status_code})")
                    print(f"   Response: {response.text[:100]}")
                    login_failed_tests.append({
                        'name': f'Protected {path}',
                        'path': path,
                        'method': method,
                        'status': response.status_code,
                        'response': response.text[:200]
                    })
                    
            except Exception as e:
                print(f"   ❌ ERROR: {str(e)}")
                login_failed_tests.append({
                    'name': f'Protected {path}',
                    'path': path,
                    'method': method,
                    'status': 'ERROR',
                    'response': str(e)
                })
    
    return login_passed_tests, login_failed_tests, access_token

def analyze_failure_patterns(all_failed_tests: List[Dict]) -> Dict:
    """Analyze patterns in the failures."""
    patterns = {
        'auth_issues': 0,
        'not_found': 0,
        'server_errors': 0,
        'network_errors': 0,
        'missing_endpoints': 0
    }
    
    for test in all_failed_tests:
        status = test.get('status')
        response = test.get('response', '').lower()
        
        if status == 401 or 'unauthorized' in response or 'missing authorization' in response:
            patterns['auth_issues'] += 1
        elif status == 404 or 'not found' in response:
            patterns['not_found'] += 1
        elif status in [500, 502, 503] or 'server error' in response:
            patterns['server_errors'] += 1
        elif status == 'ERROR':
            patterns['network_errors'] += 1
        elif 'not implemented' in response or 'endpoint' in response:
            patterns['missing_endpoints'] += 1
    
    return patterns

def generate_comprehensive_report(public_passed, public_failed, protected_passed, protected_failed):
    """Generate comprehensive TestSprite failure report."""
    all_passed = public_passed + protected_passed
    all_failed = public_failed + protected_failed
    total_tests = len(all_passed) + len(all_failed)
    
    print(f"\n" + "=" * 80)
    print("📊 COMPREHENSIVE TESTSPRITE FAILURE ANALYSIS")
    print("=" * 80)
    
    success_rate = (len(all_passed) / total_tests * 100) if total_tests > 0 else 0
    print(f"\n🎯 OVERALL TEST RESULTS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {len(all_passed)}")
    print(f"   Failed: {len(all_failed)}")
    print(f"   Success Rate: {success_rate:.1f}%")
    
    if all_failed:
        print(f"\n❌ DETAILED FAILURE BREAKDOWN:")
        patterns = analyze_failure_patterns(all_failed)
        
        print(f"   🔐 Authentication Issues: {patterns['auth_issues']}")
        print(f"   🚫 Not Found (404): {patterns['not_found']}")
        print(f"   💥 Server Errors (5xx): {patterns['server_errors']}")
        print(f"   🌐 Network/Connection Errors: {patterns['network_errors']}")
        print(f"   🏗️  Missing/Unimplemented: {patterns['missing_endpoints']}")
        
        print(f"\n📋 FAILED TEST DETAILS:")
        for i, test in enumerate(all_failed, 1):
            print(f"{i:2d}. {test['name']}")
            print(f"    Path: {test['path']} ({test['method']})")
            print(f"    Status: {test['status']}")
            if test.get('response'):
                print(f"    Error: {test['response'][:100]}...")
            print()
    
    if all_passed:
        print(f"\n✅ PASSED TESTS:")
        for test in all_passed:
            print(f"   ✅ {test['name']} ({test['path']})")
    
    return {
        'total_tests': total_tests,
        'passed': len(all_passed),
        'failed': len(all_failed),
        'success_rate': success_rate,
        'failure_patterns': analyze_failure_patterns(all_failed) if all_failed else {},
        'failed_details': all_failed
    }

def main():
    """Main execution function."""
    print("🧪 COMPREHENSIVE TESTSPRITE FAILURE ANALYSIS")
    print("Testing ALL endpoints that TestSprite would have tested...")
    print()
    
    # Load TestSprite configuration
    config = load_testsprite_config()
    if not config:
        return
    
    print(f"📋 Loaded configuration for: {config['api_name']}")
    print(f"🔗 Base URL: {config['base_url']}")
    print(f"📊 Total endpoints configured: {len(config['endpoints'])}")
    
    # Test all public endpoints
    public_passed, public_failed = test_all_public_endpoints(config)
    
    # Test protected endpoints (requires login)
    protected_passed, protected_failed, token = attempt_login_and_test_protected(config)
    
    # Generate comprehensive report
    results = generate_comprehensive_report(public_passed, public_failed, protected_passed, protected_failed)
    
    print(f"\n🎯 FINAL VERDICT:")
    if results['success_rate'] < 50:
        print("🚨 CRITICAL: Multiple system failures detected")
    elif results['success_rate'] < 80:
        print("⚠️  WARNING: Significant issues found") 
    else:
        print("✅ GOOD: Most tests passing")
        
    return results

if __name__ == "__main__":
    results = main()
