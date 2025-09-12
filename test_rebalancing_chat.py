import requests
import json

# Test configuration
BASE_URL = 'https://cryptouniverse.onrender.com'
ADMIN_EMAIL = 'admin@cryptouniverse.com'
ADMIN_PASSWORD = 'AdminPass123!'

def test_login():
    login_url = f'{BASE_URL}/api/v1/auth/login'
    login_data = {'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD}
    
    try:
        response = requests.post(login_url, json=login_data, timeout=30, verify=False)
        if response.status_code == 200:
            token = response.json().get('access_token')
            print(f'SUCCESS: Login successful')
            return token
        else:
            print(f'ERROR: Login failed: {response.status_code}')
            return None
    except Exception as e:
        print(f'ERROR: Login error: {str(e)}')
        return None

def test_rebalancing_chat(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print('\nTESTING PORTFOLIO REBALANCING VIA CHAT...\n')
    
    # Create trading session
    session_response = requests.post(f'{BASE_URL}/api/v1/chat/session/new', 
                                   json={'session_type': 'trading'}, 
                                   headers=headers, timeout=30, verify=False)
    
    if session_response.status_code != 200:
        print(f'ERROR: Failed to create session: {session_response.status_code}')
        return
        
    session_id = session_response.json().get('session_id')
    print(f'SUCCESS: Trading session created: {session_id}')
    
    # Test rebalancing requests
    rebalancing_tests = [
        "Please rebalance my portfolio using risk parity strategy",
        "I want to rebalance using equal weight allocation", 
        "Can you rebalance my portfolio to minimize risk?",
        "What is my current portfolio balance and can you suggest rebalancing?"
    ]
    
    for i, test_message in enumerate(rebalancing_tests, 1):
        print(f'\n--- TEST {i}: "{test_message}" ---')
        
        try:
            message_response = requests.post(f'{BASE_URL}/api/v1/chat/message', 
                                           json={
                                               'message': test_message,
                                               'session_id': session_id,
                                               'mode': 'trading'
                                           }, 
                                           headers=headers, timeout=60, verify=False)
            
            if message_response.status_code == 200:
                result = message_response.json()
                print(f'SUCCESS: Response received (Confidence: {result.get("confidence", "N/A")})')
                print(f'DEBUG: Response keys: {list(result.keys())}')
                
                if 'response' in result:
                    response_text = result['response']
                    print(f'\nFULL CHAT RESPONSE:')
                    print('=' * 60)
                    print(response_text)
                    print('=' * 60)
                else:
                    print(f'DEBUG: Full response: {json.dumps(result, indent=2)}')
                
                # Check for rebalancing indicators in any response field
                response_text = result.get('response', str(result))
                if any(word in response_text.lower() for word in ['rebalance', 'allocation', 'portfolio', 'strategy']):
                    print(f'SUCCESS: REBALANCING DETECTED - Chat understands rebalancing request')
                else:
                    print(f'WARNING: NO REBALANCING - Chat may not recognize rebalancing intent')
                    
                if any(word in response_text.lower() for word in ['risk', 'equal', 'weight', 'sharpe', 'variance']):
                    print(f'SUCCESS: STRATEGY DETECTION - Chat recognizes strategy types')
                
                if '$' in response_text:
                    print(f'SUCCESS: PORTFOLIO VALUES - Shows dollar amounts')
                    
            else:
                print(f'ERROR: Chat failed: {message_response.status_code}')
                print(f'Error: {message_response.text[:300]}')
                
        except Exception as e:
            print(f'ERROR: Exception: {str(e)}')
        
        print('\n' + '-' * 80)

# Main execution
print('TESTING CHAT-BASED PORTFOLIO REBALANCING...\n')
token = test_login()

if token:
    test_rebalancing_chat(token)
    print('\nREBALANCING CHAT TESTING COMPLETED!')
else:
    print('\nCannot proceed - login failed')