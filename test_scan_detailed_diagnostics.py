"""
Detailed Diagnostics Test - Investigate scan_id mismatch issue

This script will:
1. Authenticate
2. Initiate a scan
3. Check multiple endpoints with the scan_id
4. Investigate cache key patterns
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

# Authenticate
session = requests.Session()
session.verify = False

print("🔐 Authenticating...")
auth_resp = session.post(
    f"{BASE_URL}/auth/login",
    json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    timeout=15
)

if auth_resp.status_code != 200:
    print(f"❌ Auth failed: {auth_resp.status_code}")
    print(auth_resp.text)
    exit(1)

token = auth_resp.json()["access_token"]
user_id = auth_resp.json()["user_id"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

print(f"✅ Authenticated as {user_id}")

# Initiate scan
print("\n🔍 Initiating scan...")
scan_resp = session.post(
    f"{BASE_URL}/opportunities/discover",
    json={"force_refresh": True},
    headers=headers,
    timeout=15
)

if scan_resp.status_code != 200:
    print(f"❌ Scan initiation failed: {scan_resp.status_code}")
    print(scan_resp.text)
    exit(1)

scan_data = scan_resp.json()
scan_id = scan_data.get("scan_id")
print(f"✅ Scan initiated: {scan_id}")

# Wait a moment
print("\n⏳ Waiting 5 seconds...")
time.sleep(5)

# Check status endpoint
print(f"\n📊 Checking status endpoint...")
status_resp = session.get(
    f"{BASE_URL}/opportunities/status/{scan_id}",
    headers=headers,
    timeout=10
)
print(f"Status response ({status_resp.status_code}):")
print(json.dumps(status_resp.json(), indent=2))

# Check lifecycle endpoint
print(f"\n🔄 Checking lifecycle endpoint...")
lifecycle_resp = session.get(
    f"{BASE_URL}/scan-diagnostics/scan-lifecycle/{scan_id}",
    headers=headers,
    timeout=10
)
if lifecycle_resp.status_code == 200:
    lifecycle_data = lifecycle_resp.json()
    print(f"Lifecycle response:")
    print(f"  Current phase: {lifecycle_data.get('current_phase')}")
    print(f"  Current status: {lifecycle_data.get('current_status')}")
    print(f"  Redis key: {lifecycle_data.get('redis_key')}")
    print(f"  Resolved scan_id: {lifecycle_data.get('resolved_scan_id')}")
else:
    print(f"❌ Lifecycle failed: {lifecycle_resp.status_code}")
    print(lifecycle_resp.text[:500])

# Check debug endpoint
print(f"\n🐛 Checking debug endpoint...")
debug_resp = session.get(
    f"{BASE_URL}/scan-diagnostics/scan-debug/{scan_id}",
    headers=headers,
    timeout=10
)
if debug_resp.status_code == 200:
    debug_data = debug_resp.json()
    print(f"Debug response:")
    print(f"  Overall status: {debug_data.get('overall_status')}")
    print(f"  Current step: {debug_data.get('current_step')}")
    print(f"  Total steps: {debug_data.get('total_steps')}")
else:
    print(f"❌ Debug failed: {debug_resp.status_code}")
    print(debug_resp.text[:500])

# Check user status
print(f"\n👤 Checking user status...")
user_status_resp = session.get(
    f"{BASE_URL}/opportunities/user-status",
    headers=headers,
    timeout=10
)
if user_status_resp.status_code == 200:
    user_status = user_status_resp.json()
    print(f"User status:")
    print(f"  Discovery available: {user_status.get('discovery_available')}")
    print(f"  Onboarded: {user_status.get('onboarding_status', {}).get('onboarded')}")
    print(f"  Active strategies: {user_status.get('onboarding_status', {}).get('active_strategies')}")

# Monitor for a bit longer
print(f"\n⏳ Monitoring scan for 30 seconds...")
for i in range(6):
    time.sleep(5)
    status_resp = session.get(
        f"{BASE_URL}/opportunities/status/{scan_id}",
        headers=headers,
        timeout=10
    )
    if status_resp.status_code == 200:
        status_data = status_resp.json()
        status = status_data.get("status")
        progress = status_data.get("progress", {})
        print(f"  [{i*5+5}s] Status: {status} | Progress: {progress.get('percentage', 0)}%")
        
        if status == "complete":
            print("✅ Scan completed!")
            break
        elif status == "failed":
            print("❌ Scan failed!")
            break

print("\n✅ Diagnostic test complete!")
