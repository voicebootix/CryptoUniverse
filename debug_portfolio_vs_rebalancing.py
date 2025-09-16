#!/usr/bin/env python3
"""
Debug Portfolio vs Rebalancing
Compare what portfolio query returns vs what rebalancing gets
"""

import requests
import json
import time

BASE_URL = "https://cryptouniverse.onrender.com"

def compare_portfolio_vs_rebalancing():
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
    
    print("🔍 Comparing Portfolio Query vs Rebalancing Query")
    
    # Test 1: Portfolio query
    print(f"\n{'='*60}")
    print("📊 TEST 1: Portfolio Query")
    print(f"{'='*60}")
    
    portfolio_message = "What's my current portfolio balance?"
    payload = {"message": portfolio_message, "session_id": session_id}
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/chat/message", headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            metadata = data.get('metadata', {})
            portfolio_summary = metadata.get('portfolio_summary', {})
            
            print(f"✅ Portfolio Query Success")
            print(f"   Total Value: ${portfolio_summary.get('total_value', 0):,.2f}")
            print(f"   Positions: {len(portfolio_summary.get('positions', []))}")
            
            positions = portfolio_summary.get('positions', [])
            if positions:
                print(f"   Assets:")
                for pos in positions[:3]:  # Show first 3
                    symbol = pos.get('symbol')
                    value = pos.get('value_usd', 0)
                    percentage = pos.get('percentage', 0)
                    print(f"     {symbol}: ${value:,.2f} ({percentage:.1f}%)")
            
            portfolio_success = True
            portfolio_value = portfolio_summary.get('total_value', 0)
            
        else:
            print(f"❌ Portfolio Query Failed: {response.status_code}")
            portfolio_success = False
            portfolio_value = 0
            
    except Exception as e:
        print(f"❌ Portfolio Query Error: {e}")
        portfolio_success = False
        portfolio_value = 0
    
    # Small delay
    time.sleep(2)
    
    # Test 2: Rebalancing query
    print(f"\n{'='*60}")
    print("⚖️ TEST 2: Rebalancing Query")
    print(f"{'='*60}")
    
    rebalancing_message = "Should I rebalance my portfolio?"
    payload = {"message": rebalancing_message, "session_id": session_id}
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/chat/message", headers=headers, json=payload, timeout=90)
        
        if response.status_code == 200:
            data = response.json()
            metadata = data.get('metadata', {})
            
            portfolio_data = metadata.get('portfolio_data', {})
            rebalance_analysis = metadata.get('rebalance_analysis', {})
            
            print(f"✅ Rebalancing Query Success")
            print(f"   Portfolio Value: ${portfolio_data.get('total_value', 0):,.2f}")
            print(f"   Positions: {len(portfolio_data.get('positions', []))}")
            print(f"   Needs Rebalancing: {rebalance_analysis.get('needs_rebalancing')}")
            print(f"   Recommended Trades: {len(rebalance_analysis.get('recommended_trades', []))}")
            
            if 'error' in rebalance_analysis:
                print(f"   ❌ Rebalancing Error: {rebalance_analysis['error']}")
            
            rebalancing_success = True
            rebalancing_value = portfolio_data.get('total_value', 0)
            
        else:
            print(f"❌ Rebalancing Query Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            rebalancing_success = False
            rebalancing_value = 0
            
    except Exception as e:
        print(f"❌ Rebalancing Query Error: {e}")
        rebalancing_success = False
        rebalancing_value = 0
    
    # Comparison
    print(f"\n{'='*60}")
    print("🔍 COMPARISON ANALYSIS")
    print(f"{'='*60}")
    
    print(f"Portfolio Query:    {'✅' if portfolio_success else '❌'} ${portfolio_value:,.2f}")
    print(f"Rebalancing Query:  {'✅' if rebalancing_success else '❌'} ${rebalancing_value:,.2f}")
    
    if portfolio_success and not rebalancing_success:
        print(f"\n🎯 DIAGNOSIS: Portfolio works, Rebalancing fails")
        print(f"   • Portfolio data is available")
        print(f"   • Rebalancing analysis is broken")
        print(f"   • Issue is in rebalancing logic, not data source")
        
    elif portfolio_success and rebalancing_success and portfolio_value > 0 and rebalancing_value == 0:
        print(f"\n🎯 DIAGNOSIS: Data loss in rebalancing pipeline")
        print(f"   • Portfolio data: ${portfolio_value:,.2f}")
        print(f"   • Rebalancing data: ${rebalancing_value:,.2f}")
        print(f"   • Data is lost somewhere in rebalancing processing")
        
    elif portfolio_success and rebalancing_success and portfolio_value > 0 and rebalancing_value > 0:
        print(f"\n🎯 DIAGNOSIS: Data flow is working")
        print(f"   • Both queries return data")
        print(f"   • Issue must be in optimization engine or trade generation")
        
    else:
        print(f"\n🎯 DIAGNOSIS: Broader system issue")
        print(f"   • Portfolio success: {portfolio_success}")
        print(f"   • Rebalancing success: {rebalancing_success}")

if __name__ == "__main__":
    compare_portfolio_vs_rebalancing()