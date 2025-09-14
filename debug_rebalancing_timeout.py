#!/usr/bin/env python3
"""
Debug Rebalancing Timeout Issue
Quick test to get rebalancing data without timeout
"""

import requests
import json
import time

BASE_URL = "https://cryptouniverse.onrender.com"

def test_rebalancing_quick():
    # Login
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "admin@cryptouniverse.com", "password": "AdminPass123!"},
        timeout=30
    )
    
    if response.status_code != 200:
        print("Login failed")
        return
    
    auth_token = response.json().get("access_token")
    
    # Create session
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    response = requests.post(f"{BASE_URL}/api/v1/chat/session/new", headers=headers, json={}, timeout=30)
    
    if response.status_code != 200:
        print("Session creation failed")
        return
    
    session_id = response.json().get("session_id")
    
    # Quick rebalancing test
    print("Testing rebalancing with shorter timeout...")
    
    rebalance_message = "Should I rebalance my portfolio?"
    payload = {"message": rebalance_message, "session_id": session_id}
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/v1/chat/message", headers=headers, json=payload, timeout=45)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            metadata = data.get('metadata', {})
            
            print(f"✅ Success ({response_time:.1f}s)")
            
            # Extract key data
            rebalance_analysis = metadata.get('rebalance_analysis', {})
            portfolio_data = metadata.get('portfolio_data', {})
            
            print(f"\n📊 REBALANCING SYSTEM DATA:")
            print(f"   Portfolio Value: ${portfolio_data.get('total_value', 0):,.2f}")
            print(f"   Positions Count: {len(portfolio_data.get('positions', []))}")
            print(f"   Data Source: {portfolio_data.get('data_source', 'Unknown')}")
            
            positions = portfolio_data.get('positions', [])
            print(f"   Assets: {[pos.get('symbol') for pos in positions[:10]]}")
            
            # Check recommended trades
            recommended_trades = rebalance_analysis.get('recommended_trades', [])
            print(f"   Recommended Trades: {len(recommended_trades)}")
            if recommended_trades:
                trade_symbols = [trade.get('symbol') for trade in recommended_trades[:5]]
                print(f"   Trade Assets: {trade_symbols}")
            
            return {
                'portfolio_data': portfolio_data,
                'recommended_trades': recommended_trades
            }
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    result = test_rebalancing_quick()