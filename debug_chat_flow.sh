#!/bin/bash

echo "=== DEBUGGING CHAT FLOW ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Test with explicit context request
echo "Testing chat with explicit opportunity context:"
RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me all available portfolio optimization strategies with their expected returns",
    "include_context": true
  }')

echo "$RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    
    print(f'Success: {data.get(\"success\", False)}')
    print(f'Intent: {data.get(\"intent\", \"unknown\")}')
    print(f'Session ID: {data.get(\"session_id\", \"none\")}')
    
    response = data.get('response', data.get('content', ''))
    if response:
        print(f'\nResponse length: {len(response)} chars')
        
        # Check for strategy mentions
        strategies = ['kelly', 'sharpe', 'risk parity', 'variance', 'equal', 'adaptive']
        mentioned = [s for s in strategies if s.lower() in response.lower()]
        print(f'Strategies mentioned: {mentioned}')
        
        # Check for portfolio content
        has_portfolio = 'portfolio' in response.lower()
        has_optimization = 'optimization' in response.lower() or 'optimiz' in response.lower()
        print(f'Mentions portfolio: {has_portfolio}')
        print(f'Mentions optimization: {has_optimization}')
        
        print('\n--- FULL RESPONSE ---')
        print(response)
    else:
        print('No response content')
        print(f'Full data: {json.dumps(data, indent=2)}')
        
except Exception as e:
    print(f'Error: {e}')
    print(f'Raw response: {RESPONSE[:500]}')
"

