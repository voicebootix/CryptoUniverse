"""
Test if admin user has strategies in portfolio
"""
import requests
import json
import urllib3
urllib3.disable_warnings()

BASE_URL = 'https://cryptouniverse.onrender.com/api/v1'
ADMIN_EMAIL = 'admin@cryptouniverse.com'
ADMIN_PASSWORD = 'AdminPass123!'

print('='*80)
print('CHECKING ADMIN PORTFOLIO')
print('='*80)

# Authenticate
resp = requests.post(
    f'{BASE_URL}/auth/login',
    json={'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD},
    verify=False,
    timeout=15
)
token = resp.json()['access_token']
user_id = resp.json()['user_id']
headers = {'Authorization': f'Bearer {token}'}
print(f'Authenticated as: {user_id}')

# Get portfolio
print('\nChecking portfolio...')
resp = requests.get(
    f'{BASE_URL}/portfolio',
    headers=headers,
    verify=False,
    timeout=15
)

if resp.status_code == 200:
    portfolio = resp.json()
    print(f'\n{json.dumps(portfolio, indent=2)}')

    active_strategies = portfolio.get('active_strategies', [])
    print(f'\n\nActive Strategies Count: {len(active_strategies)}')

    if len(active_strategies) == 0:
        print('\n❌ NO ACTIVE STRATEGIES FOUND!')
        print('This is why scans fail - the user has no strategies to scan.')
        print('The scan exits early with "NO STRATEGIES FOUND" before lifecycle tracking starts.')
    else:
        print(f'\n✅ User has {len(active_strategies)} active strategies')
        for strategy in active_strategies[:5]:
            print(f'  - {strategy.get("strategy_name")} ({strategy.get("strategy_id")})')
else:
    print(f'ERROR: {resp.status_code}')
    print(resp.text)
