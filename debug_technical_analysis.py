#!/usr/bin/env python3
"""
Debug what technical analysis is actually returning
"""

import requests
import json

def test_technical_analysis_direct():
    """Test technical analysis directly to see what data structure it returns"""
    
    base_url = "https://cryptouniverse.onrender.com/api/v1"
    
    # Login
    login_data = {
        "email": "admin@cryptouniverse.com", 
        "password": "AdminPass123!"
    }
    
    response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=30)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 Testing technical analysis endpoint directly...")
    
    # Test technical analysis endpoint
    response = requests.post(f"{base_url}/market/technical-analysis", 
                           json={
                               "symbols": "BTC,ETH,SOL",
                               "timeframe": "1h",
                               "indicators": "sma,ema,rsi,macd"
                           },
                           headers=headers, 
                           timeout=60)
    
    print(f"📡 Technical Analysis Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"✅ Technical Analysis Response:")
        print(f"   Success: {data.get('success')}")
        
        if data.get('success'):
            # Check the actual structure
            analysis_data = data.get('data', {})
            print(f"\n📊 Data Structure Analysis:")
            print(f"   Top-level keys: {list(analysis_data.keys())}")
            
            # Check each symbol's data
            for symbol, symbol_data in analysis_data.items():
                print(f"\n   {symbol} data structure:")
                if isinstance(symbol_data, dict):
                    print(f"      Keys: {list(symbol_data.keys())}")
                    
                    # Check if signals exist
                    signals = symbol_data.get('signals', {})
                    if signals:
                        print(f"      Signals: {signals}")
                        buy_signals = signals.get('buy', 0)
                        sell_signals = signals.get('sell', 0)
                        print(f"      Buy signals: {buy_signals}, Sell signals: {sell_signals}")
                        
                        if buy_signals > sell_signals:
                            print(f"      ✅ This should create an opportunity!")
                        else:
                            print(f"      ❌ Not enough buy signals for opportunity")
                    else:
                        print(f"      ❌ No signals found in data")
                        
                    # Show full structure for first symbol
                    if symbol == list(analysis_data.keys())[0]:
                        print(f"\n   Full {symbol} data:")
                        print(json.dumps(symbol_data, indent=4))
                else:
                    print(f"      ❌ Symbol data is not a dict: {type(symbol_data)}")
        else:
            print(f"   ❌ Technical analysis failed: {data.get('error')}")
    else:
        print(f"❌ Technical Analysis Error: {response.status_code}")
        print(f"   Response: {response.text}")

def test_chat_adapters_method():
    """Test what the chat adapters get_technical_analysis method returns"""
    
    base_url = "https://cryptouniverse.onrender.com/api/v1"
    
    # Login
    login_data = {
        "email": "admin@cryptouniverse.com", 
        "password": "AdminPass123!"
    }
    
    response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=30)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n🔍 Testing what discover_opportunities actually receives...")
    
    # Create a test message that will trigger opportunity discovery
    message_data = {
        "message": "Find me trading opportunities",
        "mode": "trading"
    }
    
    response = requests.post(f"{base_url}/chat/message", 
                           json=message_data, 
                           headers=headers, 
                           timeout=120)
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get('metadata', {})
        
        # Look for any debug info or error messages
        print(f"📊 Chat Response Metadata:")
        print(json.dumps(metadata, indent=2))
        
        # Check if there are any error messages in the content
        content = data.get('content', '')
        if 'error' in content.lower() or 'failed' in content.lower():
            print(f"\n⚠️ Possible error in content: {content[:300]}...")

def main():
    """Run both tests"""
    print("🚀 DEBUGGING TECHNICAL ANALYSIS DATA STRUCTURE")
    print("="*60)
    
    # Test technical analysis directly
    test_technical_analysis_direct()
    
    # Test what chat system receives
    test_chat_adapters_method()
    
    print(f"\n{'='*60}")
    print("🔍 DIAGNOSIS:")
    print("If technical analysis returns proper signals but opportunities aren't found,")
    print("then the issue is in the discover_opportunities logic.")
    print("If technical analysis doesn't return signals, that's the root cause.")

if __name__ == "__main__":
    main()