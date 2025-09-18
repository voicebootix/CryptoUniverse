#!/bin/bash

echo "=== FULL SYSTEM TEST - PORTFOLIO OPTIMIZATION ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Test opportunity discovery
echo -e "\n1. Testing Opportunity Discovery:"
OPPORTUNITIES=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_type": "comprehensive",
    "risk_tolerance": "balanced"
  }')

echo "$OPPORTUNITIES" | python3 -c '
import json, sys
data = json.load(sys.stdin)

print(f"Total opportunities: {data.get(\"total_opportunities\", 0)}")

# Show strategy performance
perf = data.get("strategy_performance", {})
print("\nStrategy Performance:")
for s, p in perf.items():
    print(f"  - {s}: {p}")

# Count portfolio opportunities  
opps = data.get("opportunities", [])
portfolio_opps = [o for o in opps if "portfolio" in o.get("strategy_name", "").lower()]
print(f"\nPortfolio opportunities: {len(portfolio_opps)}")

# Show portfolio strategies
if portfolio_opps:
    print("\nPortfolio Optimization Strategies Found:")
    seen = set()
    for opp in portfolio_opps[:10]:  # Show first 10
        metadata = opp.get("metadata", {})
        strategy = metadata.get("strategy_used", metadata.get("strategy", ""))
        if strategy and strategy not in seen:
            seen.add(strategy)
            print(f"  - {strategy}: ${opp.get(\"profit_potential_usd\", 0):,.0f} potential")
'

# Test chat interface
echo -e "\n2. Testing Chat Interface:"
CHAT_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What portfolio rebalancing strategies do you recommend?",
    "include_context": true
  }')

echo "$CHAT_RESPONSE" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get("success"):
        response = data.get("response", "")
        
        # Count strategy mentions
        strategies = ["kelly", "sharpe", "risk parity", "variance", "equal", "adaptive"]
        mentioned = [s for s in strategies if s.lower() in response.lower()]
        
        print(f"✅ Strategies mentioned: {len(mentioned)}/6 - {mentioned}")
        
        # Show preview
        print("\nResponse preview:")
        print(response[:500] + "..." if len(response) > 500 else response)
    else:
        print(f"❌ Error: {data.get(\"error\")}")
except Exception as e:
    print(f"❌ Parse error: {e}")
'

echo -e "\n=== TEST COMPLETE ==="
