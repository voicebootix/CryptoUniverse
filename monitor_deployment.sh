#!/bin/bash

echo "Monitoring CryptoUniverse Deployment"
echo "===================================="
echo "Checking for nullable fields fix deployment..."
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test the API
test_api() {
    # First login
    LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d '{
        "email": "admin@cryptouniverse.com",
        "password": "AdminPass123!"
      }' 2>/dev/null)
    
    TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$TOKEN" ]; then
        echo -e "${RED}✗ API is down or login failed${NC}"
        return 1
    fi
    
    # Quick opportunity discovery test
    RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{"force_refresh": true}' 2>/dev/null)
    
    SUCCESS=$(echo $RESPONSE | grep -o '"success":[^,]*' | cut -d':' -f2)
    TOTAL_OPPS=$(echo $RESPONSE | grep -o '"total_opportunities":[0-9]*' | cut -d':' -f2)
    SIGNALS=$(echo $RESPONSE | grep -o '"total_signals_analyzed":[0-9]*' | cut -d':' -f2)
    
    if [ "$SUCCESS" == "true" ]; then
        echo -e "${GREEN}✓ API is up${NC}"
        echo "  - Total opportunities: $TOTAL_OPPS"
        echo "  - Signals analyzed: $SIGNALS"
        
        if [ "$TOTAL_OPPS" -gt 0 ]; then
            echo -e "  ${GREEN}✓ OPPORTUNITIES FOUND! Fix is working!${NC}"
            return 0
        elif [ "$SIGNALS" -gt 0 ]; then
            echo -e "  ${YELLOW}○ Signals analyzed but no opportunities yet${NC}"
        else
            echo -e "  ${YELLOW}○ No signals analyzed yet${NC}"
        fi
    else
        echo -e "${RED}✗ API returned error${NC}"
        return 1
    fi
}

# Monitor loop
echo "Starting monitoring (press Ctrl+C to stop)..."
echo ""

COUNTER=0
while true; do
    COUNTER=$((COUNTER + 1))
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo -n "[$TIMESTAMP] Check #$COUNTER: "
    
    test_api
    
    echo ""
    echo "Waiting 30 seconds before next check..."
    sleep 30
done