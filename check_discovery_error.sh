#!/bin/bash

echo "Checking for Discovery Service Errors"
echo "===================================="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "Login failed!"
    exit 1
fi

# Test with various parameters to see if any trigger actual processing
echo -e "\n1. Testing with explicit strategy list..."
RESPONSE1=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "strategies": ["spot_momentum_strategy"],
    "force_refresh": true
  }')

EXEC_TIME1=$(echo "$RESPONSE1" | grep -o '"execution_time_ms":[0-9.]*' | cut -d':' -f2)
echo "Execution time: $EXEC_TIME1 ms"

echo -e "\n2. Testing with different parameters..."
RESPONSE2=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "min_confidence": 10,
    "max_results": 100,
    "force_refresh": false
  }')

EXEC_TIME2=$(echo "$RESPONSE2" | grep -o '"execution_time_ms":[0-9.]*' | cut -d':' -f2)
echo "Execution time: $EXEC_TIME2 ms"

# Test the onboarding endpoint
echo -e "\n3. Testing onboarding endpoint..."
ONBOARD=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/onboard \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{}')

echo "Onboarding response:"
echo "$ONBOARD" | python3 -m json.tool 2>/dev/null || echo "$ONBOARD"

# Test status endpoint
echo -e "\n4. Testing status endpoint..."
STATUS=$(curl -s -X GET https://cryptouniverse.onrender.com/api/v1/opportunities/status \
  -H "Authorization: Bearer $TOKEN")

echo "Status response:"
echo "$STATUS" | python3 -m json.tool 2>/dev/null || echo "$STATUS"

echo -e "\nCompleted!"