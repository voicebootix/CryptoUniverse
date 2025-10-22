"""
Test Script for Opportunity Scan Diagnostics

This script demonstrates how to:
1. Authenticate as admin
2. Initiate an opportunity scan
3. Monitor scan progress
4. Retrieve detailed scan metrics and logs

Usage:
    python test_scan_diagnostics.py

Author: CTO Assistant
Date: 2025-10-22
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

# Disable SSL warnings for self-signed certs (Render uses valid certs, but just in case)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ScanDiagnosticsTester:
    """Test and monitor opportunity scan diagnostics."""

    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url
        self.email = email
        self.password = password
        self.access_token: Optional[str] = None
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification

    def authenticate(self) -> bool:
        """Authenticate and get access token."""
        print(f"\n🔐 Authenticating as {self.email}...")

        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"email": self.email, "password": self.password},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                print(f"✅ Authentication successful!")
                print(f"   Role: {data.get('role')}")
                print(f"   User ID: {data.get('user_id')}")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth token."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def initiate_scan(self, force_refresh: bool = True) -> Optional[Dict[str, Any]]:
        """Initiate an opportunity scan."""
        print(f"\n🔍 Initiating opportunity scan (force_refresh={force_refresh})...")

        try:
            response = self.session.post(
                f"{self.base_url}/opportunities/discover",
                json={"force_refresh": force_refresh},
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Scan initiated successfully!")
                print(f"   Scan ID: {data.get('scan_id')}")
                print(f"   Status: {data.get('status')}")
                print(f"   Estimated time: {data.get('estimated_completion_seconds')}s")
                return data
            else:
                print(f"❌ Scan initiation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Scan initiation error: {e}")
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
                return None

        except Exception as e:
            print(f"⚠️ Status check error: {e}")
            return None

    def monitor_scan(self, scan_id: str, max_wait: int = 120) -> bool:
        """Monitor scan progress until completion."""
        print(f"\n📊 Monitoring scan progress...")

        start_time = time.time()
        last_progress = -1

        while (time.time() - start_time) < max_wait:
            status_data = self.check_scan_status(scan_id)

            if not status_data:
                time.sleep(3)
                continue

            status = status_data.get("status")
            progress = status_data.get("progress", {})

            # Print progress if changed
            current_progress = progress.get("percentage", 0)
            if current_progress != last_progress:
                print(f"   Progress: {current_progress}% "
                      f"({progress.get('strategies_completed', 0)}/"
                      f"{progress.get('total_strategies', 0)} strategies) "
                      f"- {progress.get('opportunities_found_so_far', 0)} opportunities found")
                last_progress = current_progress

            if status == "complete":
                print(f"✅ Scan completed!")
                print(f"   Total opportunities: {status_data.get('total_opportunities', 0)}")
                return True
            elif status == "failed":
                print(f"❌ Scan failed!")
                return False

            time.sleep(3)

        print(f"⚠️ Scan monitoring timed out after {max_wait}s")
        return False

    def get_scan_metrics(self, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get detailed scan metrics from diagnostic endpoint."""
        print(f"\n📈 Retrieving scan metrics...")

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
                return data
            else:
                print(f"❌ Metrics retrieval failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Metrics retrieval error: {e}")
            return None

    def get_scan_history(self, user_id: str, limit: int = 10) -> Optional[Dict[str, Any]]:
        """Get scan history for a user."""
        print(f"\n📜 Retrieving scan history for user {user_id}...")

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
                return data
            else:
                print(f"❌ History retrieval failed: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ History retrieval error: {e}")
            return None

    def print_metrics_summary(self, metrics: Dict[str, Any]):
        """Print a formatted summary of scan metrics."""
        print(f"\n" + "="*60)
        print(f"📊 SCAN METRICS SUMMARY")
        print(f"="*60)

        # Latest scan
        latest = metrics.get("latest_scan")
        if latest:
            print(f"\n🔍 Latest Scan:")
            print(f"   Scan ID: {latest.get('scan_id')}")
            print(f"   User ID: {latest.get('user_id')}")
            print(f"   Opportunities: {latest.get('opportunities_discovered')}")
            print(f"   Strategies: {latest.get('strategies_scanned')}")
            print(f"   Execution time: {latest.get('execution_time_ms'):.2f}ms")
            print(f"   Success: {latest.get('success')}")
            print(f"   Timestamp: {latest.get('timestamp')}")

        # Daily stats
        daily = metrics.get("daily_stats")
        if daily:
            stats = daily.get("stats", {})
            print(f"\n📅 Daily Statistics ({daily.get('date')}):")
            print(f"   Total scans: {stats.get('total_scans', 0)}")
            print(f"   Successful: {stats.get('successful_scans', 0)}")
            print(f"   Success rate: {daily.get('success_rate', 0):.1f}%")
            print(f"   Total opportunities: {stats.get('total_opportunities', 0)}")
            print(f"   Total strategies: {stats.get('total_strategies', 0)}")
            print(f"   Avg execution time: {stats.get('avg_execution_time_ms', 0):.2f}ms")

        # System health
        health = metrics.get("system_health", {})
        print(f"\n🏥 System Health:")
        print(f"   Status: {health.get('status', 'unknown')}")
        print(f"   Redis connected: {health.get('redis_connected', False)}")
        print(f"   Daily errors: {health.get('daily_errors', 0)}")

        print(f"\n" + "="*60)


def main():
    """Main test function."""
    print(f"\n{'='*60}")
    print(f"🔬 OPPORTUNITY SCAN DIAGNOSTICS TEST")
    print(f"{'='*60}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    tester = ScanDiagnosticsTester(BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD)

    # Step 1: Authenticate
    if not tester.authenticate():
        print(f"\n❌ Test failed: Authentication error")
        return

    # Step 2: Initiate scan
    scan_data = tester.initiate_scan(force_refresh=True)
    if not scan_data:
        print(f"\n❌ Test failed: Could not initiate scan")
        return

    scan_id = scan_data.get("scan_id")

    # Step 3: Monitor scan progress
    success = tester.monitor_scan(scan_id, max_wait=120)

    # Step 4: Get detailed metrics
    metrics = tester.get_scan_metrics()
    if metrics:
        tester.print_metrics_summary(metrics)

    # Step 5: Get scan history (extract user_id from scan_id)
    # scan_id format: scan_{user_id}_{timestamp}
    parts = scan_id.split("_")
    if len(parts) >= 3:
        user_id = "_".join(parts[1:-1])  # Handle UUIDs with underscores
        history = tester.get_scan_history(user_id, limit=5)

        if history and history.get("scans"):
            print(f"\n📜 Recent Scan History:")
            for i, scan in enumerate(history.get("scans", [])[:5], 1):
                print(f"\n   {i}. Scan ID: {scan.get('scan_id')}")
                print(f"      Opportunities: {scan.get('opportunities_count')}")
                print(f"      Execution time: {scan.get('execution_time_ms'):.2f}ms")
                print(f"      Updated: {scan.get('last_updated')}")

    print(f"\n{'='*60}")
    print(f"✅ Test completed!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
