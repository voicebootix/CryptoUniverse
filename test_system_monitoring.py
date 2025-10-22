"""
Test Script for Unified System Monitoring

This script tests the comprehensive system monitoring endpoints that provide
real-time metrics for all 60+ CryptoUniverse services.

Usage:
    python test_system_monitoring.py

Author: CTO Assistant
Date: 2025-10-22
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SystemMonitoringTester:
    """Test system monitoring endpoints."""

    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url
        self.email = email
        self.password = password
        self.access_token: Optional[str] = None
        self.session = requests.Session()
        self.session.verify = False

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
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
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

    def get_system_health(self) -> Optional[Dict[str, Any]]:
        """Get comprehensive system health."""
        print(f"\n🏥 Fetching system health...")

        try:
            response = self.session.get(
                f"{self.base_url}/monitoring/system-health",
                headers=self._get_headers(),
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ System health retrieved!")
                return data
            else:
                print(f"❌ Failed to get system health: {response.status_code}")
                print(f"   Response: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def get_infrastructure_metrics(self) -> Optional[Dict[str, Any]]:
        """Get infrastructure metrics."""
        print(f"\n🔧 Fetching infrastructure metrics...")

        try:
            response = self.session.get(
                f"{self.base_url}/monitoring/infrastructure",
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Infrastructure metrics retrieved!")
                return data
            else:
                print(f"❌ Failed: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def print_system_health_summary(self, health: Dict[str, Any]):
        """Print formatted system health summary."""
        print(f"\n" + "="*80)
        print(f"🏥 SYSTEM HEALTH DASHBOARD")
        print(f"="*80)

        # Overall status
        overall = health.get("overall_status", "unknown").upper()
        status_emoji = "🟢" if overall == "HEALTHY" else "🟡" if overall == "DEGRADED" else "🔴"
        print(f"\n{status_emoji} Overall Status: {overall}")
        print(f"   Timestamp: {health.get('timestamp')}")

        # Summary
        summary = health.get("summary", {})
        print(f"\n📊 Summary:")
        print(f"   Total Services: {summary.get('total_services', 0)}")
        print(f"   Healthy: {summary.get('healthy_services', 0)}")
        print(f"   Degraded: {summary.get('degraded_services', 0)}")
        print(f"   Critical: {summary.get('critical_services', 0)}")
        print(f"   Total Throughput (5m): {summary.get('total_throughput_5m', 0)}")
        print(f"   Avg Error Rate: {summary.get('avg_error_rate_5m', 0):.2f}%")
        print(f"   Active Alerts: {summary.get('total_alerts', 0)}")

        # Services
        services = health.get("services", {})
        print(f"\n🔍 Service Metrics:")
        print(f"   {'-'*76}")

        for service_name, metrics in services.items():
            status = metrics.get("status", "unknown")
            status_icon = "🟢" if status == "healthy" else "🟡" if status == "degraded" else "🔴"

            print(f"\n   {status_icon} {service_name.replace('_', ' ').title()}")
            print(f"      Status: {status} | Uptime: {metrics.get('uptime_percentage', 0):.1f}%")
            print(f"      Response Time: P50={metrics.get('response_time_p50_ms', 0):.0f}ms "
                  f"P95={metrics.get('response_time_p95_ms', 0):.0f}ms "
                  f"P99={metrics.get('response_time_p99_ms', 0):.0f}ms")
            print(f"      Error Rate (5m): {metrics.get('error_rate_5m', 0):.2f}% | "
                  f"Throughput (5m): {metrics.get('throughput_5m', 0)}")

            if metrics.get("active_connections"):
                print(f"      Active Connections: {metrics.get('active_connections')}")

            # Details
            details = metrics.get("details", {})
            if details:
                print(f"      Details:")
                for key, value in list(details.items())[:5]:  # Show first 5 details
                    if isinstance(value, (int, float)):
                        print(f"        - {key}: {value}")
                    elif isinstance(value, dict):
                        print(f"        - {key}: {len(value)} items")

            # Warnings
            warnings = metrics.get("warnings", [])
            if warnings:
                print(f"      ⚠️  Warnings:")
                for warning in warnings:
                    print(f"        - {warning}")

        # Alerts
        alerts = health.get("alerts", [])
        if alerts:
            print(f"\n🚨 Active Alerts:")
            for alert in alerts[:10]:  # Show first 10
                severity_icon = "⚠️ " if alert.get("severity") == "warning" else "🔴"
                print(f"   {severity_icon} [{alert.get('service')}] {alert.get('message')}")

        print(f"\n" + "="*80)

    def print_infrastructure_summary(self, infrastructure: Dict[str, Any]):
        """Print infrastructure metrics summary."""
        print(f"\n" + "="*80)
        print(f"🔧 INFRASTRUCTURE METRICS")
        print(f"="*80)

        metrics = infrastructure.get("metrics", {})

        # Redis
        redis = metrics.get("redis", {})
        if redis.get("connected"):
            print(f"\n📦 Redis:")
            print(f"   Status: Connected ✅")
            print(f"   Uptime: {redis.get('uptime_seconds', 0) / 3600:.1f} hours")
            print(f"   Memory Used: {redis.get('used_memory_mb', 0):.1f} MB")
            print(f"   Memory Peak: {redis.get('used_memory_peak_mb', 0):.1f} MB")
            print(f"   Fragmentation Ratio: {redis.get('memory_fragmentation_ratio', 0):.2f}")
            print(f"   Connected Clients: {redis.get('connected_clients', 0)}")
            print(f"   Operations/sec: {redis.get('ops_per_sec', 0)}")
            print(f"   Hit Rate: {redis.get('hit_rate', 0):.1f}%")
            print(f"   Evicted Keys: {redis.get('evicted_keys', 0)}")
        else:
            print(f"\n📦 Redis: Disconnected ❌")

        # Database
        db = metrics.get("database", {})
        if db.get("connected"):
            print(f"\n🗄️  Database:")
            print(f"   Status: Connected ✅")
            print(f"   Query Latency: {db.get('query_latency_ms', 0):.2f} ms")
            print(f"   Pool Size: {db.get('pool_size', 0)}")
            print(f"   Connections In Use: {db.get('connections_in_use', 0)}")
            print(f"   Overflow Connections: {db.get('overflow_connections', 0)}")
            print(f"   Pool Utilization: {db.get('pool_utilization_pct', 0):.1f}%")
        else:
            print(f"\n🗄️  Database: Disconnected ❌")

        print(f"\n" + "="*80)


def main():
    """Main test function."""
    print(f"\n{'='*80}")
    print(f"🔬 UNIFIED SYSTEM MONITORING TEST")
    print(f"{'='*80}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    tester = SystemMonitoringTester(BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD)

    # Step 1: Authenticate
    if not tester.authenticate():
        print(f"\n❌ Test failed: Authentication error")
        return

    # Step 2: Get system health
    health = tester.get_system_health()
    if health:
        tester.print_system_health_summary(health)

    # Step 3: Get infrastructure metrics
    infrastructure = tester.get_infrastructure_metrics()
    if infrastructure:
        tester.print_infrastructure_summary(infrastructure)

    print(f"\n{'='*80}")
    print(f"✅ Test completed!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
