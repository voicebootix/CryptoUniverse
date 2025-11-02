"""
Comprehensive Test Script for Opportunity Scan API and Diagnostics

Tests the complete opportunity scan workflow including:
1. Authentication
2. Initiating opportunity scan
3. Monitoring scan progress
4. Retrieving scan results
5. Testing all diagnostic endpoints
6. Checking scan lifecycle and debug information

Usage:
    python test_opportunity_scan_comprehensive.py

Author: CTO Assistant
Date: 2025-01-16
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

# Disable SSL warnings for testing (not recommended for production)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OpportunityScanTester:
    """Comprehensive tester for opportunity scan API and diagnostics."""

    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url
        self.email = email
        self.password = password
        self.access_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification for testing

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth token."""
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def authenticate(self) -> bool:
        """Authenticate and get access token."""
        print(f"\n{'='*70}")
        print(f"🔐 AUTHENTICATION")
        print(f"{'='*70}")
        print(f"Email: {self.email}")
        
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"email": self.email, "password": self.password},
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.user_id = data.get("user_id")
                print(f"✅ Authentication successful!")
                print(f"   Role: {data.get('role')}")
                print(f"   User ID: {self.user_id}")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False

        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def initiate_scan(self, force_refresh: bool = True, filters: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Initiate an opportunity scan."""
        print(f"\n{'='*70}")
        print(f"🔍 INITIATING OPPORTUNITY SCAN")
        print(f"{'='*70}")
        print(f"Force refresh: {force_refresh}")
        if filters:
            print(f"Filters: {json.dumps(filters, indent=2)}")

        try:
            payload = {"force_refresh": force_refresh}
            if filters:
                payload.update(filters)

            response = self.session.post(
                f"{self.base_url}/opportunities/discover",
                json=payload,
                headers=self._get_headers(),
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Scan initiated successfully!")
                print(f"   Scan ID: {data.get('scan_id')}")
                print(f"   Status: {data.get('status')}")
                print(f"   Estimated time: {data.get('estimated_completion_seconds')}s")
                print(f"   Poll URL: {data.get('poll_url')}")
                if 'filters' in data:
                    print(f"   Filters: {json.dumps(data.get('filters'), indent=2)}")
                return data
            else:
                print(f"❌ Scan initiation failed: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return None

        except Exception as e:
            print(f"❌ Scan initiation error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def check_scan_status(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Check the status of an ongoing scan."""
        try:
            response = self.session.get(
                f"{self.base_url}/opportunities/status/{scan_id}",
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Status check failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return None

        except Exception as e:
            print(f"⚠️ Status check error: {e}")
            return None

    def monitor_scan(self, scan_id: str, max_wait: int = 180) -> bool:
        """Monitor scan progress until completion."""
        print(f"\n{'='*70}")
        print(f"📊 MONITORING SCAN PROGRESS")
        print(f"{'='*70}")
        print(f"Scan ID: {scan_id}")
        print(f"Max wait time: {max_wait}s")

        start_time = time.time()
        last_progress = -1
        last_update_time = start_time

        while (time.time() - start_time) < max_wait:
            status_data = self.check_scan_status(scan_id)

            if not status_data:
                time.sleep(3)
                continue

            status = status_data.get("status")
            progress = status_data.get("progress", {})

            # Print progress if changed
            current_progress = progress.get("percentage", 0)
            if current_progress != last_progress or status != "scanning":
                elapsed = int(time.time() - start_time)
                print(f"   [{elapsed}s] Status: {status} | Progress: {current_progress}% "
                      f"({progress.get('strategies_completed', 0)}/"
                      f"{progress.get('total_strategies', 0)} strategies) "
                      f"- {progress.get('opportunities_found_so_far', 0)} opportunities found")
                last_progress = current_progress
                last_update_time = time.time()

            if status == "complete":
                print(f"\n✅ Scan completed!")
                print(f"   Total opportunities: {status_data.get('total_opportunities', 0)}")
                return True
            elif status == "failed":
                print(f"\n❌ Scan failed!")
                print(f"   Message: {status_data.get('message', 'Unknown error')}")
                return False
            elif status == "not_found":
                print(f"\n⚠️ Scan not found!")
                print(f"   Message: {status_data.get('message', 'Unknown error')}")
                return False

            # Check for stuck scan (no update in 60 seconds)
            if time.time() - last_update_time > 60:
                print(f"\n⚠️ Scan appears to be stuck (no updates in 60s)")
                return False

            time.sleep(3)

        print(f"\n⚠️ Scan monitoring timed out after {max_wait}s")
        return False

    def get_scan_results(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get complete scan results."""
        print(f"\n{'='*70}")
        print(f"📋 RETRIEVING SCAN RESULTS")
        print(f"{'='*70}")

        try:
            response = self.session.get(
                f"{self.base_url}/opportunities/results/{scan_id}",
                headers=self._get_headers(),
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Results retrieved successfully!")
                print(f"   Total opportunities: {data.get('total_opportunities', 0)}")
                print(f"   Execution time: {data.get('execution_time_ms', 0):.2f}ms")
                
                opportunities = data.get('opportunities', [])
                if opportunities:
                    print(f"\n   First 3 opportunities:")
                    for i, opp in enumerate(opportunities[:3], 1):
                        print(f"   {i}. {opp.get('symbol')} ({opp.get('opportunity_type')})")
                        print(f"      Strategy: {opp.get('strategy_name')}")
                        print(f"      Profit potential: ${opp.get('profit_potential_usd', 0):.2f}")
                        print(f"      Confidence: {opp.get('confidence_score', 0):.2f}")
                
                return data
            elif response.status_code == 202:
                print(f"⚠️ Scan still in progress")
                print(f"   Message: {response.json().get('detail', 'Unknown')}")
                return None
            else:
                print(f"❌ Results retrieval failed: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                return None

        except Exception as e:
            print(f"❌ Results retrieval error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_scan_metrics(self, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get detailed scan metrics from diagnostic endpoint."""
        print(f"\n{'='*70}")
        print(f"📈 RETRIEVING SCAN METRICS")
        print(f"{'='*70}")

        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            response = self.session.get(
                f"{self.base_url}/scan-diagnostics/scan-metrics",
                headers=self._get_headers(),
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Metrics retrieved successfully!")
                
                # Print summary
                latest = data.get("latest_scan")
                if latest:
                    print(f"\n   Latest Scan:")
                    print(f"      Scan ID: {latest.get('scan_id', 'N/A')}")
                    print(f"      Opportunities: {latest.get('opportunities_discovered', 0)}")
                    print(f"      Execution time: {latest.get('execution_time_ms', 0):.2f}ms")
                
                daily = data.get("daily_stats")
                if daily:
                    stats = daily.get("stats", {})
                    print(f"\n   Daily Statistics:")
                    print(f"      Total scans: {stats.get('total_scans', 0)}")
                    print(f"      Success rate: {daily.get('success_rate', 0):.1f}%")
                
                health = data.get("system_health", {})
                print(f"\n   System Health:")
                print(f"      Status: {health.get('status', 'unknown')}")
                print(f"      Redis connected: {health.get('redis_connected', False)}")
                print(f"      Daily errors: {health.get('daily_errors', 0)}")
                
                return data
            else:
                print(f"❌ Metrics retrieval failed: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                return None

        except Exception as e:
            print(f"❌ Metrics retrieval error: {e}")
            return None

    def get_scan_history(self, user_id: str, limit: int = 5) -> Optional[Dict[str, Any]]:
        """Get scan history for a user."""
        print(f"\n{'='*70}")
        print(f"📜 RETRIEVING SCAN HISTORY")
        print(f"{'='*70}")
        print(f"User ID: {user_id}")

        try:
            response = self.session.get(
                f"{self.base_url}/scan-diagnostics/scan-history/{user_id}",
                headers=self._get_headers(),
                params={"limit": limit},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Scan history retrieved!")
                print(f"   Total scans found: {data.get('total_scans', 0)}")
                
                scans = data.get('scans', [])
                if scans:
                    print(f"\n   Recent scans:")
                    for i, scan in enumerate(scans[:limit], 1):
                        print(f"   {i}. Scan ID: {scan.get('scan_id', 'N/A')}")
                        print(f"      Opportunities: {scan.get('opportunities_count', 0)}")
                        print(f"      Execution time: {scan.get('execution_time_ms', 0):.2f}ms")
                        print(f"      Updated: {scan.get('last_updated', 'N/A')}")
                
                return data
            else:
                print(f"❌ History retrieval failed: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                return None

        except Exception as e:
            print(f"❌ History retrieval error: {e}")
            return None

    def get_scan_lifecycle(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed lifecycle tracking for a specific scan."""
        print(f"\n{'='*70}")
        print(f"🔄 RETRIEVING SCAN LIFECYCLE")
        print(f"{'='*70}")
        print(f"Scan ID: {scan_id}")

        try:
            response = self.session.get(
                f"{self.base_url}/scan-diagnostics/scan-lifecycle/{scan_id}",
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Lifecycle retrieved!")
                print(f"   Current phase: {data.get('current_phase', 'N/A')}")
                print(f"   Current status: {data.get('current_status', 'N/A')}")
                print(f"   Is stuck: {data.get('is_stuck', False)}")
                if data.get('stuck_duration_seconds'):
                    print(f"   Stuck duration: {data.get('stuck_duration_seconds'):.1f}s")
                
                phases = data.get('phases', {})
                if phases:
                    print(f"\n   Phase details:")
                    for phase_name, phase_data in list(phases.items())[:5]:
                        print(f"      {phase_name}: {json.dumps(phase_data, indent=6)[:100]}")
                
                return data
            else:
                print(f"❌ Lifecycle retrieval failed: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                return None

        except Exception as e:
            print(f"❌ Lifecycle retrieval error: {e}")
            return None

    def get_scan_debug(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed debug information for a specific scan."""
        print(f"\n{'='*70}")
        print(f"🐛 RETRIEVING SCAN DEBUG INFO")
        print(f"{'='*70}")
        print(f"Scan ID: {scan_id}")

        try:
            response = self.session.get(
                f"{self.base_url}/scan-diagnostics/scan-debug/{scan_id}",
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Debug info retrieved!")
                print(f"   Overall status: {data.get('overall_status', 'N/A')}")
                print(f"   Current step: {data.get('current_step', 'N/A')}")
                print(f"   Total steps: {data.get('total_steps', 0)}")
                
                steps = data.get('steps', {})
                if steps:
                    print(f"\n   Step details:")
                    for step_num, step_data in list(steps.items())[:5]:
                        status = step_data.get('status', 'unknown')
                        print(f"      Step {step_num}: {status}")
                        if step_data.get('error'):
                            print(f"         Error: {step_data.get('error')[:100]}")
                
                failure_info = data.get('failure_info')
                if failure_info:
                    print(f"\n   ⚠️ Failure detected:")
                    print(f"      Step: {failure_info.get('step', 'N/A')}")
                    print(f"      Error: {failure_info.get('error', 'N/A')}")
                
                return data
            else:
                print(f"❌ Debug retrieval failed: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                return None

        except Exception as e:
            print(f"❌ Debug retrieval error: {e}")
            return None

    def get_user_status(self) -> Optional[Dict[str, Any]]:
        """Get user's opportunity discovery status."""
        print(f"\n{'='*70}")
        print(f"👤 RETRIEVING USER STATUS")
        print(f"{'='*70}")

        try:
            response = self.session.get(
                f"{self.base_url}/opportunities/user-status",
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ User status retrieved!")
                print(f"   User ID: {data.get('user_id')}")
                print(f"   Discovery available: {data.get('discovery_available', False)}")
                
                onboarding = data.get('onboarding_status', {})
                print(f"\n   Onboarding Status:")
                print(f"      Onboarded: {onboarding.get('onboarded', False)}")
                print(f"      Active strategies: {onboarding.get('active_strategies', 0)}")
                
                last_scan = data.get('last_scan_info')
                if last_scan:
                    print(f"\n   Last Scan:")
                    print(f"      Time: {last_scan.get('last_scan', 'N/A')}")
                    time_since = last_scan.get('time_since_last_scan')
                    if time_since:
                        print(f"      Time since: {time_since:.1f}s")
                
                return data
            else:
                print(f"❌ User status retrieval failed: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                return None

        except Exception as e:
            print(f"❌ User status retrieval error: {e}")
            return None


def main():
    """Main test function."""
    print(f"\n{'='*70}")
    print(f"🔬 COMPREHENSIVE OPPORTUNITY SCAN API & DIAGNOSTICS TEST")
    print(f"{'='*70}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Base URL: {BASE_URL}")

    tester = OpportunityScanTester(BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD)

    # Step 1: Authenticate
    if not tester.authenticate():
        print(f"\n❌ Test failed: Authentication error")
        sys.exit(1)

    # Step 2: Get user status
    user_status = tester.get_user_status()
    if not user_status:
        print(f"\n⚠️ Warning: Could not retrieve user status")

    # Step 3: Initiate scan
    scan_data = tester.initiate_scan(force_refresh=True)
    if not scan_data:
        print(f"\n❌ Test failed: Could not initiate scan")
        sys.exit(1)

    scan_id = scan_data.get("scan_id")
    print(f"\n📝 Scan ID for diagnostics: {scan_id}")

    # Step 4: Monitor scan progress
    scan_completed = tester.monitor_scan(scan_id, max_wait=180)
    
    # Step 5: Get scan results if completed
    if scan_completed:
        results = tester.get_scan_results(scan_id)
        if results:
            print(f"\n✅ Successfully retrieved {results.get('total_opportunities', 0)} opportunities")
    else:
        print(f"\n⚠️ Scan did not complete within timeout, but continuing with diagnostics...")

    # Step 6: Get scan metrics
    metrics = tester.get_scan_metrics(user_id=tester.user_id)
    
    # Step 7: Get scan history
    if tester.user_id:
        history = tester.get_scan_history(tester.user_id, limit=5)
    
    # Step 8: Get scan lifecycle
    lifecycle = tester.get_scan_lifecycle(scan_id)
    
    # Step 9: Get scan debug info
    debug_info = tester.get_scan_debug(scan_id)

    # Summary
    print(f"\n{'='*70}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Authentication: Success")
    print(f"{'✅' if scan_data else '❌'} Scan Initiation: {'Success' if scan_data else 'Failed'}")
    print(f"{'✅' if scan_completed else '⚠️'} Scan Completion: {'Success' if scan_completed else 'Timeout/Incomplete'}")
    print(f"{'✅' if metrics else '❌'} Metrics Retrieval: {'Success' if metrics else 'Failed'}")
    print(f"{'✅' if lifecycle else '❌'} Lifecycle Retrieval: {'Success' if lifecycle else 'Failed'}")
    print(f"{'✅' if debug_info else '❌'} Debug Info Retrieval: {'Success' if debug_info else 'Failed'}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
