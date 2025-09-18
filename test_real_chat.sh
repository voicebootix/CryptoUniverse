#!/bin/bash

echo "=== TESTING CHAT WITH REAL PORTFOLIO DATA ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Try different prompts to trigger opportunity discovery
PROMPTS=(
  "What are my current trading opportunities?"
  "Show me portfolio optimization strategies"
  "Find opportunities for me"
  "What portfolio rebalancing do you recommend?"
)

for prompt in "${PROMPTS[@]}"; do
  echo -e "\n--- Testing: '$prompt' ---"
  
  RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"$prompt\", \"include_context\": true}")
  
  echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)

intent = data.get('intent', 'unknown')
print(f'Intent detected: {intent}')

response = data.get('response', data.get('content', ''))
if response:
    # Check for specific portfolio optimization mentions
    strategies = ['kelly criterion', 'max sharpe', 'risk parity', 'min variance', 'equal weight', 'adaptive']
    found = [s for s in strategies if s.lower() in response.lower()]
    
    if found:
        print(f'✅ Found strategies: {found}')
    else:
        print('❌ No specific strategies mentioned')
    
    # Check for numbers/percentages
    import re
    percentages = re.findall(r'\d+\.?\d*%', response)
    if percentages:
        print(f'📊 Percentages found: {percentages[:5]}')
    
    print(f'Response length: {len(response)} chars')
else:
    print('❌ No response')
"
done

