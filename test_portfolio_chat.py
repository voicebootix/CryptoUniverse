import requests
import json
import sys

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

def test_portfolio_via_chat(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print('\n=== Testing Portfolio Balance via Chat ===')
    try:
        # Create a new session first
        session_response = requests.post(f'{BASE_URL}/api/v1/chat/session/new', 
                                       json={'session_type': 'trading'}, 
                                       headers=headers, timeout=30, verify=False)
        
        if session_response.status_code != 200:
            print(f'ERROR: Failed to create session: {session_response.status_code}')
            return
            
        session_id = session_response.json().get('session_id')
        print(f'SUCCESS: Created trading session: {session_id}')
        
        # Test portfolio-related messages
        portfolio_messages = [
            "What's my portfolio balance?",
            "Show me my current portfolio",
            "How much money do I have?",
            "What are my current holdings?",
            "Give me a portfolio summary",
            "Show my portfolio value"
        ]
        
        for i, message in enumerate(portfolio_messages, 1):
            print(f'\n--- Test Message {i}: "{message}" ---')
            
            message_response = requests.post(f'{BASE_URL}/api/v1/chat/message', 
                                           json={
                                               'message': message,
                                               'session_id': session_id,
                                               'mode': 'trading'
                                           }, 
                                           headers=headers, timeout=90, verify=False)
            
            if message_response.status_code == 200:
                result = message_response.json()
                print(f'SUCCESS: Portfolio chat message processed')
                
                if 'response' in result:
                    response_text = result['response']
                    print(f'  AI Response Preview: {response_text[:300]}...')
                    
                    # Check for common $0 indicators
                    if '$0' in response_text or '$0.00' in response_text:
                        print(f'  WARNING ISSUE DETECTED: Response contains $0 balance!')
                    elif '$4,028' in response_text or '$4028' in response_text:
                        print(f'  SUCCESS CORRECT: Response shows proper portfolio value!')
                    elif 'balance' in response_text.lower() or 'portfolio' in response_text.lower():
                        print(f'  INFO Portfolio info detected in response')
                
                if 'confidence' in result:
                    print(f'  Confidence: {result["confidence"]}')
                    
                if 'metadata' in result and result['metadata']:
                    print(f'  Metadata keys: {list(result["metadata"].keys())}')
                    
            else:
                print(f'ERROR: Portfolio chat message failed: {message_response.status_code}')
                error_text = message_response.text[:300] if message_response.text else 'No error details'
                print(f'  Error: {error_text}')
                
    except Exception as e:
        print(f'ERROR: Portfolio chat error: {str(e)}')

# Test quick portfolio analysis endpoint
def test_portfolio_quick_analysis(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print('\n=== Testing Quick Portfolio Analysis Endpoint ===')
    try:
        response = requests.post(f'{BASE_URL}/api/v1/chat/portfolio/quick-analysis', 
                               json={}, 
                               headers=headers, timeout=60, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            print(f'SUCCESS: Quick portfolio analysis successful')
            
            if 'analysis' in result:
                analysis_preview = result['analysis'][:200] + '...' if len(result['analysis']) > 200 else result['analysis']
                print(f'  Analysis Preview: {analysis_preview}')
                
                if '$0' in result['analysis']:
                    print(f'  WARNING ISSUE: Analysis shows $0 balance!')
                elif '$4,028' in result['analysis'] or '$4028' in result['analysis']:
                    print(f'  SUCCESS CORRECT: Analysis shows proper portfolio value!')
            
        else:
            print(f'ERROR: Quick portfolio analysis failed: {response.status_code}')
            error_text = response.text[:300] if response.text else 'No error details'
            print(f'  Error: {error_text}')
            
    except Exception as e:
        print(f'ERROR: Quick portfolio analysis error: {str(e)}')

# Main test execution
print('ROCKET Testing Portfolio Balance via Chat Interface...')
token = test_login()

if token:
    test_portfolio_via_chat(token)
    test_portfolio_quick_analysis(token)
    print('\nCHART Portfolio chat testing completed!')
    print('   If responses show $0, there may be an issue with portfolio data integration in chat.')
    print('   The direct API endpoint shows $4,028.90, so the issue is likely in chat processing.')
else:
    print('\nERROR Cannot proceed with tests - login failed')
    sys.exit(1)