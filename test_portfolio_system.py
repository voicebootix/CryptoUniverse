#!/usr/bin/env python3
import json
import subprocess
import sys

print("=== COMPREHENSIVE PORTFOLIO OPTIMIZATION TEST ===")

# Login
login_cmd = [
    "curl", "-s", "-X", "POST", 
    "https://cryptouniverse.onrender.com/api/v1/auth/login",
    "-H", "Content-Type: application/json",
    "-d", '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}'
]
login_response = subprocess.run(login_cmd, capture_output=True, text=True)
login_data = json.loads(login_response.stdout)
access_token = login_data.get("access_token", "")

if not access_token:
    print("❌ Login failed!")
    sys.exit(1)

print("✅ Login successful")

# Test 1: Opportunity Discovery
print("\n1. Testing Opportunity Discovery:")
discover_cmd = [
    "curl", "-s", "-X", "POST",
    "https://cryptouniverse.onrender.com/api/v1/opportunities/discover",
    "-H", f"Authorization: Bearer {access_token}",
    "-H", "Content-Type: application/json",
    "-d", '{"scan_type": "comprehensive", "risk_tolerance": "balanced"}'
]
discover_response = subprocess.run(discover_cmd, capture_output=True, text=True)
discover_data = json.loads(discover_response.stdout)

print(f"Total opportunities: {discover_data.get('total_opportunities', 0)}")

# Show strategy performance
perf = discover_data.get('strategy_performance', {})
if perf:
    print("\nStrategy Performance:")
    for s, p in perf.items():
        print(f"  - {s}: {p}")

# Count portfolio opportunities
opps = discover_data.get('opportunities', [])
portfolio_opps = [o for o in opps if 'portfolio' in o.get('strategy_name', '').lower()]
print(f"\nPortfolio opportunities found: {len(portfolio_opps)}")

# Show portfolio strategies
if portfolio_opps:
    print("\nPortfolio Optimization Details:")
    seen_strategies = set()
    for opp in portfolio_opps[:10]:
        metadata = opp.get('metadata', {})
        strategy = metadata.get('strategy_used', metadata.get('strategy', ''))
        if strategy and strategy not in seen_strategies:
            seen_strategies.add(strategy)
            profit = opp.get('profit_potential_usd', 0)
            print(f"  - {strategy}: ${profit:,.0f} potential")

# Test 2: Chat Interface
print("\n2. Testing Chat Interface:")
chat_cmd = [
    "curl", "-s", "-X", "POST",
    "https://cryptouniverse.onrender.com/api/v1/chat/message",
    "-H", f"Authorization: Bearer {access_token}",
    "-H", "Content-Type: application/json",
    "-d", '{"message": "What portfolio rebalancing strategies do you recommend?", "include_context": true}'
]
chat_response = subprocess.run(chat_cmd, capture_output=True, text=True)

try:
    chat_data = json.loads(chat_response.stdout)
    if chat_data.get('success'):
        response_text = chat_data.get('response', '')
        
        # Check strategy mentions
        strategies = ['kelly', 'sharpe', 'risk parity', 'variance', 'equal', 'adaptive']
        mentioned = [s for s in strategies if s.lower() in response_text.lower()]
        
        print(f"✅ Strategies mentioned: {len(mentioned)}/6")
        if mentioned:
            print(f"   Found: {', '.join(mentioned)}")
        
        # Show response quality
        if 'portfolio' in response_text.lower() and 'optimization' in response_text.lower():
            print("✅ Response discusses portfolio optimization")
        else:
            print("❌ Response lacks portfolio optimization content")
            
        print("\nResponse preview:")
        print(response_text[:400] + "..." if len(response_text) > 400 else response_text)
    else:
        print(f"❌ Chat error: {chat_data.get('error')}")
except Exception as e:
    print(f"❌ Chat parse error: {e}")

print("\n=== TEST COMPLETE ===")