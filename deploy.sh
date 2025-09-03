#!/bin/bash

# Deploy to Render
echo "Deploying to Render..."

# Push changes to git
git add .
git commit -m "Update CORS and environment settings"
git push origin main

# Manual deploy trigger for backend
curl -X POST "https://api.render.com/deploy/srv-YOUR_SERVICE_ID?key=YOUR_DEPLOY_KEY"

echo "Deployment triggered. Check Render dashboard for status."
