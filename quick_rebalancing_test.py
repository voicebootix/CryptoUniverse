import requests
import json

BASE_URL = 'https://cryptouniverse.onrender.com'
ADMIN_EMAIL = 'admin@cryptouniverse.com'
ADMIN_PASSWORD = 'AdminPass123!'

# Login
login_response = requests.post(f'{BASE_URL}/api/v1/auth/login', 
                             json={'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD}, 
                             timeout=30, verify=False)

if login_response.status_code != 200:
    print(f'Login failed: {login_response.status_code}')
    exit()

token = login_response.json().get('access_token')
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

print('=== TESTING REBALANCING CHAT ===\n')

# Create session
session_response = requests.post(f'{BASE_URL}/api/v1/chat/session/new', 
                               json={'session_type': 'trading'}, 
                               headers=headers, timeout=30, verify=False)

session_id = session_response.json().get('session_id')
print(f'Session ID: {session_id}')

# Test one simple rebalancing request
print('\nSending: "Can you rebalance my portfolio with equal weight strategy?"')

try:
    message_response = requests.post(f'{BASE_URL}/api/v1/chat/message', 
                                   json={
                                       'message': 'Can you rebalance my portfolio with equal weight strategy?',
                                       'session_id': session_id,
                                       'mode': 'trading'
                                   }, 
                                   headers=headers, timeout=45, verify=False)
    
    print(f'Status: {message_response.status_code}')
    
    if message_response.status_code == 200:
        result = message_response.json()
        print(f'Response keys: {list(result.keys())}')
        
        # Print full response structure
        print('\n=== FULL RESPONSE STRUCTURE ===')
        print(json.dumps(result, indent=2))
        
        # Check for actual content
        if 'response' in result and result['response']:
            print('\n=== CHAT RESPONSE CONTENT ===')
            print(result['response'])
        elif 'message' in result:
            print('\n=== CHAT MESSAGE CONTENT ===') 
            print(result['message'])
        else:
            print('\n=== RAW RESPONSE ===')
            print(result)
            
    else:
        print(f'Error: {message_response.text}')
        
except Exception as e:
    print(f'Exception: {str(e)}')

print('\n=== END TEST ===')