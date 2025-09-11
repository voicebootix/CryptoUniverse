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

def test_chat_endpoints(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # Test 1: Create chat session
    print('\n=== Testing Chat Session Creation ===')
    try:
        response = requests.post(f'{BASE_URL}/api/v1/chat/session/new', 
                               json={'session_type': 'general'}, 
                               headers=headers, timeout=30)
        if response.status_code == 200:
            session_id = response.json().get('session_id')
            print(f'SUCCESS: Chat session created: {session_id}')
            
            # Test 2: Send message to session
            print('\n=== Testing Message Sending ===')
            message_response = requests.post(f'{BASE_URL}/api/v1/chat/message', 
                                           json={
                                               'message': 'Hello, test message for verification',
                                               'session_id': session_id,
                                               'mode': 'trading'
                                           }, 
                                           headers=headers, timeout=30)
            
            if message_response.status_code == 200:
                msg_result = message_response.json()
                print(f'SUCCESS: Message sent successfully')
                if 'response' in msg_result:
                    print(f'  AI Response: {msg_result["response"][:100]}...')
                
                # Test 3: Get session messages
                print('\n=== Testing Message Retrieval ===')
                messages_response = requests.get(f'{BASE_URL}/api/v1/chat/history/{session_id}', 
                                               headers=headers, timeout=30)
                
                if messages_response.status_code == 200:
                    messages = messages_response.json()
                    print(f'SUCCESS: Messages retrieved: {len(messages.get("messages", []))} messages')
                else:
                    print(f'ERROR: Message retrieval failed: {messages_response.status_code}')
            else:
                print(f'ERROR: Message sending failed: {message_response.status_code} - {message_response.text[:200]}')
                
        else:
            print(f'ERROR: Session creation failed: {response.status_code} - {response.text[:200]}')
            
    except Exception as e:
        print(f'ERROR: Chat endpoint error: {str(e)}')

def test_market_analysis(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print('\n=== Testing Market Analysis (Session Variable Fix) ===')
    try:
        response = requests.post(f'{BASE_URL}/api/v1/chat/market/opportunities', 
                               json={
                                   'risk_tolerance': 'balanced'
                               }, 
                               headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print(f'SUCCESS: Market analysis successful')
            print(f'  Analysis type: {result.get("analysis_type", "N/A")}')
            if 'analysis' in result and result['analysis']:
                analysis_preview = result['analysis'][:100] + '...' if len(result['analysis']) > 100 else result['analysis']
                print(f'  Preview: {analysis_preview}')
            elif 'opportunities' in result:
                print(f'  Found {len(result["opportunities"])} opportunities')
        else:
            print(f'ERROR: Market analysis failed: {response.status_code}')
            error_text = response.text[:500] if response.text else 'No error details'
            print(f'  Error: {error_text}')
            
    except Exception as e:
        print(f'ERROR: Market analysis error: {str(e)}')

def test_user_sessions(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print('\n=== Testing User Sessions Retrieval ===')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/chat/sessions', 
                               headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, dict) and 'sessions' in result:
                sessions = result['sessions']
                print(f'SUCCESS: User sessions retrieved: {len(sessions)} sessions')
                for i, session in enumerate(sessions[:2]):  # Show first 2 sessions
                    if isinstance(session, dict):
                        print(f'  - Session {session.get("session_id", "N/A")} ({session.get("session_type", "N/A")})')
                    else:
                        print(f'  - Session: {session}')
            else:
                sessions = result if isinstance(result, list) else [result]
                print(f'SUCCESS: User sessions retrieved: {len(sessions)} sessions')
                for session in sessions[:2]:
                    print(f'  - Session: {session}')
        else:
            print(f'ERROR: User sessions failed: {response.status_code} - {response.text[:200]}')
            
    except Exception as e:
        print(f'ERROR: User sessions error: {str(e)}')

# Main test execution
print('Starting Chat Endpoints Verification...')
token = test_login()

if token:
    test_chat_endpoints(token)
    test_market_analysis(token)  # This should verify the session variable fix
    test_user_sessions(token)
    print('\nChat endpoint verification completed!')
else:
    print('\nCannot proceed with tests - login failed')
    sys.exit(1)