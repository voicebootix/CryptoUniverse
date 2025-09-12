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

def test_portfolio_chat_content(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print('\n=== PORTFOLIO CHAT CONTENT TEST ===')
    
    # Create session
    session_response = requests.post(f'{BASE_URL}/api/v1/chat/session/new', 
                                   json={'session_type': 'trading'}, 
                                   headers=headers, timeout=30, verify=False)
    
    if session_response.status_code != 200:
        print(f'ERROR: Failed to create session: {session_response.status_code}')
        return
        
    session_id = session_response.json().get('session_id')
    
    # Test portfolio question
    print('\n--- Testing: "What is my portfolio balance?" ---')
    try:
        message_response = requests.post(f'{BASE_URL}/api/v1/chat/message', 
                                       json={
                                           'message': 'What is my portfolio balance?',
                                           'session_id': session_id,
                                           'mode': 'trading'
                                       }, 
                                       headers=headers, timeout=60, verify=False)
        
        if message_response.status_code == 200:
            result = message_response.json()
            print(f'SUCCESS: Portfolio response received')
            
            if 'response' in result:
                response_text = result['response']
                print(f'\n=== PORTFOLIO RESPONSE ===')
                print(response_text)
                print(f'===========================\n')
                
                # Check for key indicators
                if '$4,028' in response_text or '$4028' in response_text:
                    print(f'SUCCESS: Shows correct portfolio value $4,028.90!')
                elif '$0' in response_text or '$0.00' in response_text:
                    print(f'WARNING: Still showing $0 balance issue')
                elif '$' in response_text:
                    print(f'INFO: Shows dollar amounts - check if correct')
                else:
                    print(f'INFO: No dollar amounts detected')
                    
            if 'confidence' in result:
                print(f'Confidence: {result["confidence"]}')
                
        else:
            print(f'ERROR: Portfolio chat failed: {message_response.status_code}')
            print(f'Error: {message_response.text[:300]}')
            
    except Exception as e:
        print(f'ERROR: Portfolio chat exception: {str(e)}')

def test_market_chat_content(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print('\n=== MARKET ANALYSIS CHAT CONTENT TEST ===')
    
    # Create session
    session_response = requests.post(f'{BASE_URL}/api/v1/chat/session/new', 
                                   json={'session_type': 'analysis'}, 
                                   headers=headers, timeout=30, verify=False)
    
    if session_response.status_code != 200:
        print(f'ERROR: Failed to create session: {session_response.status_code}')
        return
        
    session_id = session_response.json().get('session_id')
    
    # Test market question
    print('\n--- Testing: "Find me trading opportunities" ---')
    try:
        message_response = requests.post(f'{BASE_URL}/api/v1/chat/message', 
                                       json={
                                           'message': 'Find me trading opportunities',
                                           'session_id': session_id,
                                           'mode': 'analysis'
                                       }, 
                                       headers=headers, timeout=60, verify=False)
        
        if message_response.status_code == 200:
            result = message_response.json()
            print(f'SUCCESS: Market opportunities response received')
            
            if 'response' in result:
                response_text = result['response']
                print(f'\n=== MARKET OPPORTUNITIES RESPONSE ===')
                print(response_text)
                print(f'====================================\n')
                
                # Check for opportunities
                if 'no opportunities' in response_text.lower() or '0 opportunities' in response_text.lower():
                    print(f'WARNING: Still showing zero opportunities')
                elif 'opportunity' in response_text.lower() or 'buy' in response_text.lower():
                    print(f'SUCCESS: Shows trading opportunities!')
                else:
                    print(f'INFO: Check content for market data')
                    
            if 'confidence' in result:
                print(f'Confidence: {result["confidence"]}')
                
        else:
            print(f'ERROR: Market chat failed: {message_response.status_code}')
            print(f'Error: {message_response.text[:300]}')
            
    except Exception as e:
        print(f'ERROR: Market chat exception: {str(e)}')

# Main execution
print('TESTING CHAT CONTENT AFTER DEPLOYMENT...')
token = test_login()

if token:
    test_portfolio_chat_content(token)
    test_market_chat_content(token)
    print('\nCHAT CONTENT TESTING COMPLETED!')
    print('\nSUMMARY:')
    print('- Check if portfolio shows $4,028.90 instead of $0')
    print('- Check if market analysis shows opportunities instead of empty results')
else:
    print('\nERROR: Cannot proceed with tests - login failed')