"""
Test Opportunity Scan with Diagnostic Monitoring

This script:
1. Initiates an admin opportunity scan
2. Monitors scan progress
3. Checks diagnostic metrics before and after
4. Verifies scan history tracking
"""

import requests
import json
import time
import urllib3
urllib3.disable_warnings()

BASE_URL = 'https://cryptouniverse.onrender.com/api/v1'
ADMIN_EMAIL = 'admin@cryptouniverse.com'
ADMIN_PASSWORD = 'AdminPass123!'

print('='*80)
print('OPPORTUNITY SCAN DIAGNOSTIC TEST')
print('='*80)

# Step 1: Authenticate
print('\nStep 1: Authenticating as admin...')
resp = requests.post(
    f'{BASE_URL}/auth/login',
    json={'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD},
    verify=False,
    timeout=15
)
token = resp.json()['access_token']
user_id = resp.json()['user_id']
headers = {'Authorization': f'Bearer {token}'}
print(f'OK - Authenticated as admin')
print(f'User ID: {user_id}')

# Step 2: Check metrics BEFORE scan
print('\n' + '-'*80)
print('Step 2: Checking scan metrics BEFORE initiating scan...')
print('-'*80)
try:
    resp = requests.get(
        f'{BASE_URL}/scan-diagnostics/scan-metrics',
        headers=headers,
        verify=False,
        timeout=15
    )
    if resp.status_code == 200:
        data = resp.json()
        latest = data.get('latest_scan')
        if latest:
            print(f'Previous Latest Scan:')
            print(f'  Scan ID: {latest.get("scan_id")}')
            print(f'  Opportunities: {latest.get("opportunities_discovered")}')
        else:
            print('No previous scans found')

        daily = data.get('daily_stats')
        if daily:
            stats = daily.get('stats', {})
            print(f'Daily Stats (before):')
            print(f'  Total Scans: {stats.get("total_scans", 0)}')
            print(f'  Success Rate: {daily.get("success_rate", 0):.1f}%')
except Exception as e:
    print(f'Error checking pre-scan metrics: {e}')

# Step 3: Initiate opportunity scan
print('\n' + '-'*80)
print('Step 3: Initiating opportunity scan...')
print('-'*80)
try:
    resp = requests.post(
        f'{BASE_URL}/opportunities/discover',
        json={'force_refresh': True},
        headers=headers,
        verify=False,
        timeout=15
    )
    print(f'Status: {resp.status_code}')

    if resp.status_code == 200:
        scan_data = resp.json()
        scan_id = scan_data.get('scan_id')
        print(f'OK - Scan initiated!')
        print(f'Scan ID: {scan_id}')
        print(f'Status: {scan_data.get("status")}')
        print(f'Estimated time: {scan_data.get("estimated_completion_seconds")}s')

        # Step 4: Monitor scan progress
        print('\n' + '-'*80)
        print('Step 4: Monitoring scan progress...')
        print('-'*80)

        max_wait = 120
        start_time = time.time()
        last_progress = -1

        while (time.time() - start_time) < max_wait:
            try:
                status_resp = requests.get(
                    f'{BASE_URL}/opportunities/status/{scan_id}',
                    headers=headers,
                    verify=False,
                    timeout=15
                )

                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    status = status_data.get('status')
                    progress = status_data.get('progress', {})
                    current_progress = progress.get('percentage', 0)

                    if current_progress != last_progress:
                        print(f'  Progress: {current_progress}% - {progress.get("strategies_completed", 0)}/{progress.get("total_strategies", 0)} strategies - {progress.get("opportunities_found_so_far", 0)} opportunities')
                        last_progress = current_progress

                    if status == 'complete':
                        print(f'\nOK - Scan completed!')
                        print(f'Total opportunities: {status_data.get("total_opportunities", 0)}')
                        break
                    elif status == 'failed':
                        print(f'\nERROR - Scan failed!')
                        break
            except Exception as e:
                print(f'  Warning: {e}')

            time.sleep(3)

        # Step 5: Check diagnostic logs immediately after
        print('\n' + '-'*80)
        print('Step 5: Checking scan diagnostics AFTER scan...')
        print('-'*80)

        time.sleep(2)  # Brief pause to ensure metrics are written

        resp = requests.get(
            f'{BASE_URL}/scan-diagnostics/scan-metrics',
            headers=headers,
            verify=False,
            timeout=15
        )

        if resp.status_code == 200:
            data = resp.json()

            # Latest scan
            latest = data.get('latest_scan')
            if latest:
                print(f'\nLatest Scan Metrics:')
                print(f'  Scan ID: {latest.get("scan_id")}')
                print(f'  User ID: {latest.get("user_id")}')
                print(f'  Timestamp: {latest.get("timestamp")}')
                print(f'  Opportunities Discovered: {latest.get("opportunities_discovered")}')
                print(f'  Strategies Scanned: {latest.get("strategies_scanned")}')
                exec_time = latest.get('execution_time_ms')
                if exec_time:
                    print(f'  Execution Time: {exec_time:.2f} ms')
                print(f'  Success: {latest.get("success")}')

                # Check if it matches our scan
                if scan_id in latest.get('scan_id', ''):
                    print(f'\n  *** VERIFIED: This matches our initiated scan! ***')
            else:
                print(f'\nWARNING: No latest scan found in metrics')

            # Daily stats
            daily = data.get('daily_stats')
            if daily:
                stats = daily.get('stats', {})
                print(f'\nDaily Statistics (updated):')
                print(f'  Date: {daily.get("date")}')
                print(f'  Total Scans: {stats.get("total_scans", 0)}')
                print(f'  Successful Scans: {stats.get("successful_scans", 0)}')
                print(f'  Failed Scans: {stats.get("failed_scans", 0)}')
                print(f'  Success Rate: {daily.get("success_rate", 0):.1f}%')
                print(f'  Total Opportunities Found: {stats.get("total_opportunities", 0)}')
                print(f'  Total Strategies Executed: {stats.get("total_strategies", 0)}')
                avg_time = stats.get('avg_execution_time_ms')
                if avg_time:
                    print(f'  Avg Execution Time: {avg_time:.2f} ms')

            # System health
            health = data.get('system_health', {})
            print(f'\nSystem Health:')
            print(f'  Status: {health.get("status", "unknown")}')
            print(f'  Redis Connected: {health.get("redis_connected", False)}')
            print(f'  Daily Errors: {health.get("daily_errors", 0)}')

        # Step 6: Check scan history
        print('\n' + '-'*80)
        print('Step 6: Checking scan history for this user...')
        print('-'*80)

        resp = requests.get(
            f'{BASE_URL}/scan-diagnostics/scan-history/{user_id}',
            headers=headers,
            params={'limit': 5},
            verify=False,
            timeout=15
        )

        if resp.status_code == 200:
            history = resp.json()
            print(f'\nTotal scans found: {history.get("total_scans", 0)}')

            scans = history.get('scans', [])
            if scans:
                print(f'\nRecent scan history:')
                for i, scan in enumerate(scans[:5], 1):
                    print(f'  {i}. Scan ID: {scan.get("scan_id")}')
                    opps = scan.get('opportunities_count') or scan.get('opportunities') or 0
                    print(f'     Opportunities: {opps}')
                    exec_time = scan.get('execution_time_ms')
                    if exec_time:
                        print(f'     Execution Time: {exec_time:.2f} ms')
                    print(f'     Last Updated: {scan.get("last_updated")}')

    else:
        print(f'FAILED to initiate scan: {resp.status_code}')
        print(f'Response: {resp.text}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()

print('\n' + '='*80)
print('DIAGNOSTIC TEST COMPLETED!')
print('='*80)
