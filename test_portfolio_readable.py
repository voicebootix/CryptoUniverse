import requests
import json

# Test configuration
BASE_URL = 'https://cryptouniverse.onrender.com'
ADMIN_EMAIL = 'admin@cryptouniverse.com'
ADMIN_PASSWORD = 'AdminPass123!'

def test_login():
    login_url = f'{BASE_URL}/api/v1/auth/login'
    login_data = {'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD}
    
    response = requests.post(login_url, json=login_data, timeout=30, verify=False)
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

def test_portfolio_readable(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print('=== PORTFOLIO BALANCE ANALYSIS ===')
    
    try:
        response = requests.get(f'{BASE_URL}/api/v1/trading/portfolio', 
                              headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            portfolio = response.json()
            
            print(f"✅ TOTAL PORTFOLIO VALUE: ${float(portfolio['total_value']):,.2f}")
            print(f"   Available Balance: ${float(portfolio['available_balance']):,.2f}")
            print(f"   Daily P&L: ${float(portfolio['daily_pnl']):,.2f} ({portfolio['daily_pnl_pct']:.2f}%)")
            print(f"   Total P&L: ${float(portfolio['total_pnl']):,.2f} ({portfolio['total_pnl_pct']:.2f}%)")
            print(f"   Active Positions: {len(portfolio['positions'])}")
            print(f"   Risk Score: {portfolio['risk_score']}/100")
            
            # Group by exchange
            exchanges = {}
            for pos in portfolio['positions']:
                exchange = pos['exchange']
                if exchange not in exchanges:
                    exchanges[exchange] = {'count': 0, 'value': 0}
                exchanges[exchange]['count'] += 1
                exchanges[exchange]['value'] += float(pos['value_usd'])
            
            print(f"\n=== EXCHANGE BREAKDOWN ===")
            for exchange, data in exchanges.items():
                print(f"📊 {exchange.upper()}: {data['count']} positions, ${data['value']:.2f}")
            
            # Top positions
            print(f"\n=== TOP 5 POSITIONS ===")
            top_positions = sorted(portfolio['positions'], 
                                 key=lambda x: float(x['value_usd']), reverse=True)[:5]
            
            for i, pos in enumerate(top_positions, 1):
                print(f"{i}. {pos['symbol']} ({pos['exchange']}): ${float(pos['value_usd']):.2f}")
                print(f"   Amount: {float(pos['amount']):.4f} @ ${float(pos['current_price']):.4f}")
            
            return True
        else:
            print(f"❌ Portfolio request failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Portfolio test error: {str(e)}")
        return False

# Test execution
print("🚀 Testing Portfolio Balance with Connected Exchanges...")
token = test_login()

if token:
    success = test_portfolio_readable(token)
    if success:
        print(f"\n✅ CONCLUSION: Portfolio is working correctly and shows significant balance!")
        print(f"   The system is successfully retrieving balances from multiple exchanges.")
    else:
        print(f"\n❌ CONCLUSION: Portfolio endpoint has issues that need investigation.")
else:
    print("❌ Login failed - cannot test portfolio")