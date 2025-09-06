#!/bin/bash

echo "This script will help you safely fetch Render logs"
echo "=================================================="
echo ""
echo "1. First, set your credentials (don't share these!):"
echo "   export RENDER_API_KEY='rnd_YOUR_KEY_HERE'"
echo "   export RENDER_SERVICE_ID='srv_YOUR_SERVICE_ID'"
echo ""
echo "2. Then run this command to fetch logs:"
echo ""

if [ -z "$RENDER_API_KEY" ]; then
    echo "❌ RENDER_API_KEY not set. Please set it first (see instructions above)"
    exit 1
fi

if [ -z "$RENDER_SERVICE_ID" ]; then
    echo "❌ RENDER_SERVICE_ID not set. Please set it first (see instructions above)"
    exit 1
fi

echo "✅ Fetching logs (API key hidden for security)..."
echo "Service ID: $RENDER_SERVICE_ID"
echo ""

# Fetch recent logs
curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
     "https://api.render.com/v1/services/$RENDER_SERVICE_ID/logs?limit=100" \
     | grep -E "(ERROR|CRITICAL|500|AttributeError|NameError|TypeError)" \
     | tail -50

echo ""
echo "=================================================="
echo "✅ You can safely share the log output above (no API keys shown)"