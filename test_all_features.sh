#!/bin/bash

# Comprehensive CryptoUniverse Feature Testing Script
# Tests all API endpoints and features to identify issues

BASE_URL="https://cryptouniverse.onrender.com"
API_URL="${BASE_URL}/api/v1"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
PASSED=0
FAILED=0
WARNINGS=0

echo -e "${BLUE}🚀 Comprehensive CryptoUniverse Feature Testing${NC}"
echo -e "${BLUE}📍 Testing: $BASE_URL${NC}"
echo "=================================================="

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local name=$3
    local data=$4
    local token=$5
    
    echo -e "\n${YELLOW}Testing: $name${NC}"
    echo "Endpoint: $method $endpoint"
    
    if [ -n "$token" ]; then
        AUTH_HEADER="-H \"Authorization: Bearer $token\""
    else
        AUTH_HEADER=""
    fi
    
    if [ -n "$data" ]; then
        DATA_PARAM="-d '$data'"
    else
        DATA_PARAM=""
    fi
    
    # Build and execute curl command
    if [ "$method" == "GET" ]; then
        if [ -n "$token" ]; then
            RESPONSE=$(curl -s -w "\n|||STATUS_CODE:%{http_code}|||" -H "Authorization: Bearer $token" "$endpoint" 2>/dev/null)
        else
            RESPONSE=$(curl -s -w "\n|||STATUS_CODE:%{http_code}|||" "$endpoint" 2>/dev/null)
        fi
    else
        if [ -n "$token" ]; then
            RESPONSE=$(curl -s -X $method -w "\n|||STATUS_CODE:%{http_code}|||" \
                -H "Authorization: Bearer $token" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$endpoint" 2>/dev/null)
        else
            RESPONSE=$(curl -s -X $method -w "\n|||STATUS_CODE:%{http_code}|||" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$endpoint" 2>/dev/null)
        fi
    fi
    
    STATUS_CODE=$(echo "$RESPONSE" | grep -o "STATUS_CODE:[0-9]*" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed 's/|||STATUS_CODE:[0-9]*|||//')
    
    if [ "$STATUS_CODE" == "200" ] || [ "$STATUS_CODE" == "201" ]; then
        echo -e "${GREEN}✅ PASSED (Status: $STATUS_CODE)${NC}"
        ((PASSED++))
        echo "Response preview: $(echo "$BODY" | head -c 200)..."
        return 0
    elif [ "$STATUS_CODE" == "404" ]; then
        echo -e "${RED}❌ FAILED - Not Found (Status: $STATUS_CODE)${NC}"
        ((FAILED++))
        return 1
    elif [ "$STATUS_CODE" == "401" ] || [ "$STATUS_CODE" == "403" ]; then
        echo -e "${YELLOW}⚠️  WARNING - Unauthorized (Status: $STATUS_CODE)${NC}"
        ((WARNINGS++))
        return 2
    elif [ "$STATUS_CODE" == "500" ] || [ "$STATUS_CODE" == "502" ] || [ "$STATUS_CODE" == "503" ]; then
        echo -e "${RED}❌ FAILED - Server Error (Status: $STATUS_CODE)${NC}"
        echo "Error: $BODY"
        ((FAILED++))
        return 1
    else
        echo -e "${RED}❌ FAILED (Status: $STATUS_CODE)${NC}"
        echo "Response: $(echo "$BODY" | head -c 200)..."
        ((FAILED++))
        return 1
    fi
}

# Step 1: Login and get token
echo -e "\n${BLUE}=== AUTHENTICATION ===${NC}"
LOGIN_DATA="{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -d "$LOGIN_DATA")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -n "$TOKEN" ]; then
    echo -e "${GREEN}✅ Login successful${NC}"
    echo "Token obtained: ${TOKEN:0:30}..."
else
    echo -e "${RED}❌ Login failed${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

# Save results to file
REPORT_FILE="/c/Users/ASUS/CryptoUniverse/test_results_$(date +%Y%m%d_%H%M%S).json"
echo "{\"timestamp\":\"$(date)\",\"results\":[" > "$REPORT_FILE"

# Test AI Chat System
echo -e "\n${BLUE}=== AI CHAT SYSTEM ===${NC}"
test_endpoint "POST" "${API_URL}/chat/message" "AI Chat Message" \
    '{"message":"What is the current market trend for Bitcoin?","context":{}}' "$TOKEN"

test_endpoint "GET" "${API_URL}/chat/history" "Chat History" "" "$TOKEN"

# Test Market Analysis
echo -e "\n${BLUE}=== MARKET ANALYSIS ===${NC}"
test_endpoint "GET" "${API_URL}/market/analysis/BTC" "BTC Analysis" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/market/analysis/ETH" "ETH Analysis" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/market/sentiment" "Market Sentiment" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/market/indicators/BTC" "BTC Indicators" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/market/predictions" "Market Predictions" "" "$TOKEN"

# Test Trading Strategies
echo -e "\n${BLUE}=== TRADING STRATEGIES ===${NC}"
test_endpoint "GET" "${API_URL}/strategies/list" "Strategy List" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/strategies/active" "Active Strategies" "" "$TOKEN"
test_endpoint "POST" "${API_URL}/strategies/backtest" "Strategy Backtest" \
    '{"strategy_id":"momentum","symbol":"BTC","timeframe":"1h","period":"7d"}' "$TOKEN"

# Test AI Consensus
echo -e "\n${BLUE}=== AI CONSENSUS SYSTEM ===${NC}"
test_endpoint "POST" "${API_URL}/ai/consensus" "AI Consensus Analysis" \
    '{"symbol":"BTC","action":"analyze","timeframe":"4h"}' "$TOKEN"
test_endpoint "POST" "${API_URL}/ai/risk-assessment" "AI Risk Assessment" \
    '{"portfolio_id":"default","market_conditions":"current"}' "$TOKEN"
test_endpoint "GET" "${API_URL}/ai/recommendations" "AI Recommendations" "" "$TOKEN"

# Test Exchange Integration
echo -e "\n${BLUE}=== EXCHANGE INTEGRATION ===${NC}"
test_endpoint "GET" "${API_URL}/exchanges/list" "Exchange List" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/exchanges/balances" "Exchange Balances" "" "$TOKEN"
test_endpoint "POST" "${API_URL}/exchanges/test-connection" "Test Exchange Connection" \
    '{"exchange":"binance"}' "$TOKEN"

# Test Paper Trading
echo -e "\n${BLUE}=== PAPER TRADING ===${NC}"
test_endpoint "POST" "${API_URL}/paper-trading/setup" "Setup Paper Trading" \
    '{"initial_balance":10000,"enable_margin":false}' "$TOKEN"
test_endpoint "GET" "${API_URL}/paper-trading/portfolio" "Paper Trading Portfolio" "" "$TOKEN"
test_endpoint "POST" "${API_URL}/paper-trading/execute" "Execute Paper Trade" \
    '{"symbol":"BTC","side":"buy","amount":0.01,"order_type":"market"}' "$TOKEN"

# Test Trading Execution
echo -e "\n${BLUE}=== TRADING EXECUTION ===${NC}"
test_endpoint "GET" "${API_URL}/trading/portfolio" "Trading Portfolio" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/trading/history" "Trading History" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/trading/open-orders" "Open Orders" "" "$TOKEN"
test_endpoint "POST" "${API_URL}/trading/simulate" "Simulate Trade" \
    '{"symbol":"ETH","side":"buy","amount":0.1,"exchange":"binance"}' "$TOKEN"

# Test Credits/Payment System
echo -e "\n${BLUE}=== CREDIT & PAYMENT SYSTEM ===${NC}"
test_endpoint "GET" "${API_URL}/credits/balance" "Credit Balance" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/credits/history" "Credit History" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/credits/pricing" "Pricing Plans" "" "$TOKEN"

# Test Telegram Integration
echo -e "\n${BLUE}=== TELEGRAM INTEGRATION ===${NC}"
test_endpoint "GET" "${API_URL}/telegram/status" "Telegram Bot Status" "" "$TOKEN"
test_endpoint "POST" "${API_URL}/telegram/connect" "Connect Telegram" \
    '{"telegram_id":"test_user"}' "$TOKEN"
test_endpoint "GET" "${API_URL}/telegram/commands" "Telegram Commands" "" "$TOKEN"

# Test Admin Functions
echo -e "\n${BLUE}=== ADMIN FUNCTIONS ===${NC}"
test_endpoint "GET" "${API_URL}/admin/users" "User List" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/admin/system/status" "System Status" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/admin/metrics" "System Metrics" "" "$TOKEN"
test_endpoint "GET" "${API_URL}/admin/logs/recent" "Recent Logs" "" "$TOKEN"

# Test API Keys Management
echo -e "\n${BLUE}=== API KEY MANAGEMENT ===${NC}"
test_endpoint "GET" "${API_URL}/api-keys" "List API Keys" "" "$TOKEN"
test_endpoint "POST" "${API_URL}/api-keys/generate" "Generate API Key" \
    '{"name":"Test Key","permissions":["read"]}' "$TOKEN"

# Test WebSocket Connection
echo -e "\n${BLUE}=== WEBSOCKET CONNECTION ===${NC}"
echo "Testing WebSocket at: wss://cryptouniverse.onrender.com/ws"
# Note: WebSocket testing requires different approach, marking as info
echo -e "${YELLOW}ℹ️  WebSocket endpoint configured at wss://cryptouniverse.onrender.com/ws${NC}"
echo "Manual testing required for WebSocket functionality"

# Generate Summary Report
echo -e "\n${BLUE}=================================================="
echo -e "📊 TEST SUMMARY REPORT"
echo -e "==================================================${NC}"
echo -e "${GREEN}✅ Passed: $PASSED${NC}"
echo -e "${RED}❌ Failed: $FAILED${NC}"
echo -e "${YELLOW}⚠️  Warnings: $WARNINGS${NC}"

TOTAL=$((PASSED + FAILED + WARNINGS))
if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$((PASSED * 100 / TOTAL))
    echo -e "📈 Success Rate: ${SUCCESS_RATE}%"
fi

# Identify critical issues
echo -e "\n${BLUE}=== CRITICAL ISSUES TO FIX ===${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}The following features need immediate attention:${NC}"
    echo "1. Review failed endpoints in the log above"
    echo "2. Check server logs for 500 errors"
    echo "3. Verify endpoint routes match implementation"
    echo "4. Ensure all required services are running"
else
    echo -e "${GREEN}No critical issues found!${NC}"
fi

# Save final report
echo "]}" >> "$REPORT_FILE"
echo -e "\n${BLUE}Full report saved to: $REPORT_FILE${NC}"

exit $FAILED