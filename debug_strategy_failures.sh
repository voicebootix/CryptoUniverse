#!/bin/bash

echo "=== Debugging Why Strategies Return 0 Opportunities ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Test Risk Management with full response
echo -e "\n1. Risk Management Full Response:"
RISK_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "risk_management",
    "simulation_mode": true
  }')

echo "$RISK_RESPONSE" | python3 -m json.tool | head -50

# Test Portfolio Optimization with full response  
echo -e "\n2. Portfolio Optimization Full Response:"
PORTFOLIO_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "portfolio_optimization",
    "simulation_mode": true
  }')

echo "$PORTFOLIO_RESPONSE" | python3 -m json.tool | head -50

# Test Options Trade with full response
echo -e "\n3. Options Trade Full Response:"
OPTIONS_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "options_trade",
    "simulation_mode": true
  }')

echo "$OPTIONS_RESPONSE" | python3 -m json.tool | head -50

