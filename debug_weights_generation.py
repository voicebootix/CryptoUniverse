#!/usr/bin/env python3
"""
Debug Weights Generation
Tests what weights the optimization engine is actually producing
"""

import requests
import json
import time

BASE_URL = "https://cryptouniverse.onrender.com"

def debug_weights():
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
    
    # Test rebalancing with detailed logging
    print("🔍 Testing rebalancing to debug weights generation...")
    
    message = "Rebalance my portfolio using adaptive strategy"
    payload = {"message": message, "session_id": session_id}
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/chat/message", headers=headers, json=payload, timeout=90)
        
        if response.status_code == 200:
            data = response.json()
            metadata = data.get('metadata', {})
            
            print("✅ Response received")
            
            # Check portfolio data
            portfolio_data = metadata.get('portfolio_data', {})
            print(f"\n📊 PORTFOLIO DATA:")
            print(f"   Total Value: ${portfolio_data.get('total_value', 0):,.2f}")
            
            positions = portfolio_data.get('positions', [])
            print(f"   Positions ({len(positions)}):")
            for pos in positions:
                symbol = pos.get('symbol')
                value = pos.get('value_usd', 0)
                percentage = pos.get('percentage', 0)
                print(f"     {symbol}: ${value:,.2f} ({percentage:.1f}%)")
            
            # Check rebalancing analysis
            rebalance_analysis = metadata.get('rebalance_analysis', {})
            print(f"\n⚖️ REBALANCING ANALYSIS:")
            print(f"   Needs Rebalancing: {rebalance_analysis.get('needs_rebalancing')}")
            print(f"   Deviation Score: {rebalance_analysis.get('deviation_score', 0):.1f}%")
            
            # Check recommended trades in detail
            recommended_trades = rebalance_analysis.get('recommended_trades', [])
            print(f"   Recommended Trades ({len(recommended_trades)}):")
            
            for i, trade in enumerate(recommended_trades):
                symbol = trade.get('symbol')
                action = trade.get('action')
                current_value = trade.get('current_value', 0)
                target_value = trade.get('target_value', 0)
                value_change = trade.get('value_change', 0)
                weight_change = trade.get('weight_change', 0)
                
                print(f"     {i+1}. {action} {symbol}:")
                print(f"        Current Value: ${current_value:,.2f}")
                print(f"        Target Value: ${target_value:,.2f}")
                print(f"        Value Change: ${value_change:,.2f}")
                print(f"        Weight Change: {weight_change:.4f}")
            
            # Check if there are any errors
            if 'error' in rebalance_analysis:
                print(f"❌ Rebalancing Error: {rebalance_analysis['error']}")
            
            # Analyze the issue
            print(f"\n🔍 ISSUE ANALYSIS:")
            
            if len(recommended_trades) == 0:
                print("   ❌ No trades generated - optimization engine may be failing")
            elif all(trade.get('value_change', 0) == 0 for trade in recommended_trades):
                print("   ❌ All trades have $0 value change - weights calculation issue")
            elif all(trade.get('target_value', 0) == 0 for trade in recommended_trades):
                print("   ❌ All target values are $0 - optimization weights are empty/zero")
            else:
                print("   ✅ Trades look reasonable")
                
            return True
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    debug_weights()