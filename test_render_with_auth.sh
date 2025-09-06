#!/bin/bash

# CryptoUniverse Render Deployment Test Script with Authentication
# Admin credentials: admin@cryptouniverse.com / AdminPass123!

BASE_URL="https://cryptouniverse.onrender.com"
API_URL="${BASE_URL}/api/v1"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "🚀 Testing CryptoUniverse Render Deployment with Authentication"
echo "📍 Base URL: $BASE_URL"
echo "👤 User: $EMAIL"
echo "=================================================="

# Step 1: Test Health Endpoint (No Auth Required)
echo -e "\n1️⃣ Testing Health Endpoint..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/health")
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -n 1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -n -1)
echo "   Status Code: $HEALTH_CODE"
if [ "$HEALTH_CODE" == "200" ]; then
    echo "   ✅ Health check passed"
else
    echo "   ❌ Health check failed"
fi

# Step 2: Login and Get Token
echo -e "\n2️⃣ Testing Login..."
LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}" \
    -w "\n%{http_code}")

LOGIN_CODE=$(echo "$LOGIN_RESPONSE" | tail -n 1)
LOGIN_BODY=$(echo "$LOGIN_RESPONSE" | head -n -1)

echo "   Status Code: $LOGIN_CODE"

if [ "$LOGIN_CODE" == "200" ] || [ "$LOGIN_CODE" == "201" ]; then
    echo "   ✅ Login successful"
    
    # Extract access token using grep and sed
    ACCESS_TOKEN=$(echo "$LOGIN_BODY" | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')
    
    if [ -n "$ACCESS_TOKEN" ]; then
        echo "   🔑 Token obtained (first 20 chars): ${ACCESS_TOKEN:0:20}..."
        
        # Save token for later use
        echo "$ACCESS_TOKEN" > /tmp/cryptouniverse_token.txt
        
        # Step 3: Test Authenticated Endpoints
        echo -e "\n3️⃣ Testing Market Prices (Authenticated)..."
        PRICES_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/market/prices" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}")
        PRICES_CODE=$(echo "$PRICES_RESPONSE" | tail -n 1)
        echo "   Status Code: $PRICES_CODE"
        if [ "$PRICES_CODE" == "200" ]; then
            echo "   ✅ Market prices retrieved"
        else
            echo "   ❌ Failed to get market prices"
        fi
        
        echo -e "\n4️⃣ Testing Portfolio Endpoint..."
        PORTFOLIO_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/trading/portfolio" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}")
        PORTFOLIO_CODE=$(echo "$PORTFOLIO_RESPONSE" | tail -n 1)
        echo "   Status Code: $PORTFOLIO_CODE"
        if [ "$PORTFOLIO_CODE" == "200" ]; then
            echo "   ✅ Portfolio data retrieved"
        else
            echo "   ❌ Failed to get portfolio"
        fi
        
        echo -e "\n5️⃣ Testing Exchange List..."
        EXCHANGES_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/exchanges/list" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}")
        EXCHANGES_CODE=$(echo "$EXCHANGES_RESPONSE" | tail -n 1)
        echo "   Status Code: $EXCHANGES_CODE"
        if [ "$EXCHANGES_CODE" == "200" ]; then
            echo "   ✅ Exchange list retrieved"
        else
            echo "   ❌ Failed to get exchanges"
        fi
        
        echo -e "\n6️⃣ Testing Strategy List..."
        STRATEGIES_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/strategies/list" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}")
        STRATEGIES_CODE=$(echo "$STRATEGIES_RESPONSE" | tail -n 1)
        echo "   Status Code: $STRATEGIES_CODE"
        if [ "$STRATEGIES_CODE" == "200" ]; then
            echo "   ✅ Strategy list retrieved"
        else
            echo "   ❌ Failed to get strategies"
        fi
        
        echo -e "\n7️⃣ Testing Market Analysis (BTC)..."
        ANALYSIS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/market/analysis/BTC" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}")
        ANALYSIS_CODE=$(echo "$ANALYSIS_RESPONSE" | tail -n 1)
        echo "   Status Code: $ANALYSIS_CODE"
        if [ "$ANALYSIS_CODE" == "200" ]; then
            echo "   ✅ BTC analysis retrieved"
        else
            echo "   ❌ Failed to get BTC analysis"
        fi
        
        echo -e "\n8️⃣ Testing AI Consensus..."
        AI_RESPONSE=$(curl -s -X POST -w "\n%{http_code}" "${API_URL}/ai/consensus" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            -H "Content-Type: application/json" \
            -d '{"symbol":"BTC","action":"analyze"}')
        AI_CODE=$(echo "$AI_RESPONSE" | tail -n 1)
        echo "   Status Code: $AI_CODE"
        if [ "$AI_CODE" == "200" ]; then
            echo "   ✅ AI consensus retrieved"
        else
            echo "   ❌ Failed to get AI consensus"
        fi
        
        echo -e "\n9️⃣ Testing Admin Endpoints (Admin Only)..."
        ADMIN_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/admin/users" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}")
        ADMIN_CODE=$(echo "$ADMIN_RESPONSE" | tail -n 1)
        echo "   Status Code: $ADMIN_CODE"
        if [ "$ADMIN_CODE" == "200" ]; then
            echo "   ✅ Admin access confirmed"
        else
            echo "   ⚠️  Admin endpoint not accessible (Code: $ADMIN_CODE)"
        fi
        
    else
        echo "   ❌ Failed to extract token from response"
        echo "   Response: $LOGIN_BODY"
    fi
else
    echo "   ❌ Login failed"
    echo "   Response: $LOGIN_BODY"
fi

echo -e "\n=================================================="
echo "📊 Test Summary Complete"
echo "=================================================="