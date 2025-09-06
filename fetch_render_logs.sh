#!/bin/bash

# Fetch Render logs using API
# You need to set your RENDER_API_KEY environment variable

RENDER_API_KEY="${RENDER_API_KEY:-your_api_key_here}"
SERVICE_ID="${RENDER_SERVICE_ID:-your_service_id_here}"

if [ "$RENDER_API_KEY" == "your_api_key_here" ]; then
    echo "Please set your RENDER_API_KEY environment variable"
    echo "You can find it at: https://dashboard.render.com/account/api-keys"
    exit 1
fi

if [ "$SERVICE_ID" == "your_service_id_here" ]; then
    echo "Please set your RENDER_SERVICE_ID environment variable"
    echo "You can find it in your service URL: https://dashboard.render.com/web/srv-XXXXXX"
    exit 1
fi

echo "Fetching logs from Render..."
echo "================================"

# Fetch logs from Render API
curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
     "https://api.render.com/v1/services/$SERVICE_ID/logs" \
     | jq -r '.[] | "\(.timestamp) | \(.message)"' 2>/dev/null || \
     curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
     "https://api.render.com/v1/services/$SERVICE_ID/logs"

echo "================================"
echo "To get real-time logs, visit:"
echo "https://dashboard.render.com/web/$SERVICE_ID/logs"