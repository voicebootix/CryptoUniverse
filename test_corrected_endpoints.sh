#!/bin/bash

# Test CryptoUniverse with CORRECT endpoint paths based on router.py

BASE_URL="https://cryptouniverse.onrender.com"
API_URL="${BASE_URL}/api/v1"

# Check if TOKEN environment variable is set
if [ -z "$TOKEN" ]; then
    echo "Error: TOKEN environment variable not set"
    echo "Please set TOKEN with: export TOKEN=your_jwt_token_here"
    exit 1
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Testing CORRECTED Endpoints${NC}"
echo "================================"

# Test AI Consensus (correct path: /ai-consensus)
echo -e "\n${YELLOW}AI Consensus:${NC}"
curl -s -o /dev/null -w "POST /ai-consensus/analyze: %{http_code}\n" \
  -X POST "${API_URL}/ai-consensus/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC"}'

# Test Chat (correct path: /chat)
echo -e "\n${YELLOW}Chat System:${NC}"
curl -s -o /dev/null -w "POST /chat/message: %{http_code}\n" \
  -X POST "${API_URL}/chat/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'

curl -s -o /dev/null -w "GET /chat/sessions: %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "${API_URL}/chat/sessions"

# Test Market Analysis (correct path: /market)
echo -e "\n${YELLOW}Market Analysis:${NC}"
curl -s -o /dev/null -w "GET /market/prices: %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "${API_URL}/market/prices"

curl -s -o /dev/null -w "GET /market/analysis/BTC: %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "${API_URL}/market/analysis/BTC"

# Test Admin endpoints
echo -e "\n${YELLOW}Admin Endpoints:${NC}"
curl -s -o /dev/null -w "GET /admin/users: %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "${API_URL}/admin/users"

curl -s -o /dev/null -w "GET /admin/system/status: %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "${API_URL}/admin/system/status"

# Test Telegram
echo -e "\n${YELLOW}Telegram:${NC}"
curl -s -o /dev/null -w "POST /telegram/connect: %{http_code}\n" \
  -X POST "${API_URL}/telegram/connect" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"telegram_id":"test"}'

# Check what endpoints actually exist in market
echo -e "\n${YELLOW}Available Market Endpoints:${NC}"
curl -s "${API_URL}/market" -H "Authorization: Bearer $TOKEN" | head -100