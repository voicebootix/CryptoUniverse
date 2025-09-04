#!/usr/bin/env python3
"""
ENTERPRISE EVIDENCE COLLECTION
Gather real evidence of TestSprite failures from production system
"""

import requests
import time
from datetime import datetime

def collect_production_evidence():
    """Collect hard evidence from production system with enterprise rigor."""
    
    base_url = "https://cryptouniverse.onrender.com"
    evidence = {
        'timestamp': datetime.utcnow().isoformat(),
        'production_url': base_url,
        'test_results': []
    }
    
    print("🏢 COLLECTING ENTERPRISE EVIDENCE FROM PRODUCTION")
    print("=" * 60)
    print(f"Target: {base_url}")
    print(f"Time: {evidence['timestamp']}")
    print()
    
    # Critical endpoints that TestSprite would test
    test_cases = [
        {
            'name': 'Health Check (Should Work)',
            'method': 'GET',
            'url': f"{base_url}/health",
            'expected_status': 200,
            'critical': True
        },
        {
            'name': 'API Status (TestSprite Public Endpoint)',
            'method': 'GET', 
            'url': f"{base_url}/api/v1/status",
            'expected_status': 200,
            'critical': True
        },
        {
            'name': 'Login Endpoint (TestSprite Auth Test)',
            'method': 'POST',
            'url': f"{base_url}/auth/login",
            'body': {"email": "test@cryptouniverse.com", "password": "TestPassword123!"},
            'expected_status': [200, 401, 404],  # Any of these acceptable, 401 auth middleware issue
            'critical': True
        },
        {
            'name': 'Registration Endpoint',
            'method': 'POST',
            'url': f"{base_url}/auth/register", 
            'body': {"email": "new@test.com", "password": "TestPass123!", "full_name": "Test User"},
            'expected_status': [201, 401, 400],
            'critical': True
        },
        {
            'name': 'API Documentation (Should Work)',
            'method': 'GET',
            'url': f"{base_url}/docs",
            'expected_status': 200,
            'critical': False
        }
    ]
    
    # Execute tests with detailed evidence collection
    for test in test_cases:
        print(f"📍 Testing: {test['name']}")
        print(f"   URL: {test['url']}")
        print(f"   Method: {test['method']}")
        
        start_time = time.time()
        result = {
            'test_name': test['name'],
            'url': test['url'],
            'method': test['method'],
            'critical': test['critical'],
            'expected_status': test['expected_status']
        }
        
        try:
            if test['method'] == 'GET':
                response = requests.get(test['url'], timeout=10)
            else:
                response = requests.post(test['url'], json=test.get('body', {}), timeout=10)
            
            response_time = (time.time() - start_time) * 1000
            
            result.update({
                'actual_status': response.status_code,
                'response_time_ms': round(response_time, 1),
                'response_body': response.text[:300],
                'response_headers': dict(response.headers),
                'success': response.status_code in (test['expected_status'] if isinstance(test['expected_status'], list) else [test['expected_status']])
            })
            
            # Detailed analysis
            if response.status_code == 401 and "Missing authorization header" in response.text:
                result['failure_type'] = 'AUTHENTICATION_MIDDLEWARE_BLOCK'
                result['evidence'] = 'Middleware blocking endpoint that should be public'
                print(f"   ❌ CRITICAL FAILURE: {response.status_code} - Middleware blocking public endpoint")
                print(f"   📋 Evidence: {response.text[:100]}")
            elif response.status_code == 500:
                result['failure_type'] = 'SERVER_ERROR'
                result['evidence'] = 'Internal server error - likely database or service issue'
                print(f"   ❌ SERVER ERROR: {response.status_code}")
                print(f"   📋 Evidence: {response.text[:100]}")
            elif result['success']:
                print(f"   ✅ SUCCESS: {response.status_code} ({response_time:.0f}ms)")
            else:
                result['failure_type'] = 'UNEXPECTED_STATUS'
                print(f"   ⚠️  UNEXPECTED: {response.status_code} (expected {test['expected_status']})")
                print(f"   📋 Response: {response.text[:100]}")
            
        except Exception as e:
            result.update({
                'actual_status': 'ERROR',
                'error': str(e),
                'failure_type': 'NETWORK_ERROR',
                'success': False
            })
            print(f"   ❌ NETWORK ERROR: {str(e)}")
        
        evidence['test_results'].append(result)
        print()
    
    return evidence

def analyze_evidence(evidence):
    """Analyze collected evidence with enterprise precision."""
    
    total_tests = len(evidence['test_results'])
    critical_tests = [t for t in evidence['test_results'] if t['critical']]
    successful_tests = [t for t in evidence['test_results'] if t.get('success', False)]
    failed_tests = [t for t in evidence['test_results'] if not t.get('success', False)]
    
    critical_failures = [t for t in critical_tests if not t.get('success', False)]
    
    analysis = {
        'total_tests': total_tests,
        'critical_tests': len(critical_tests),
        'successful_tests': len(successful_tests),
        'failed_tests': len(failed_tests),
        'critical_failures': len(critical_failures),
        'success_rate': (len(successful_tests) / total_tests * 100) if total_tests > 0 else 0,
        'critical_success_rate': (len([t for t in critical_tests if t.get('success', False)]) / len(critical_tests) * 100) if critical_tests else 0
    }
    
    # Categorize failures
    failure_categories = {}
    for test in failed_tests:
        failure_type = test.get('failure_type', 'UNKNOWN')
        if failure_type not in failure_categories:
            failure_categories[failure_type] = []
        failure_categories[failure_type].append(test)
    
    analysis['failure_categories'] = failure_categories
    
    return analysis

def generate_evidence_report(evidence, analysis):
    """Generate evidence-based report for enterprise decision making."""
    
    print("=" * 80)
    print("🏢 ENTERPRISE PRODUCTION EVIDENCE REPORT")
    print("=" * 80)
    
    print(f"\n📊 EXECUTIVE SUMMARY:")
    print(f"   Production URL: {evidence['production_url']}")
    print(f"   Test Timestamp: {evidence['timestamp']}")
    print(f"   Total Tests: {analysis['total_tests']}")
    print(f"   Overall Success Rate: {analysis['success_rate']:.1f}%")
    print(f"   Critical Success Rate: {analysis['critical_success_rate']:.1f}%")
    
    if analysis['critical_success_rate'] < 50:
        print(f"   🚨 VERDICT: CRITICAL SYSTEM FAILURE")
    elif analysis['critical_success_rate'] < 80:
        print(f"   ⚠️  VERDICT: SIGNIFICANT ISSUES REQUIRING URGENT ATTENTION")
    else:
        print(f"   ✅ VERDICT: ACCEPTABLE PERFORMANCE")
    
    print(f"\n🔍 DETAILED EVIDENCE:")
    
    for i, test in enumerate(evidence['test_results'], 1):
        status_icon = "✅" if test.get('success') else "❌"
        critical_marker = "🚨 CRITICAL" if test['critical'] and not test.get('success') else ""
        
        print(f"\n{i}. {status_icon} {test['test_name']} {critical_marker}")
        print(f"   URL: {test['url']}")
        print(f"   Status: {test.get('actual_status')} (expected {test['expected_status']})")
        
        if 'response_time_ms' in test:
            print(f"   Response Time: {test['response_time_ms']}ms")
        
        if test.get('failure_type'):
            print(f"   Failure Type: {test['failure_type']}")
            print(f"   Evidence: {test.get('evidence', 'See response body')}")
        
        if test.get('response_body'):
            print(f"   Response: {test['response_body'][:150]}...")
    
    print(f"\n🚨 CRITICAL FAILURE ANALYSIS:")
    if analysis['failure_categories']:
        for failure_type, tests in analysis['failure_categories'].items():
            print(f"   {failure_type}: {len(tests)} failures")
            for test in tests:
                if test['critical']:
                    print(f"      - {test['test_name']} ({test['url']})")
    else:
        print("   ✅ No critical failures identified")
    
    print(f"\n🎯 ENTERPRISE RECOMMENDATIONS:")
    if analysis['critical_failures'] > 0:
        print("   1. IMMEDIATE deployment of authentication middleware fixes required")
        print("   2. Emergency system verification before production use")
        print("   3. Implement automated monitoring to prevent similar failures")
        print("   4. Review deployment and testing procedures")
    else:
        print("   1. Monitor system performance")
        print("   2. Consider implementing additional automated testing")

def main():
    """Execute enterprise evidence collection and analysis."""
    
    try:
        # Collect evidence
        evidence = collect_production_evidence()
        
        # Analyze evidence
        analysis = analyze_evidence(evidence)
        
        # Generate report
        generate_evidence_report(evidence, analysis)
        
        return evidence, analysis
        
    except Exception as e:
        print(f"❌ Evidence collection failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    evidence, analysis = main()
