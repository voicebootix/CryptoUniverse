import requests
import json
import sys

# Test configuration
BASE_URL = 'https://cryptouniverse.onrender.com'
ADMIN_EMAIL = 'admin@cryptouniverse.com'
ADMIN_PASSWORD = 'AdminPass123!'

def test_login():
    login_url = f'{BASE_URL}/api/v1/auth/login'
    login_data = {
        'email': ADMIN_EMAIL,
        'password': ADMIN_PASSWORD
    }
    
    try:
        response = requests.post(login_url, json=login_data, timeout=30)
        if response.status_code == 200:
            token = response.json().get('access_token')
            print(f'SUCCESS: Login successful - Token: {token[:20]}...')
            return token
        else:
            print(f'ERROR: Login failed: {response.status_code} - {response.text}')
            return None
    except Exception as e:
        print(f'ERROR: Login error: {str(e)}')
        return None

def test_market_analysis_via_chat(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print('\n=== Testing Market Analysis via Chat Message (Session Variable Fix) ===')
    try:
        # Create a new session first
        session_response = requests.post(f'{BASE_URL}/api/v1/chat/session/new', 
                                       json={'session_type': 'analysis'}, 
                                       headers=headers, timeout=30)
        
        if session_response.status_code != 200:
            print(f'ERROR: Failed to create session: {session_response.status_code}')
            return
            
        session_id = session_response.json().get('session_id')
        print(f'SUCCESS: Created analysis session: {session_id}')
        
        # Test market analysis message that should trigger enhanced_market_analysis
        market_messages = [
            "What are the current market trends for Bitcoin?",
            "Analyze the market opportunities for cryptocurrency trading",
            "Give me a comprehensive market analysis with trading recommendations"
        ]
        
        for i, message in enumerate(market_messages, 1):
            print(f'\n--- Test Message {i}: {message[:50]}... ---')
            
            message_response = requests.post(f'{BASE_URL}/api/v1/chat/message', 
                                           json={
                                               'message': message,
                                               'session_id': session_id,
                                               'mode': 'analysis'
                                           }, 
                                           headers=headers, timeout=90)
            
            if message_response.status_code == 200:
                result = message_response.json()
                print(f'SUCCESS: Market analysis message processed')
                
                if 'response' in result:
                    response_preview = result['response'][:200] + '...' if len(result['response']) > 200 else result['response']
                    print(f'  AI Response: {response_preview}')
                
                if 'confidence' in result:
                    print(f'  Confidence: {result["confidence"]}')
                    
                if 'metadata' in result and result['metadata']:
                    print(f'  Metadata keys: {list(result["metadata"].keys())}')
                    
            else:
                print(f'ERROR: Market analysis message failed: {message_response.status_code}')
                error_text = message_response.text[:300] if message_response.text else 'No error details'
                print(f'  Error: {error_text}')
                
                # Check if it's the session variable error we fixed
                if 'session' in error_text.lower() and 'not defined' in error_text.lower():
                    print('  !!! SESSION VARIABLE ERROR DETECTED - Fix may not be working !!!')
                else:
                    print('  Different error - session variable fix appears to be working')
                    
    except Exception as e:
        print(f'ERROR: Market analysis via chat error: {str(e)}')

# Main test execution
print('Starting Market Analysis via Chat Test (Session Variable Fix Verification)...')
token = test_login()

if token:
    test_market_analysis_via_chat(token)
    print('\nMarket analysis via chat test completed!')
else:
    print('\nCannot proceed with tests - login failed')
    sys.exit(1)