#!/bin/bash

# Enable strict mode and safety guards
set -euo pipefail
IFS=$'\n\t'

# Error handling
trap 'echo "Error on line $LINENO. Exit code: $?" >&2' ERR
trap 'echo "Received interrupt signal. Exiting..." >&2; exit 1' INT TERM

# Default branch if not provided
TARGET_BRANCH=${1:-main}

# Validate required environment variables
if [[ -z "${RENDER_DEPLOY_URL:-}" ]]; then
    echo "Error: RENDER_DEPLOY_URL environment variable is not set" >&2
    exit 1
fi

# Check for changes
if git diff-index --quiet HEAD --; then
    echo "No changes to commit"
    exit 0
fi

# Check for potential secrets (basic check)
if git diff --cached | grep -i "key\|secret\|password\|token" > /dev/null; then
    echo "Warning: Potential secrets detected in changes. Use --force to override" >&2
    if [[ "${FORCE_PUSH:-}" != "true" ]]; then
        exit 1
    fi
fi

# Stage only specific files
git add render.yaml

# Commit changes if any
if ! git diff --cached --quiet; then
    git commit -m "Update CORS and environment settings"
    
    # Push changes
    echo "Pushing changes to $TARGET_BRANCH..."
    git push origin "$TARGET_BRANCH"
else
    echo "No changes to commit"
fi

# Deploy to Render
echo "Deploying to Render..."
DEPLOY_RESPONSE=$(curl -s -w "%{http_code}" -X POST "$RENDER_DEPLOY_URL")
HTTP_STATUS=${DEPLOY_RESPONSE: -3}

if [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]]; then
    echo "Deployment triggered successfully"
else
    echo "Error: Deployment failed with status $HTTP_STATUS" >&2
    echo "Response: ${DEPLOY_RESPONSE%???}" >&2
    exit 1
fi