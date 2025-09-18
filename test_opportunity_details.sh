#!/bin/bash

echo "=== Testing Opportunity Details ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Get a few opportunities to see their structure
DISCOVERY_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "force_refresh": false,
    "include_details": true
  }')

echo "Sample opportunities:"
echo "$DISCOVERY_RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
opps = data.get('opportunities', [])[:3]  # First 3
for i, opp in enumerate(opps, 1):
    print(f'\\nOpportunity {i}:')
    print(f'  Symbol: {opp.get(\"symbol\")}')
    print(f'  Strategy: {opp.get(\"strategy_name\")}')
    print(f'  Action: {opp.get(\"action\")}')
    print(f'  Entry: {opp.get(\"entry_price\")}')
    print(f'  Target: {opp.get(\"target_price\")}')
    print(f'  Stop Loss: {opp.get(\"stop_loss_price\")}')
    print(f'  Signal Strength: {opp.get(\"signal_strength\")}')
    print(f'  Confidence: {opp.get(\"confidence_score\")}')
    print(f'  Metadata: {opp.get(\"metadata\")}')
"

# Check signal analysis
echo -e "\n=== Signal Analysis ==="
echo "$DISCOVERY_RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
signal_analysis = data.get('signal_analysis')
threshold_transparency = data.get('threshold_transparency')
print(f'Signal Analysis: {signal_analysis}')
print(f'Threshold Transparency: {threshold_transparency}')
"

