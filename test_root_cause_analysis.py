"""
Root Cause Analysis - Test to verify the actual problem

This test will:
1. Initiate a scan
2. Immediately check what's in the lookup vs cache
3. Trace the exact timing of when cache entries appear
"""

import requests
import json
import time
import asyncio
from datetime import datetime

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()
session.verify = False

print("="*80)
print("ROOT CAUSE ANALYSIS - Testing Cache Entry Creation Timing")
print("="*80)

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

# Initiate scan
print("\n2. INITIATING SCAN...")
init_time = time.time()
scan_resp = session.post(
    f"{BASE_URL}/opportunities/discover",
    json={"force_refresh": True},
    headers=headers,
    timeout=15
)
init_duration = time.time() - init_time
print(f"   Initiation took: {init_duration:.3f}s")

if scan_resp.status_code != 200:
    print(f"❌ Failed: {scan_resp.status_code}")
    print(scan_resp.text[:500])
    exit(1)

scan_data = scan_resp.json()
scan_id = scan_data.get("scan_id")
print(f"✅ Scan ID: {scan_id}")

# Immediately check status (should fail if cache entry doesn't exist yet)
print("\n3. IMMEDIATE STATUS CHECK (within 0.1s of initiation)...")
time.sleep(0.1)  # Wait just 100ms
status_resp = session.get(
    f"{BASE_URL}/opportunities/status/{scan_id}",
    headers=headers,
    timeout=10
)
if status_resp.status_code == 200:
    status_data = status_resp.json()
    print(f"   Status: {status_data.get('status')}")
    print(f"   Success: {status_data.get('success')}")
    if status_data.get('status') == 'not_found':
        print(f"   ❌ PROBLEM CONFIRMED: Status returns 'not_found' immediately after initiation")

# Check lifecycle (this should work because it uses Redis, not in-memory cache)
print("\n4. CHECKING LIFECYCLE (should work even if cache doesn't)...")
lifecycle_resp = session.get(
    f"{BASE_URL}/scan-diagnostics/scan-lifecycle/{scan_id}",
    headers=headers,
    timeout=10
)
if lifecycle_resp.status_code == 200:
    lifecycle = lifecycle_resp.json()
    print(f"   ✅ Lifecycle found scan!")
    print(f"   Current phase: {lifecycle.get('current_phase')}")
    print(f"   Current status: {lifecycle.get('current_status')}")
    print(f"   Redis key: {lifecycle.get('redis_key')}")
else:
    print(f"   ⚠️ Lifecycle failed: {lifecycle_resp.status_code}")

# Monitor status checks over time
print("\n5. MONITORING STATUS CHECKS OVER TIME...")
print("   (Checking every 0.5s to see when cache entry appears)")
for i in range(20):  # 10 seconds total
    elapsed = i * 0.5
    status_resp = session.get(
        f"{BASE_URL}/opportunities/status/{scan_id}",
        headers=headers,
        timeout=10
    )
    if status_resp.status_code == 200:
        status_data = status_resp.json()
        status = status_data.get('status')
        if status != 'not_found':
            print(f"   [{elapsed:.1f}s] ✅ Status changed to: {status}")
            if status == 'scanning':
                progress = status_data.get('progress', {})
                print(f"      Progress: {progress.get('percentage', 0)}%")
            break
        elif i % 2 == 0:  # Print every second
            print(f"   [{elapsed:.1f}s] Status: {status}")
    time.sleep(0.5)

# Final status check
print("\n6. FINAL STATUS CHECK...")
status_resp = session.get(
    f"{BASE_URL}/opportunities/status/{scan_id}",
    headers=headers,
    timeout=10
)
if status_resp.status_code == 200:
    status_data = status_resp.json()
    print(f"   Final status: {status_data.get('status')}")
    print(f"   Success: {status_data.get('success')}")
    
    if status_data.get('status') == 'scanning':
        progress = status_data.get('progress', {})
        print(f"   Progress: {progress.get('percentage', 0)}%")
        print(f"   Strategies: {progress.get('strategies_completed', 0)}/{progress.get('total_strategies', 0)}")

print("\n" + "="*80)
print("ROOT CAUSE ANALYSIS COMPLETE")
print("="*80)
print("\n🔍 EVIDENCE:")
print("   If status returns 'not_found' immediately but lifecycle works,")
print("   then the problem is: Cache entry not created synchronously")
print("   - Lookup registration: ✅ Synchronous (line 229)")
print("   - Cache entry creation: ❌ Asynchronous (line 867 in background task)")
print("   - Status endpoint needs cache entry: ✅ (line 225)")
print("   - Result: Status fails until background task creates cache entry")
