#!/bin/bash

echo "Testing Live Service..."

# Get token
TOKEN=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Quick test
RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}')

echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Success:', d.get('success'))
print('Opportunities:', d.get('total_opportunities', 0))
print('Assets scanned:', d.get('asset_discovery', {}).get('total_assets_scanned', 0))
print('Execution time: {:.1f}s'.format(d.get('execution_time_ms', 0)/1000))
"