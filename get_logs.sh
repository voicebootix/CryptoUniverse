#!/bin/bash

# Load Render credentials from local env file
source .env.render.local

if [ -z "$RENDER_API_KEY" ] || [ "$RENDER_API_KEY" == "rnd_paste_your_key_here" ]; then
    echo "❌ Please edit .env.render.local and add your actual Render API key"
    exit 1
fi

echo "📋 Fetching recent error logs from Render..."
echo "==========================================="

# Fetch logs with error filtering
curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
     "https://api.render.com/v1/services/$RENDER_SERVICE_ID/logs?limit=200" | \
     grep -i -E "(error|exception|traceback|failed|500)" | \
     tail -30

echo ""
echo "✅ Safe to share the above logs (no keys shown)"