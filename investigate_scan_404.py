#!/usr/bin/env python3
"""
Investigate scan results 404 errors by:
1. Checking if scans are completing successfully
2. Verifying Redis keys exist
3. Checking if scans are timing out before saving results
"""

import requests
import time
import json
from typing import Dict, Any, Optional

BASE_URL = "https://cryptouniverse.onrender.com"
EMAIL = "admin@cryptouniverse.com"
PASSWORD = "AdminPass123!"

class ScanInvestigator:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.access_token = None
        self.user_id = None
        
    def authenticate(self) -> bool:
        """Authenticate and get access token."""
        print("🔐 Authenticating...")
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": EMAIL, "password": PASSWORD},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            self.access_token = data.get("access_token")
            self.user_id = data.get("user_id")
            
            if self.access_token:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })
                print(f"✅ Authenticated successfully (user_id: {self.user_id})")
                return True
            else:
                print("❌ No access token in response")
                return False
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get request headers with auth token."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def initiate_scan(self) -> Optional[str]:
        """Initiate a new opportunity scan."""
        print("\n🚀 Initiating new opportunity scan...")
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/opportunities/discover",
                json={
                    "force_refresh": True,
                    "include_strategy_recommendations": True
                },
                headers=self.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            scan_id = data.get("scan_id")
            status = data.get("status")
            print(f"✅ Scan initiated: scan_id={scan_id}, status={status}")
            print(f"   Poll URL: {data.get('poll_url')}")
            print(f"   Results URL: {data.get('results_url')}")
            return scan_id
        except Exception as e:
            print(f"❌ Failed to initiate scan: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
            return None
    
    def check_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """Check scan status."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/opportunities/status/{scan_id}",
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Failed to check status: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
            return {}
    
    def get_scan_results(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get scan results."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/opportunities/results/{scan_id}",
                headers=self.get_headers(),
                timeout=10
            )
            if response.status_code == 404:
                return {"error": "404_NOT_FOUND", "message": response.text}
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"error": "404_NOT_FOUND", "message": e.response.text}
            print(f"❌ HTTP error getting results: {e}")
            return {"error": str(e), "status_code": e.response.status_code}
        except Exception as e:
            print(f"❌ Failed to get results: {e}")
            return {"error": str(e)}
    
    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get discovery metrics (admin only)."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/opportunities/metrics",
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️  Failed to get metrics: {e}")
            return None
    
    def get_user_status(self) -> Optional[Dict[str, Any]]:
        """Get user discovery status."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/opportunities/user-status",
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️  Failed to get user status: {e}")
            return None
    
    def monitor_scan(self, scan_id: str, max_wait_seconds: int = 180) -> Dict[str, Any]:
        """Monitor scan progress until completion or timeout."""
        print(f"\n📊 Monitoring scan {scan_id} (max wait: {max_wait_seconds}s)...")
        start_time = time.time()
        last_status = None
        check_interval = 3
        not_found_count = 0
        max_not_found = 5  # Allow some initial "not_found" responses
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                print(f"\n⏱️  Timeout reached ({max_wait_seconds}s)")
                break
            
            status_data = self.check_scan_status(scan_id)
            if not status_data:
                print(f"[{elapsed:.1f}s] ⚠️  Could not get status")
                time.sleep(check_interval)
                continue
            
            current_status = status_data.get("status")
            success = status_data.get("success", False)
            
            # Track "not_found" responses
            if current_status == "not_found":
                not_found_count += 1
                if not_found_count <= max_not_found:
                    print(f"[{elapsed:.1f}s] ⚠️  Status: not_found (attempt {not_found_count}/{max_not_found})")
                    time.sleep(1)  # Check more frequently during initial setup
                    continue
                else:
                    print(f"\n⚠️  Scan not found after {not_found_count} attempts ({elapsed:.1f}s)")
                    return {"status": "not_found", "data": status_data, "elapsed_seconds": elapsed, "attempts": not_found_count}
            
            # Print status update if it changed
            if current_status != last_status:
                print(f"\n[{elapsed:.1f}s] Status: {current_status} (success: {success})")
                last_status = current_status
                not_found_count = 0  # Reset counter when status changes
                
                if "progress" in status_data:
                    progress = status_data["progress"]
                    print(f"   Progress: {progress.get('strategies_completed', 0)}/{progress.get('total_strategies', 0)} strategies")
                    print(f"   Opportunities found so far: {progress.get('opportunities_found_so_far', 0)}")
                    if progress.get('percentage'):
                        print(f"   Completion: {progress.get('percentage')}%")
            
            # Periodic progress updates
            elif current_status == "scanning" and int(elapsed) % 10 == 0:
                if "progress" in status_data:
                    progress = status_data["progress"]
                    print(f"[{elapsed:.1f}s] Still scanning... {progress.get('strategies_completed', 0)}/{progress.get('total_strategies', 0)} strategies")
            
            # Check if complete or failed
            if current_status == "complete":
                print(f"\n✅ Scan completed successfully in {elapsed:.1f}s")
                return {"status": "complete", "data": status_data, "elapsed_seconds": elapsed}
            elif current_status == "failed":
                print(f"\n❌ Scan failed after {elapsed:.1f}s")
                return {"status": "failed", "data": status_data, "elapsed_seconds": elapsed}
            
            time.sleep(check_interval)
        
        # Final status check
        final_status = self.check_scan_status(scan_id)
        return {
            "status": "timeout",
            "data": final_status,
            "elapsed_seconds": elapsed
        }
    
    def investigate_redis_keys(self, scan_id: str, cache_key: Optional[str] = None) -> Dict[str, Any]:
        """Investigate Redis key existence (via service analysis)."""
        print(f"\n🔍 Investigating Redis keys for scan_id={scan_id}")
        
        # Expected Redis keys based on code analysis:
        # 1. opportunity_scan_lookup:{scan_id} -> cache_key
        # 2. opportunity_scan_result:{cache_key} -> scan result data
        # 3. opportunity_user_latest_scan:{user_id} -> cache_key
        
        expected_keys = {
            "lookup": f"opportunity_scan_lookup:{scan_id}",
            "user_latest": f"opportunity_user_latest_scan:{self.user_id}" if self.user_id else None
        }
        
        if cache_key:
            expected_keys["result"] = f"opportunity_scan_result:{cache_key}"
        
        print(f"   Expected Redis keys:")
        for key_type, key_name in expected_keys.items():
            if key_name:
                print(f"   - {key_type}: {key_name}")
        
        # Note: We can't directly access Redis, but we can check via API endpoints
        # The service should check Redis when we call status/results endpoints
        return {
            "expected_keys": expected_keys,
            "note": "Direct Redis access not available via API. Checking via service endpoints..."
        }
    
    def full_investigation(self):
        """Run full investigation."""
        print("=" * 80)
        print("SCAN RESULTS 404 INVESTIGATION")
        print("=" * 80)
        
        # Step 1: Authenticate
        if not self.authenticate():
            return
        
        # Step 2: Get user status
        print("\n" + "=" * 80)
        print("STEP 1: User Status Check")
        print("=" * 80)
        user_status = self.get_user_status()
        if user_status:
            print(json.dumps(user_status, indent=2))
        
        # Step 3: Get metrics
        print("\n" + "=" * 80)
        print("STEP 2: System Metrics")
        print("=" * 80)
        metrics = self.get_metrics()
        if metrics:
            print(json.dumps(metrics, indent=2))
        
        # Step 4: Initiate scan
        print("\n" + "=" * 80)
        print("STEP 3: Initiating New Scan")
        print("=" * 80)
        scan_id = self.initiate_scan()
        if not scan_id:
            print("❌ Cannot proceed without scan_id")
            return
        
        # Small delay to allow background task to register
        print("\n⏳ Waiting 2 seconds for background task to register...")
        time.sleep(2)
        
        # Step 5: Investigate Redis keys
        print("\n" + "=" * 80)
        print("STEP 4: Redis Key Investigation")
        print("=" * 80)
        redis_info = self.investigate_redis_keys(scan_id)
        print(json.dumps(redis_info, indent=2))
        
        # Step 6: Monitor scan
        print("\n" + "=" * 80)
        print("STEP 5: Monitoring Scan Progress")
        print("=" * 80)
        monitor_result = self.monitor_scan(scan_id, max_wait_seconds=180)
        
        # Step 7: Check results endpoint
        print("\n" + "=" * 80)
        print("STEP 6: Checking Results Endpoint")
        print("=" * 80)
        results = self.get_scan_results(scan_id)
        if results:
            if "error" in results:
                print(f"❌ Error getting results: {results.get('error')}")
                print(f"   Message: {results.get('message', 'N/A')}")
            else:
                print(f"✅ Results retrieved successfully")
                print(f"   Total opportunities: {results.get('total_opportunities', 0)}")
                print(f"   Scan ID: {results.get('scan_id')}")
        
        # Step 8: Final status check
        print("\n" + "=" * 80)
        print("STEP 7: Final Status Check")
        print("=" * 80)
        final_status = self.check_scan_status(scan_id)
        print(json.dumps(final_status, indent=2))
        
        # Step 9: Summary
        print("\n" + "=" * 80)
        print("INVESTIGATION SUMMARY")
        print("=" * 80)
        print(f"Scan ID: {scan_id}")
        print(f"Monitor Status: {monitor_result.get('status')}")
        print(f"Elapsed Time: {monitor_result.get('elapsed_seconds', 0):.1f}s")
        
        if results and "error" in results:
            error_type = results.get('error')
            print(f"\n❌ RESULTS ENDPOINT ERROR: {error_type}")
            
            if error_type == "404_NOT_FOUND":
                print("\n🔍 ROOT CAUSE ANALYSIS (404 Not Found):")
                print("   - Scan status endpoint returned: success=True")
                print("   - But results endpoint returned: 404 Not Found")
                print("\n   Possible causes:")
                print("   1. Scan completed but results not persisted to Redis")
                print("   2. Cache key lookup failed (scan_id -> cache_key mapping missing)")
                print("   3. Cross-worker issue (scan on Worker A, results request on Worker B)")
                print("   4. Scan timed out before saving results")
                print("   5. Redis persistence code path not executing")
                print("   6. _register_scan_lookup() not called or failed silently")
            elif "still in progress" in str(results.get('message', '')).lower():
                print("\n⚠️  Scan still in progress - this is expected if scan hasn't completed yet")
                print("   Monitor status shows:", monitor_result.get('status'))
        else:
            print(f"\n✅ Results endpoint working correctly")
            if results:
                print(f"   Total opportunities: {results.get('total_opportunities', 0)}")
        
        print("\n" + "=" * 80)

if __name__ == "__main__":
    investigator = ScanInvestigator()
    investigator.full_investigation()
