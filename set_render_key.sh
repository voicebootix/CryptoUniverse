#!/bin/bash

# Replace with your actual Render API key
export RENDER_API_KEY="rnd_xxxxxxxxxxxxxxxxxxxx"

# Also set your service ID (find it in your Render dashboard URL)
# Example: If your dashboard URL is https://dashboard.render.com/web/srv-abc123xyz
# Then your service ID is: srv-abc123xyz
export RENDER_SERVICE_ID="srv-your-service-id-here"

echo "Render API key and Service ID set for this session"
echo "You can now run: ./fetch_render_logs.sh"