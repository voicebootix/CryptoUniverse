import requests
import urllib3
import time
urllib3.disable_warnings()

BASE_URL = 'https://cryptouniverse.onrender.com/api/v1'

resp = requests.post(f'{BASE_URL}/auth/login', json={'email': 'admin@cryptouniverse.com', 'password': 'AdminPass123!'}, verify=False, timeout=15)
token = resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

resp = requests.post(f'{BASE_URL}/opportunities/discover', json={'force_refresh': True}, headers=headers, verify=False, timeout=15)
scan_id = resp.json().get('scan_id')
print(f'Scan initiated: {scan_id}')

time.sleep(20)

try:
    resp = requests.get(f'{BASE_URL}/scan-diagnostics/scan-lifecycle/{scan_id}', headers=headers, verify=False, timeout=30)
    print(f'Status: {resp.status_code}')
    print(resp.text[:500])
except Exception as e:
    print(f'Error: {e}')
