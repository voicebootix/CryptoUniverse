#!/bin/bash

echo "=== TESTING EXACT FLOW ==="
echo

# Get token
TOKEN=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "1. Testing Market Analysis directly with BTC/USDT:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/market/analysis \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "technical_analysis",
    "symbols": "BTC/USDT",
    "timeframe": "4h"
  }' | python3 -m json.tool | head -30

echo
echo "2. Testing Market Analysis with just BTC:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/market/analysis \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "technical_analysis",
    "symbols": "BTC",
    "timeframe": "4h"
  }' | python3 -m json.tool | head -30

echo
echo "3. Testing Trading Strategy execution directly:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "spot_momentum_strategy",
    "symbol": "BTC/USDT",
    "parameters": {
      "timeframe": "4h"
    }
  }' | python3 -m json.tool

echo
echo "4. Checking user's actual strategies:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/strategies/my-strategies \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | grep -E '"strategy_id"|"name"|"is_active"' | head -20