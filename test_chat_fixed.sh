#!/bin/bash

echo "=== TESTING CHAT AFTER FIXES ==="

# Test chat endpoint directly
curl -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy_token" \
  -d '{
    "message": "find opportunities",
    "user_id": "admin_user",
    "session_id": "test_session",
    "stream": false
  }' -s | jq '.'

echo -e "\n=== Chat should now work without NoneType errors ==="
