#!/usr/bin/env python3
"""
Debug the deployed fix to see exactly what's happening
"""

import requests
import json
import time

BASE_URL = "https://cryptouniverse.onrender.com"

def test_deployed_fix():
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
    
    # Test with a simple rebalancing question
    print("🔍 Testing deployed fix with simple rebalancing question...")
    
    message = "Do I need to rebalance?"
    payload = {"message": message, "session_id": session_id}
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/v1/chat/message", headers=headers, json=payload, timeout=90)
        response_time = time.time() - start_time
        
        print(f"⏱️ Response time: {response_time:.1f}s")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Response received")
            print(f"🎯 Intent: {data.get('intent')}")
            print(f"📊 Confidence: {data.get('confidence')}")
            
            # Check metadata
            metadata = data.get('metadata', {})
            
            # Portfolio data
            portfolio_data = metadata.get('portfolio_data', {})
            print(f"\n📊 PORTFOLIO DATA IN RESPONSE:")
            print(f"   Value: ${portfolio_data.get('total_value', 0):,.2f}")
            print(f"   Positions: {len(portfolio_data.get('positions', []))}")
            if portfolio_data.get('positions'):
                assets = [pos.get('symbol') for pos in portfolio_data.get('positions', [])]
                print(f"   Assets: {assets}")
            
            # Rebalancing analysis
            rebalance_analysis = metadata.get('rebalance_analysis', {})
            print(f"\n⚖️ REBALANCING ANALYSIS:")
            print(f"   Needs Rebalancing: {rebalance_analysis.get('needs_rebalancing', 'Unknown')}")
            print(f"   Recommended Trades: {len(rebalance_analysis.get('recommended_trades', []))}")
            
            if rebalance_analysis.get('recommended_trades'):
                trades = rebalance_analysis.get('recommended_trades', [])
                trade_assets = [trade.get('symbol') for trade in trades[:3]]
                print(f"   Trade Assets: {trade_assets}")
            
            # Check for errors
            if 'error' in rebalance_analysis:
                print(f"❌ Rebalancing Error: {rebalance_analysis['error']}")
            
            # Show response content (truncated)
            content = data.get('content', '')
            print(f"\n💬 RESPONSE CONTENT (first 200 chars):")
            print(f"   {content[:200]}...")
            
            return True
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_deployed_fix()