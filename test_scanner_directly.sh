#!/bin/bash

echo "=== TESTING SCANNER EXECUTION DIRECTLY ==="

TOKEN=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Test with debug parameter if supported
echo "1. Testing with debug flag to see scanner execution:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit": 1, "debug": true}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
# Look for any debug info
if 'debug' in d:
    print('Debug info:', d['debug'])
if 'errors' in d:
    print('Errors:', d['errors'])
if 'warnings' in d:
    print('Warnings:', d['warnings'])
print('Strategy performance:', d.get('strategy_performance', {}))
"

echo
echo "2. Testing if scanners are even being called by checking execution time:"
START_TIME=$(date +%s)
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit": 1}' > /dev/null
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "Request took ${DURATION} seconds"

echo
echo "3. Check if we can access logs endpoint:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/admin/logs \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print('Logs response:', list(d.keys()) if isinstance(d, dict) else type(d))
except:
    print('No logs endpoint available')
"