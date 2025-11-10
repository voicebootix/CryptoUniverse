"""
Full Cycle Test - Wait for scan completion and verify configuration

This test will:
1. Initiate a scan
2. Monitor it until completion (or timeout)
3. Verify results
4. Check all diagnostic endpoints
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()
session.verify = False

print("="*70)
print("FULL CYCLE OPPORTUNITY SCAN TEST")
print("="*70)

# Authenticate
print("\n1. AUTHENTICATING...")
auth_resp = session.post(
    f"{BASE_URL}/auth/login",
    json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    timeout=15
)
if auth_resp.status_code != 200:
    print(f"❌ Auth failed")
    exit(1)
token = auth_resp.json()["access_token"]
user_id = auth_resp.json()["user_id"]
headers = {"Authorization": f"Bearer {token}"}
print(f"✅ Authenticated as {user_id}")

# Get user status
print("\n2. CHECKING USER STATUS...")
user_status_resp = session.get(f"{BASE_URL}/opportunities/user-status", headers=headers)
if user_status_resp.status_code == 200:
    status_data = user_status_resp.json()
    print(f"   Onboarded: {status_data.get('onboarding_status', {}).get('onboarded')}")
    print(f"   Active strategies: {status_data.get('onboarding_status', {}).get('active_strategies')}")

# Initiate scan
print("\n3. INITIATING SCAN...")
scan_resp = session.post(
    f"{BASE_URL}/opportunities/discover",
    json={"force_refresh": True},
    headers=headers,
    timeout=15
)
if scan_resp.status_code != 200:
    print(f"❌ Failed: {scan_resp.status_code}")
    print(scan_resp.text[:500])
    exit(1)

scan_data = scan_resp.json()
scan_id = scan_data.get("scan_id")
print(f"✅ Scan ID: {scan_id}")
print(f"   Status: {scan_data.get('status')}")
print(f"   Estimated time: {scan_data.get('estimated_completion_seconds')}s")

# Monitor scan
print("\n4. MONITORING SCAN PROGRESS...")
max_wait = 240  # 4 minutes
start_time = time.time()
last_status = None
progress_updates = []

while (time.time() - start_time) < max_wait:
    elapsed = int(time.time() - start_time)
    
    # Check status
    status_resp = session.get(
        f"{BASE_URL}/opportunities/status/{scan_id}",
        headers=headers,
        timeout=10
    )
    
    if status_resp.status_code == 200:
        status_data = status_resp.json()
        current_status = status_data.get("status")
        progress = status_data.get("progress", {})
        
        # Print if status changed
        if current_status != last_status:
            print(f"   [{elapsed}s] Status: {current_status}")
            last_status = current_status
            
            if current_status == "scanning":
                pct = progress.get("percentage", 0)
                strategies_done = progress.get("strategies_completed", 0)
                strategies_total = progress.get("total_strategies", 0)
                opps_found = progress.get("opportunities_found_so_far", 0)
                print(f"      Progress: {pct}% ({strategies_done}/{strategies_total} strategies, {opps_found} opportunities)")
                progress_updates.append({
                    "elapsed": elapsed,
                    "status": current_status,
                    "progress": progress
                })
        
        if current_status == "complete":
            print(f"\n✅ Scan completed in {elapsed}s!")
            print(f"   Total opportunities: {status_data.get('total_opportunities', 0)}")
            break
        elif current_status == "failed":
            print(f"\n❌ Scan failed!")
            print(f"   Message: {status_data.get('message', 'Unknown error')}")
            break
        elif current_status == "not_found":
            # Check lifecycle as fallback
            lifecycle_resp = session.get(
                f"{BASE_URL}/scan-diagnostics/scan-lifecycle/{scan_id}",
                headers=headers,
                timeout=10
            )
            if lifecycle_resp.status_code == 200:
                lifecycle_data = lifecycle_resp.json()
                if lifecycle_data.get("current_status") == "in_progress":
                    print(f"   [{elapsed}s] Status endpoint says 'not_found' but lifecycle shows 'in_progress'")
                    print(f"      Current phase: {lifecycle_data.get('current_phase')}")
                    # Continue monitoring
                    time.sleep(5)
                    continue
    
    time.sleep(5)

# Get results if completed
if last_status == "complete":
    print("\n5. RETRIEVING RESULTS...")
    results_resp = session.get(
        f"{BASE_URL}/opportunities/results/{scan_id}",
        headers=headers,
        timeout=15
    )
    
    if results_resp.status_code == 200:
        results_data = results_resp.json()
        print(f"✅ Results retrieved!")
        print(f"   Total opportunities: {results_data.get('total_opportunities', 0)}")
        print(f"   Execution time: {results_data.get('execution_time_ms', 0):.2f}ms")
        
        opportunities = results_data.get('opportunities', [])
        if opportunities:
            print(f"\n   Sample opportunities:")
            for i, opp in enumerate(opportunities[:5], 1):
                print(f"   {i}. {opp.get('symbol')} - {opp.get('opportunity_type')}")
                print(f"      Strategy: {opp.get('strategy_name')}")
                print(f"      Profit: ${opp.get('profit_potential_usd', 0):.2f}")
                print(f"      Confidence: {opp.get('confidence_score', 0):.2f}")
    else:
        print(f"⚠️ Could not retrieve results: {results_resp.status_code}")

# Diagnostic endpoints
print("\n6. CHECKING DIAGNOSTIC ENDPOINTS...")

# Scan metrics
metrics_resp = session.get(
    f"{BASE_URL}/scan-diagnostics/scan-metrics",
    headers=headers,
    params={"user_id": user_id},
    timeout=10
)
if metrics_resp.status_code == 200:
    metrics = metrics_resp.json()
    print(f"✅ Scan metrics retrieved")
    print(f"   System health: {metrics.get('system_health', {}).get('status')}")

# Scan lifecycle
lifecycle_resp = session.get(
    f"{BASE_URL}/scan-diagnostics/scan-lifecycle/{scan_id}",
    headers=headers,
    timeout=10
)
if lifecycle_resp.status_code == 200:
    lifecycle = lifecycle_resp.json()
    print(f"✅ Scan lifecycle retrieved")
    print(f"   Current phase: {lifecycle.get('current_phase')}")
    print(f"   Current status: {lifecycle.get('current_status')}")
    print(f"   Is stuck: {lifecycle.get('is_stuck')}")

# Scan debug
debug_resp = session.get(
    f"{BASE_URL}/scan-diagnostics/scan-debug/{scan_id}",
    headers=headers,
    timeout=10
)
if debug_resp.status_code == 200:
    debug = debug_resp.json()
    print(f"✅ Scan debug retrieved")
    print(f"   Overall status: {debug.get('overall_status')}")
    print(f"   Current step: {debug.get('current_step')}")
    print(f"   Total steps: {debug.get('total_steps')}")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
