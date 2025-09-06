#!/bin/bash

# Direct method - replace these values with your actual credentials
RENDER_API_KEY="rnd_YOUR_API_KEY_HERE"
SERVICE_ID="srv-YOUR_SERVICE_ID_HERE"

# Instructions:
echo "To use this script:"
echo "1. Get your API key from: https://dashboard.render.com/account/api-keys"
echo "2. Find your service ID in the URL when viewing your service"
echo "   Example: https://dashboard.render.com/web/srv-abc123 → service ID is srv-abc123"
echo ""
echo "3. Replace the values above with your actual credentials"
echo ""

# Uncomment these lines after adding your credentials:
# echo "Fetching logs..."
# curl -H "Authorization: Bearer $RENDER_API_KEY" \
#      "https://api.render.com/v1/services/$SERVICE_ID/logs" \
#      | jq -r '.[] | "\(.timestamp) | \(.message)"' 2>/dev/null