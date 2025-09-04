#!/usr/bin/env python3
"""
Enterprise-grade TestSprite Result Extraction
Extract REAL test results from the TestSprite PDF with proper evidence
"""

import re
import sys
from typing import Dict, List, Tuple, Optional

def extract_testsprite_text_data(pdf_path: str = "TestSprite.pdf") -> str:
    """Extract text from TestSprite PDF using multiple methods."""
    
    try:
        # Try pdfplumber first (best for structured data)
        import pdfplumber
        text_content = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages[:10]):  # First 10 pages for efficiency
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(f"--- PAGE {page_num + 1} ---\n{page_text}\n")
                except Exception as e:
                    print(f"Error extracting page {page_num + 1}: {e}")
        
        return "\n".join(text_content)
        
    except ImportError:
        try:
            # Fallback to PyPDF2
            import PyPDF2
            text_content = []
            
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(reader.pages[:10]):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(f"--- PAGE {page_num + 1} ---\n{page_text}\n")
                    except Exception as e:
                        print(f"Error extracting page {page_num + 1}: {e}")
            
            return "\n".join(text_content)
            
        except ImportError:
            print("❌ No PDF libraries available. Installing pdfplumber...")
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pdfplumber'])
            
            # Retry after installation
            import pdfplumber
            text_content = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages[:10]):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(f"--- PAGE {page_num + 1} ---\n{page_text}\n")
                    except Exception as e:
                        print(f"Error extracting page {page_num + 1}: {e}")
            
            return "\n".join(text_content)

def parse_test_results(text_content: str) -> Dict:
    """Parse actual test results from TestSprite text with enterprise precision."""
    
    results = {
        'executive_summary': None,
        'total_tests': 0,
        'passed_tests': 0,
        'failed_tests': 0,
        'success_rate': 0.0,
        'failed_endpoints': [],
        'passed_endpoints': [],
        'critical_issues': [],
        'performance_metrics': {},
        'error_patterns': {}
    }
    
    # Extract executive summary
    exec_summary_pattern = r'(?i)executive\s+summary.*?(?=\n[A-Z]|\n\n|\Z)'
    exec_match = re.search(exec_summary_pattern, text_content, re.DOTALL)
    if exec_match:
        results['executive_summary'] = exec_match.group(0).strip()
    
    # Extract test counts with multiple patterns
    test_patterns = [
        r'(?i)total\s+tests?:?\s*(\d+)',
        r'(?i)(\d+)\s+total\s+tests?',
        r'(?i)executed\s+(\d+)\s+tests?',
        r'(?i)tests?\s+executed:?\s*(\d+)'
    ]
    
    for pattern in test_patterns:
        match = re.search(pattern, text_content)
        if match:
            results['total_tests'] = int(match.group(1))
            break
    
    # Extract passed/failed counts
    passed_patterns = [
        r'(?i)passed:?\s*(\d+)',
        r'(?i)(\d+)\s+passed',
        r'(?i)successful:?\s*(\d+)',
        r'(?i)(\d+)\s+successful'
    ]
    
    failed_patterns = [
        r'(?i)failed:?\s*(\d+)', 
        r'(?i)(\d+)\s+failed',
        r'(?i)errors?:?\s*(\d+)',
        r'(?i)(\d+)\s+errors?'
    ]
    
    for pattern in passed_patterns:
        match = re.search(pattern, text_content)
        if match:
            results['passed_tests'] = int(match.group(1))
            break
    
    for pattern in failed_patterns:
        match = re.search(pattern, text_content)
        if match:
            results['failed_tests'] = int(match.group(1))
            break
    
    # Calculate success rate
    if results['total_tests'] > 0:
        results['success_rate'] = (results['passed_tests'] / results['total_tests']) * 100
    
    # Extract specific endpoint failures
    endpoint_failure_patterns = [
        r'(?i)((?:/api/v1/|/)[a-zA-Z0-9/_-]+)\s*(?:failed|error|401|404|500)',
        r'(?i)failed.*?((?:/api/v1/|/)[a-zA-Z0-9/_-]+)',
        r'(?i)error.*?((?:/api/v1/|/)[a-zA-Z0-9/_-]+)',
        r'(?i)((?:/api/v1/|/)[a-zA-Z0-9/_-]+)\s*(?:returned|status|code)\s*(?:401|404|500)'
    ]
    
    failed_endpoints = set()
    for pattern in endpoint_failure_patterns:
        matches = re.findall(pattern, text_content)
        failed_endpoints.update(matches)
    
    results['failed_endpoints'] = list(failed_endpoints)
    
    # Extract critical issues
    critical_patterns = [
        r'(?i)critical:?\s*(.+?)(?=\n|$)',
        r'(?i)severe:?\s*(.+?)(?=\n|$)',
        r'(?i)blocker:?\s*(.+?)(?=\n|$)',
        r'(?i)authentication.+?fail',
        r'(?i)login.+?fail',
        r'(?i)token.+?invalid'
    ]
    
    critical_issues = set()
    for pattern in critical_patterns:
        matches = re.findall(pattern, text_content)
        critical_issues.update(matches)
    
    results['critical_issues'] = list(critical_issues)
    
    return results

def verify_against_production_system(results: Dict) -> Dict:
    """Verify TestSprite results against actual production system."""
    
    import requests
    
    verification = {
        'production_health': None,
        'auth_endpoint_status': None,
        'api_status_status': None,
        'confirmed_failures': [],
        'false_positives': []
    }
    
    base_url = "https://cryptouniverse.onrender.com"
    
    print("🔍 ENTERPRISE VERIFICATION: Testing Production System")
    print("=" * 60)
    
    # Test 1: Health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        verification['production_health'] = {
            'status_code': response.status_code,
            'response_time_ms': response.elapsed.total_seconds() * 1000,
            'content': response.text[:200]
        }
        print(f"✅ Health Check: {response.status_code} ({response.elapsed.total_seconds()*1000:.0f}ms)")
    except Exception as e:
        verification['production_health'] = {'error': str(e)}
        print(f"❌ Health Check: ERROR - {e}")
    
    # Test 2: Auth endpoints (should be accessible)
    auth_endpoints = ["/api/v1/auth/login", "/auth/login"]
    
    for endpoint in auth_endpoints:
        try:
            test_data = {"email": "test@example.com", "password": "testpass"}
            response = requests.post(f"{base_url}{endpoint}", json=test_data, timeout=10)
            
            status = {
                'endpoint': endpoint,
                'status_code': response.status_code,
                'response_time_ms': response.elapsed.total_seconds() * 1000,
                'content': response.text[:200]
            }
            
            if endpoint not in verification['auth_endpoint_status']:
                verification['auth_endpoint_status'] = []
            verification['auth_endpoint_status'].append(status)
            
            if response.status_code == 401 and "Missing authorization header" in response.text:
                verification['confirmed_failures'].append({
                    'endpoint': endpoint,
                    'issue': 'Authentication middleware blocking auth endpoint',
                    'evidence': response.text[:100]
                })
                print(f"❌ {endpoint}: CONFIRMED FAILURE - Middleware blocking auth endpoint")
            else:
                print(f"✅ {endpoint}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {endpoint}: ERROR - {e}")
    
    # Test 3: API Status endpoint
    try:
        response = requests.get(f"{base_url}/api/v1/status", timeout=10)
        verification['api_status_status'] = {
            'status_code': response.status_code,
            'response_time_ms': response.elapsed.total_seconds() * 1000,
            'content': response.text[:200]
        }
        
        if response.status_code == 401:
            verification['confirmed_failures'].append({
                'endpoint': '/api/v1/status',
                'issue': 'Status endpoint incorrectly requiring authentication',
                'evidence': response.text[:100]
            })
            print(f"❌ API Status: CONFIRMED FAILURE - Should be public but returns 401")
        else:
            print(f"✅ API Status: {response.status_code}")
            
    except Exception as e:
        verification['api_status_status'] = {'error': str(e)}
        print(f"❌ API Status: ERROR - {e}")
    
    return verification

def generate_enterprise_report(results: Dict, verification: Dict) -> str:
    """Generate enterprise-grade analysis report."""
    
    report = []
    report.append("=" * 80)
    report.append("🏢 ENTERPRISE TESTSPRITE ANALYSIS REPORT")
    report.append("=" * 80)
    
    # Executive Summary
    if results.get('executive_summary'):
        report.append(f"\n📊 EXECUTIVE SUMMARY:")
        report.append(results['executive_summary'])
    
    # Key Metrics
    report.append(f"\n📈 KEY METRICS:")
    report.append(f"   Total Tests: {results['total_tests']}")
    report.append(f"   Passed: {results['passed_tests']}")
    report.append(f"   Failed: {results['failed_tests']}")
    report.append(f"   Success Rate: {results['success_rate']:.1f}%")
    
    # Production Verification
    report.append(f"\n🔍 PRODUCTION VERIFICATION:")
    
    if verification['production_health']:
        health = verification['production_health']
        if 'error' in health:
            report.append(f"   ❌ Health: ERROR - {health['error']}")
        else:
            report.append(f"   ✅ Health: {health['status_code']} ({health['response_time_ms']:.0f}ms)")
    
    # Confirmed Failures
    if verification['confirmed_failures']:
        report.append(f"\n🚨 CONFIRMED PRODUCTION FAILURES:")
        for i, failure in enumerate(verification['confirmed_failures'], 1):
            report.append(f"   {i}. {failure['endpoint']}")
            report.append(f"      Issue: {failure['issue']}")
            report.append(f"      Evidence: {failure['evidence']}")
    
    # Failed Endpoints
    if results['failed_endpoints']:
        report.append(f"\n❌ FAILED ENDPOINTS:")
        for i, endpoint in enumerate(results['failed_endpoints'], 1):
            report.append(f"   {i}. {endpoint}")
    
    # Critical Issues
    if results['critical_issues']:
        report.append(f"\n🔴 CRITICAL ISSUES:")
        for i, issue in enumerate(results['critical_issues'], 1):
            report.append(f"   {i}. {issue}")
    
    # Enterprise Recommendations
    report.append(f"\n🎯 ENTERPRISE RECOMMENDATIONS:")
    
    if results['success_rate'] < 50:
        report.append("   🚨 IMMEDIATE ACTION REQUIRED - System has critical failures")
        report.append("   📋 Recommended Actions:")
        report.append("      1. Fix authentication middleware configuration")
        report.append("      2. Deploy fixes to production immediately")
        report.append("      3. Run comprehensive regression testing")
        report.append("      4. Implement monitoring for similar issues")
    elif results['success_rate'] < 80:
        report.append("   ⚠️  SIGNIFICANT ISSUES - Requires urgent attention")
    else:
        report.append("   ✅ ACCEPTABLE - Minor issues to address")
    
    return "\n".join(report)

def main():
    """Main execution with enterprise-grade rigor."""
    
    print("🏢 ENTERPRISE TESTSPRITE ANALYSIS")
    print("Extracting real evidence from TestSprite results...")
    print()
    
    try:
        # Extract PDF content
        print("📄 Extracting TestSprite PDF content...")
        text_content = extract_testsprite_text_data()
        
        if not text_content or len(text_content) < 100:
            print("⚠️  Limited text extracted from PDF. Proceeding with production verification...")
            text_content = "Limited PDF extraction available"
        else:
            print(f"✅ Extracted {len(text_content)} characters from TestSprite report")
        
        # Parse results
        print("📊 Parsing test results...")
        results = parse_test_results(text_content)
        
        # Verify against production
        print("🔍 Verifying against production system...")
        verification = verify_against_production_system(results)
        
        # Generate report
        print("📋 Generating enterprise report...")
        report = generate_enterprise_report(results, verification)
        
        print("\n" + report)
        
        # Save report
        with open("ENTERPRISE_TESTSPRITE_ANALYSIS.md", "w") as f:
            f.write(report)
        
        print(f"\n💾 Report saved to: ENTERPRISE_TESTSPRITE_ANALYSIS.md")
        
        return results, verification
        
    except Exception as e:
        print(f"❌ Enterprise analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    results, verification = main()
