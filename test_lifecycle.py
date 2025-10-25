"""
Test the new scan lifecycle diagnostic endpoint
"""
import requests
import json
import urllib3
urllib3.disable_warnings()

BASE_URL = 'https://cryptouniverse.onrender.com/api/v1'
ADMIN_EMAIL = 'admin@cryptouniverse.com'
ADMIN_PASSWORD = 'AdminPass123!'

print('='*80)
print('LIFECYCLE DIAGNOSTIC ENDPOINT TEST')
print('='*80)

# Step 1: Authenticate
print('\nStep 1: Authenticating...')
resp = requests.post(
    f'{BASE_URL}/auth/login',
    json={'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD},
    verify=False,
    timeout=15
)
token = resp.json()['access_token']
user_id = resp.json()['user_id']
headers = {'Authorization': f'Bearer {token}'}
print(f'OK - User ID: {user_id}')

# Step 2: Initiate a scan
print('\nStep 2: Initiating opportunity scan...')
resp = requests.post(
    f'{BASE_URL}/opportunities/discover',
    json={'force_refresh': True},
    headers=headers,
    verify=False,
    timeout=15
)

if resp.status_code == 200:
    scan_data = resp.json()
    scan_id = scan_data.get('scan_id')
    print(f'OK - Scan ID: {scan_id}')

    import time
    time.sleep(10)  # Wait for scan to start processing

    # Step 3: Check lifecycle data
    print('\nStep 3: Checking scan lifecycle...')
    resp = requests.get(
        f'{BASE_URL}/scan-diagnostics/scan-lifecycle/{scan_id}',
        headers=headers,
        verify=False,
        timeout=15
    )

    print(f'Status Code: {resp.status_code}')

    if resp.status_code == 200:
        data = resp.json()
        print('\n' + '-'*80)
        print('LIFECYCLE DATA:')
        print('-'*80)
        print(json.dumps(data, indent=2))
    elif resp.status_code == 404:
        print('ERROR: No lifecycle data found!')
        print('This means lifecycle tracking is NOT working in production')
        print(f'Response: {resp.text}')
    else:
        print(f'ERROR {resp.status_code}: {resp.text}')
else:
    print(f'FAILED to initiate scan: {resp.status_code}')
    print(resp.text)

print('\n' + '='*80)
