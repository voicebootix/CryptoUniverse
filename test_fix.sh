#!/bin/bash
# Quick test to verify opportunities are now being generated

BASE_URL="https://cryptouniverse.onrender.com"
TOKEN="YOUR_TOKEN_HERE"

echo "Testing opportunity discovery after threshold fix..."

curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force_refresh":true}' | \
  python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Opportunities found: {data.get(\"total_opportunities\", 0)}')"
