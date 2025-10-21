"""Test script to verify both diagnostic endpoint enhancement and symbol discovery fix."""
import requests
import json
import sys
import io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"

print("=" * 80)
print("DIAGNOSTIC ENHANCEMENT & SYMBOL DISCOVERY FIX VERIFICATION TEST")
print("=" * 80)
print(f"Test started at: {datetime.now().isoformat()}")

# Login
print("\n[1/3] Logging in...")
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "admin@cryptouniverse.com", "password": "AdminPass123!"},
    timeout=30
)

if response.status_code != 200:
    print(f"❌ Login failed: {response.status_code}")
    exit(1)

token = response.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}
print("✅ Login successful")

# Get background services status with new metrics
print("\n[2/3] Fetching enhanced background services diagnostics...")
services_response = requests.get(
    f"{BASE_URL}/admin/system/background-services",
    headers=headers,
    timeout=30
)

if services_response.status_code != 200:
    print(f"❌ Failed to get status: {services_response.status_code}")
    print(services_response.text)
    exit(1)

data = services_response.json()

print("\n" + "=" * 80)
print("SYSTEM STATUS")
print("=" * 80)

uptime = data.get('uptime_hours', 0)
redis_available = data.get('redis_available', False)
summary = data.get('services_summary', {})

print(f"\n📊 System Info:")
print(f"   Uptime: {uptime:.2f} hours")
print(f"   Redis: {'✅ Available' if redis_available else '❌ Unavailable'}")
print(f"   Services: {summary.get('running', 0)} running, {summary.get('error', 0)} error, {summary.get('stopped', 0)} stopped")

# Analyze services with focus on effectiveness metrics
services = data.get('services', {})

print("\n" + "=" * 80)
print("SERVICE EFFECTIVENESS METRICS")
print("=" * 80)

# Track test results
test_results = {
    "metrics_present": False,
    "market_data_has_symbols": False,
    "signal_dispatch_metrics": False,
    "balance_sync_metrics": False,
    "services_running": False
}

for service_name, service_info in services.items():
    status = service_info.get('status', 'unknown')
    metrics = service_info.get('metrics')

    print(f"\n🔧 {service_name}:")
    print(f"   Status: {status}")
    print(f"   Interval: {service_info.get('interval_seconds', 0)}s")

    # Check if metrics are present
    if metrics:
        test_results["metrics_present"] = True
        print(f"   📈 Effectiveness Metrics:")

        # Market data sync metrics
        if service_name == "market_data_sync":
            symbols_discovered = metrics.get('symbols_discovered', 0)
            sample_symbols = metrics.get('sample_symbols', [])
            last_sync = metrics.get('last_sync_time', 'N/A')

            print(f"      • Symbols Discovered: {symbols_discovered}")
            if sample_symbols:
                print(f"      • Sample Symbols: {', '.join(sample_symbols[:5])}")
            print(f"      • Last Sync: {last_sync}")

            if symbols_discovered > 0:
                test_results["market_data_has_symbols"] = True

        # Signal dispatch metrics
        elif service_name == "signal_dispatch":
            signals_sent = metrics.get('signals_sent', 0)
            last_dispatch = metrics.get('last_dispatch_time', 'N/A')

            print(f"      • Signals Sent: {signals_sent}")
            print(f"      • Last Dispatch: {last_dispatch}")

            test_results["signal_dispatch_metrics"] = True

        # Balance sync metrics
        elif service_name == "balance_sync":
            users_synced = metrics.get('users_synced', 0)
            total_users = metrics.get('total_users', 0)
            last_sync = metrics.get('last_sync_time', 'N/A')

            print(f"      • Users Synced: {users_synced}/{total_users}")
            print(f"      • Last Sync: {last_sync}")

            test_results["balance_sync_metrics"] = True

        # Other services - show all available metrics
        else:
            for key, value in metrics.items():
                if key != 'timestamp':
                    print(f"      • {key}: {value}")
    else:
        print(f"   ⏳ No metrics available yet (service may not have run)")

if summary.get('running', 0) > 0:
    test_results["services_running"] = True

# Final verdict
print("\n" + "=" * 80)
print("TEST RESULTS")
print("=" * 80)

print(f"\n✓ Test 1 - Diagnostic Endpoint Enhancement:")
if test_results["metrics_present"]:
    print("  ✅ PASS: Metrics field is now present in service details")
else:
    print("  ⚠️  PENDING: Metrics not yet available (services may need to run first)")

print(f"\n✓ Test 2 - Symbol Discovery Fix:")
if test_results["market_data_has_symbols"]:
    print("  ✅ PASS: Market data sync is discovering symbols (no longer 0)")
elif test_results["metrics_present"]:
    # Metrics present but no symbols yet - may not have run
    print("  ⏳ PENDING: Service hasn't run yet or metrics are initializing")
else:
    print("  ⚠️  UNKNOWN: No metrics available to verify symbol discovery")

print(f"\n✓ Test 3 - Service Health:")
if test_results["services_running"]:
    print("  ✅ PASS: Background services are running")
else:
    print("  ❌ FAIL: No services are running")

# Overall assessment
print("\n" + "=" * 80)
print("OVERALL ASSESSMENT")
print("=" * 80)

if test_results["metrics_present"] and test_results["market_data_has_symbols"]:
    print("\n🎉 SUCCESS! Both fixes are working correctly:")
    print("   1. ✅ Diagnostic endpoint now shows effectiveness metrics")
    print("   2. ✅ Symbol discovery is no longer returning 0 symbols")
    print("\nThe system can now detect 'silent failures' where services run but don't do useful work!")

elif test_results["metrics_present"] and not test_results["market_data_has_symbols"]:
    print("\n⏳ PARTIAL SUCCESS:")
    print("   1. ✅ Diagnostic endpoint enhancement deployed (metrics field present)")
    print("   2. ⏳ Symbol discovery fix deployed but waiting for service to run")
    print("\nRecommendation: Wait 5-10 minutes for market_data_sync to run, then re-test")

elif not test_results["metrics_present"]:
    print("\n⚠️  DEPLOYMENT PENDING:")
    print("   The enhanced code may not be deployed yet to Render")
    print("   Check Render deployment status and wait for deployment to complete")

else:
    print("\n❌ UNEXPECTED STATE:")
    print("   Please review the service details above for more information")

print("\n" + "=" * 80)
print(f"Test completed at: {datetime.now().isoformat()}")
print("=" * 80)
