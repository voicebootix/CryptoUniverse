#!/usr/bin/env python3
"""
Script to check Render logs for opportunity scan issues.
This script attempts to fetch logs from Render and analyze opportunity scan behavior.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Try to import render API if available
try:
    import renderapi
    RENDER_API_AVAILABLE = True
except ImportError:
    RENDER_API_AVAILABLE = False

def fetch_render_logs_via_api(api_key: str, service_id: Optional[str] = None) -> List[str]:
    """Fetch logs from Render API."""
    if not api_key:
        return []
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    
    logs = []
    
    # Try to get services first
    try:
        services_url = "https://api.render.com/v1/services"
        response = requests.get(services_url, headers=headers, timeout=10)
        if response.status_code == 200:
            services = response.json()
            print(f"Found {len(services)} services")
            for service in services:
                service_id = service.get("id")
                service_name = service.get("name", "unknown")
                print(f"  - {service_name} (ID: {service_id})")
                
                # Try to get logs for this service
                logs_url = f"https://api.render.com/v1/services/{service_id}/logs"
                log_response = requests.get(logs_url, headers=headers, timeout=10)
                if log_response.status_code == 200:
                    service_logs = log_response.json()
                    logs.extend(service_logs.get("logs", []))
        else:
            print(f"Failed to fetch services: {response.status_code}")
    except Exception as e:
        print(f"Error fetching logs via API: {e}")
    
    return logs

def analyze_opportunity_scan_logs(logs: List[str]) -> Dict:
    """Analyze logs for opportunity scan related issues."""
    analysis = {
        "scan_initiations": [],
        "scan_completions": [],
        "lookup_failures": [],
        "cache_key_resolutions": [],
        "redis_errors": [],
        "status_endpoint_calls": [],
        "results_endpoint_calls": [],
        "not_found_responses": [],
        "timeline": []
    }
    
    # Keywords to search for
    scan_keywords = [
        "opportunity_scan",
        "scan_id",
        "_resolve_scan_cache_key",
        "_register_scan_lookup",
        "_update_cached_scan_result",
        "opportunity_scan_lookup",
        "opportunity_scan_result",
        "not_found",
        "Failed to resolve scan cache key",
        "Scan lookup persisted to Redis",
        "Scan cache key resolved",
    ]
    
    for log_line in logs:
        if isinstance(log_line, dict):
            log_text = log_line.get("message", "") or json.dumps(log_line)
        else:
            log_text = str(log_line)
        
        log_lower = log_line.lower() if isinstance(log_line, str) else log_text.lower()
        
        # Check for scan initiation
        if "discover_opportunities" in log_lower or "initiating opportunity scan" in log_lower:
            analysis["scan_initiations"].append(log_text)
            analysis["timeline"].append({
                "time": log_line.get("timestamp", "") if isinstance(log_line, dict) else "",
                "event": "scan_initiation",
                "message": log_text[:200]
            })
        
        # Check for scan completion
        if "scan completed" in log_lower or "opportunities found" in log_lower:
            analysis["scan_completions"].append(log_text)
            analysis["timeline"].append({
                "time": log_line.get("timestamp", "") if isinstance(log_line, dict) else "",
                "event": "scan_completion",
                "message": log_text[:200]
            })
        
        # Check for lookup failures
        if "Failed to resolve scan cache key" in log_text or "all_lookup_methods_failed" in log_text:
            analysis["lookup_failures"].append(log_text)
            analysis["timeline"].append({
                "time": log_line.get("timestamp", "") if isinstance(log_line, dict) else "",
                "event": "lookup_failure",
                "message": log_text[:200]
            })
        
        # Check for cache key resolutions
        if "Scan cache key resolved" in log_text:
            analysis["cache_key_resolutions"].append(log_text)
        
        # Check for Redis errors
        if "redis_error" in log_lower or "redis not available" in log_lower:
            analysis["redis_errors"].append(log_text)
        
        # Check for status endpoint calls
        if "/opportunities/status/" in log_text or "get_scan_status" in log_lower:
            analysis["status_endpoint_calls"].append(log_text)
            if "not_found" in log_lower:
                analysis["not_found_responses"].append(log_text)
        
        # Check for results endpoint calls
        if "/opportunities/results/" in log_text or "get_scan_results" in log_lower:
            analysis["results_endpoint_calls"].append(log_text)
    
    return analysis

def print_analysis(analysis: Dict):
    """Print analysis results."""
    print("\n" + "="*80)
    print("OPPORTUNITY SCAN LOG ANALYSIS")
    print("="*80)
    
    print(f"\n📊 Summary:")
    print(f"  - Scan Initiations: {len(analysis['scan_initiations'])}")
    print(f"  - Scan Completions: {len(analysis['scan_completions'])}")
    print(f"  - Lookup Failures: {len(analysis['lookup_failures'])}")
    print(f"  - Cache Key Resolutions: {len(analysis['cache_key_resolutions'])}")
    print(f"  - Redis Errors: {len(analysis['redis_errors'])}")
    print(f"  - Status Endpoint Calls: {len(analysis['status_endpoint_calls'])}")
    print(f"  - Not Found Responses: {len(analysis['not_found_responses'])}")
    print(f"  - Results Endpoint Calls: {len(analysis['results_endpoint_calls'])}")
    
    if analysis['lookup_failures']:
        print(f"\n❌ Lookup Failures ({len(analysis['lookup_failures'])}):")
        for i, failure in enumerate(analysis['lookup_failures'][:10], 1):
            print(f"  {i}. {failure[:300]}")
    
    if analysis['redis_errors']:
        print(f"\n⚠️  Redis Errors ({len(analysis['redis_errors'])}):")
        for i, error in enumerate(analysis['redis_errors'][:10], 1):
            print(f"  {i}. {error[:300]}")
    
    if analysis['not_found_responses']:
        print(f"\n❌ Not Found Responses ({len(analysis['not_found_responses'])}):")
        for i, response in enumerate(analysis['not_found_responses'][:10], 1):
            print(f"  {i}. {response[:300]}")
    
    if analysis['timeline']:
        print(f"\n📅 Timeline (last 20 events):")
        for event in analysis['timeline'][-20:]:
            print(f"  [{event['time']}] {event['event']}: {event['message'][:100]}")

def main():
    """Main function."""
    print("🔍 Checking Render logs for opportunity scan issues...")
    
    # Try to get Render API key from environment
    render_api_key = os.environ.get("RENDER_API_KEY")
    
    if not render_api_key:
        print("⚠️  RENDER_API_KEY not set. Trying alternative methods...")
        print("\nTo use Render API:")
        print("  1. Get your API key from: https://dashboard.render.com/account/api-keys")
        print("  2. Set RENDER_API_KEY environment variable")
        print("  3. Or pass it as an argument: python check_render_logs_opportunity_scan.py <api_key>")
    
    # Try to fetch logs
    logs = []
    if render_api_key:
        print("\n📥 Fetching logs from Render API...")
        logs = fetch_render_logs_via_api(render_api_key)
        print(f"Fetched {len(logs)} log entries")
    
    if not logs:
        print("\n⚠️  No logs fetched. Alternative methods:")
        print("  1. Use Render CLI: render logs --service <service-name>")
        print("  2. Check Render dashboard: https://dashboard.render.com")
        print("  3. Export logs manually and pipe to this script")
        
        # Try to read from stdin if available
        print("\n📥 Reading from stdin (if available)...")
        try:
            import select
            if select.select([sys.stdin], [], [], 0)[0]:
                logs = sys.stdin.readlines()
                print(f"Read {len(logs)} lines from stdin")
        except:
            pass
    
    if logs:
        print("\n🔬 Analyzing logs...")
        analysis = analyze_opportunity_scan_logs(logs)
        print_analysis(analysis)
        
        # Save analysis to file
        output_file = f"opportunity_scan_log_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"\n💾 Analysis saved to: {output_file}")
    else:
        print("\n❌ No logs available for analysis.")
        print("\n📋 Manual Steps to Check Render Logs:")
        print("  1. Go to https://dashboard.render.com")
        print("  2. Select your service (cryptouniverse)")
        print("  3. Click on 'Logs' tab")
        print("  4. Search for:")
        print("     - 'opportunity_scan'")
        print("     - '_resolve_scan_cache_key'")
        print("     - 'Failed to resolve scan cache key'")
        print("     - 'opportunity_scan_lookup'")
        print("     - 'not_found'")
        print("  5. Look for patterns:")
        print("     - When scans are initiated")
        print("     - When lookup keys are created")
        print("     - When lookups fail")
        print("     - Redis connection issues")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        os.environ["RENDER_API_KEY"] = sys.argv[1]
    main()
