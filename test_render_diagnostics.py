"""
Test the new diagnostic endpoints to access Render logs and service status.
"""
import requests
import json

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"

def login():
    """Login and get token."""
    print("Logging in as admin...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "admin@cryptouniverse.com",
            "password": "AdminPass123!"
        },
        timeout=30
    )
    if response.status_code == 200:
        print("✅ Login successful\n")
        return response.json().get("access_token")
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

def get_background_services(token):
    """Get detailed background services status."""
    print("="*60)
    print("BACKGROUND SERVICES STATUS")
    print("="*60)

    response = requests.get(
        f"{BASE_URL}/admin/system/background-services",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()

        print(f"\nUptime: {data.get('uptime_hours', 0)} hours")
        print(f"Redis Available: {data.get('redis_available', False)}")

        summary = data.get('services_summary', {})
        print(f"\nServices Summary:")
        print(f"  Total: {summary.get('total', 0)}")
        print(f"  Running: {summary.get('running', 0)}")
        print(f"  Stopped: {summary.get('stopped', 0)}")
        print(f"  Error: {summary.get('error', 0)}")

        print(f"\nDetailed Service Status:")
        services = data.get('services', {})
        for service_name, service_info in services.items():
            status = service_info.get('status', 'unknown')
            interval = service_info.get('interval_seconds', 0)

            status_icon = "✅" if status == "running" else "⚠️" if status == "starting" else "❌"
            print(f"  {status_icon} {service_name}: {status} (every {interval}s)")

            if 'error' in service_info:
                print(f"      Error: {service_info['error']}")

        # Highlight signal_dispatch specifically
        signal_dispatch = services.get('signal_dispatch', {})
        print(f"\n🎯 Signal Dispatch Service:")
        print(f"   Status: {signal_dispatch.get('status', 'unknown')}")
        print(f"   Interval: {signal_dispatch.get('interval_seconds', 0)}s (should be 300s/5min)")

        return data
    else:
        print(f"❌ Failed to get services status: {response.status_code}")
        print(response.text)
        return None

def get_system_logs(token, lines=200, service_filter=None, level_filter=None):
    """Get system logs."""
    print("\n" + "="*60)
    print("SYSTEM LOGS")
    print("="*60)

    params = {"lines": lines}
    if service_filter:
        params["service"] = service_filter
    if level_filter:
        params["level"] = level_filter

    response = requests.get(
        f"{BASE_URL}/admin/system/logs",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()

        print(f"\nLog File: {data.get('log_file', 'Not found')}")
        print(f"Total Returned: {data.get('total_returned', 0)}")
        print(f"Filters Applied: {data.get('filters', {})}")

        logs = data.get('logs', [])
        if not logs:
            print("\n⚠️  No logs found!")
        else:
            print(f"\nShowing last {min(20, len(logs))} log entries:\n")
            for log in logs[-20:]:  # Show last 20
                timestamp = log.get('timestamp', 'N/A')
                level = log.get('level', 'INFO')
                event = log.get('event', '')

                # Truncate long events
                if len(event) > 100:
                    event = event[:97] + "..."

                print(f"[{timestamp}] {level:8} {event}")

        return data
    else:
        print(f"❌ Failed to get logs: {response.status_code}")
        print(response.text)
        return None

def search_logs_for_issues(token):
    """Search logs for signal-related errors."""
    print("\n" + "="*60)
    print("SEARCHING FOR SIGNAL/BACKGROUND SERVICE ISSUES")
    print("="*60)

    # Search for signal-related logs
    print("\n🔍 Searching for 'signal' in logs...")
    get_system_logs(token, lines=100, service_filter="signal")

    # Search for ERROR level
    print("\n🔍 Searching for ERROR logs...")
    get_system_logs(token, lines=100, level_filter="ERROR")

    # Search for background service logs
    print("\n🔍 Searching for 'background' in logs...")
    get_system_logs(token, lines=100, service_filter="background")

if __name__ == "__main__":
    print("="*60)
    print("RENDER DIAGNOSTICS - CryptoUniverse")
    print("="*60)

    token = login()
    if not token:
        print("\n❌ Cannot proceed without authentication")
        exit(1)

    # Get background services status
    services_data = get_background_services(token)

    # Get recent logs
    get_system_logs(token, lines=50)

    # Search for issues if services aren't running
    if services_data:
        summary = services_data.get('services_summary', {})
        if summary.get('running', 0) < summary.get('total', 0):
            search_logs_for_issues(token)

    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)
    print("\nNext Steps:")
    print("1. If signal_dispatch shows 'not_started' or 'stopped':")
    print("   - Check the ERROR logs above for startup failures")
    print("   - Verify Redis is connected")
    print("   - Check if 30-second deferred startup delay has passed")
    print("\n2. If logs show 'No log file found':")
    print("   - Logs are written to stdout on Render (check Render dashboard)")
    print("   - The endpoint will still show background service status")
    print("\n3. To deploy these changes to Render:")
    print("   - Commit the updated admin.py file")
    print("   - Push to your repository")
    print("   - Render will auto-deploy")
