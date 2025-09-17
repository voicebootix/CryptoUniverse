#!/bin/bash

echo "=== TESTING THE ACTUAL ERROR ==="

TOKEN=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Let's see what actually happens with the default
echo "Testing the exact code from line 949:"
python3 -c "
# Simulate what happens
risk_mgmt = {'stop_loss': None, 'take_profit': None, 'position_size': 0.01}

# Line 949: profit_potential_usd=float(risk_mgmt.get('take_profit', 100))
try:
    value = float(risk_mgmt.get('take_profit', 100))
    print(f'✅ With default, no error: {value}')
except Exception as e:
    print(f'❌ Error: {e}')

# But what if risk_mgmt itself is None?
risk_mgmt = None
try:
    value = float(risk_mgmt.get('take_profit', 100))
    print(f'Value: {value}')
except Exception as e:
    print(f'❌ Error when risk_mgmt is None: {e}')
"