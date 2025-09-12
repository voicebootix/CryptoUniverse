import asyncio
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

def test_market_analysis_endpoints(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print('\n=== TESTING MARKET ANALYSIS ENDPOINTS ===')
    
    # Test technical analysis endpoint
    print('\n1. Testing Technical Analysis Endpoint...')
    try:
        response = requests.post(f'{BASE_URL}/api/v1/market-analysis/technical-analysis', 
                               json={'symbols': 'BTC,ETH,SOL', 'timeframe': '1h'}, 
                               headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            print(f'   SUCCESS: Technical analysis returned')
            if 'analysis' in result:
                print(f'   Analysis keys: {list(result.get("analysis", {}).keys())}')
            else:
                print(f'   Result keys: {list(result.keys())}')
        else:
            print(f'   ERROR: Technical analysis failed: {response.status_code}')
            print(f'   Error: {response.text[:300]}')
            
    except Exception as e:
        print(f'   ERROR: Technical analysis exception: {str(e)}')
    
    # Test market sentiment endpoint
    print('\n2. Testing Market Sentiment Endpoint...')
    try:
        response = requests.post(f'{BASE_URL}/api/v1/market-analysis/sentiment-analysis', 
                               json={'symbols': 'BTC,ETH,SOL'}, 
                               headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            print(f'   SUCCESS: Market sentiment returned')
            print(f'   Result keys: {list(result.keys())}')
        else:
            print(f'   ERROR: Market sentiment failed: {response.status_code}')
            print(f'   Error: {response.text[:300]}')
            
    except Exception as e:
        print(f'   ERROR: Market sentiment exception: {str(e)}')
    
    # Test arbitrage opportunities endpoint
    print('\n3. Testing Arbitrage Opportunities Endpoint...')
    try:
        response = requests.post(f'{BASE_URL}/api/v1/market-analysis/arbitrage-opportunities', 
                               json={'symbols': 'BTC,ETH,SOL', 'exchanges': 'binance,kucoin'}, 
                               headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            print(f'   SUCCESS: Arbitrage opportunities returned')
            if 'opportunities' in result:
                opportunities = result.get('opportunities', [])
                print(f'   Found {len(opportunities)} arbitrage opportunities')
                if opportunities:
                    print(f'   Sample opportunity: {opportunities[0]}')
            else:
                print(f'   Result keys: {list(result.keys())}')
        else:
            print(f'   ERROR: Arbitrage opportunities failed: {response.status_code}')
            print(f'   Error: {response.text[:300]}')
            
    except Exception as e:
        print(f'   ERROR: Arbitrage opportunities exception: {str(e)}')

def test_chat_market_questions(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print('\n=== TESTING MARKET ANALYSIS VIA CHAT ===')
    
    # Create a session first
    session_response = requests.post(f'{BASE_URL}/api/v1/chat/session/new', 
                                   json={'session_type': 'analysis'}, 
                                   headers=headers, timeout=30, verify=False)
    
    if session_response.status_code != 200:
        print(f'ERROR: Failed to create session: {session_response.status_code}')
        return
        
    session_id = session_response.json().get('session_id')
    print(f'SUCCESS: Created analysis session: {session_id}')
    
    market_questions = [
        "What's the current market sentiment?",
        "Find me some trading opportunities",
        "What are the best coins to buy right now?",
        "Show me technical analysis for BTC"
    ]
    
    for i, question in enumerate(market_questions, 1):
        print(f'\n--- Question {i}: "{question}" ---')
        
        try:
            message_response = requests.post(f'{BASE_URL}/api/v1/chat/message', 
                                           json={
                                               'message': question,
                                               'session_id': session_id,
                                               'mode': 'analysis'
                                           }, 
                                           headers=headers, timeout=60, verify=False)
            
            if message_response.status_code == 200:
                result = message_response.json()
                print(f'   SUCCESS: Chat response received')
                
                if 'response' in result:
                    response_text = result['response'][:200] + '...' if len(result['response']) > 200 else result['response']
                    print(f'   Response: {response_text}')
                    
                    # Check for zero opportunities
                    if 'no opportunities' in response_text.lower() or '0 opportunities' in response_text.lower():
                        print(f'   WARNING: Response indicates zero opportunities found')
                        
                if 'metadata' in result and 'error' in result['metadata']:
                    print(f'   WARNING: Metadata contains error: {result["metadata"]["error"]}')
                    
            else:
                print(f'   ERROR: Chat message failed: {message_response.status_code}')
                print(f'   Error: {message_response.text[:200]}')
                
        except Exception as e:
            print(f'   ERROR: Chat question exception: {str(e)}')

# Main execution
print('TESTING MARKET ANALYSIS SERVICES AND CHAT INTEGRATION...')
token = test_login()

if token:
    test_market_analysis_endpoints(token)
    test_chat_market_questions(token)
    print('\nMARKET ANALYSIS TESTING COMPLETED!')
    print('\nSUMMARY:')
    print('- If endpoints work but chat shows zero opportunities, the adaptor has issues')
    print('- If endpoints fail, the underlying market analysis service has problems')
else:
    print('\nERROR: Cannot proceed with tests - login failed')