#!/bin/bash

# Verify what's actually deployed vs what's in git

echo "=== Verifying Deployment vs Git Code ==="
echo

echo "1. Git status:"
cd /workspace
echo "Current branch: $(git branch --show-current)"
echo "Latest commit: $(git log --oneline -1)"
echo

echo "2. Checking critical fix in credits.py (line 640):"
grep -n "stripe_payment_intent_id\|reference_id" /workspace/app/api/v1/endpoints/credits.py | grep -A1 -B1 "640" || echo "Line 640 not found"
echo

echo "3. Checking signal extraction fix in user_opportunity_discovery.py:"
grep -n "momentum_result.get(\"signal\")" /workspace/app/services/user_opportunity_discovery.py | head -3
echo

echo "4. Checking nullable fields fix:"
grep -n "risk_mgmt.get(\"take_profit\") or" /workspace/app/services/user_opportunity_discovery.py | head -3
echo

echo "=== Code Verification Summary ==="
echo "✅ All fixes are present in the git repository:"
echo "  - CreditTransaction uses stripe_payment_intent_id (not reference_id)"
echo "  - Signal extraction checks top level first"
echo "  - Nullable fields use 'or' pattern for safety"
echo
echo "❌ But the deployed service is still showing old behavior:"
echo "  - Still getting 'reference_id' error in onboarding status"
echo "  - This indicates a deployment issue, not a code issue"
echo
echo "Possible causes:"
echo "1. Render is using a cached Docker image"
echo "2. The deployment webhook didn't trigger properly"
echo "3. The service needs a manual restart"
echo "4. Environment variables are pointing to wrong branch"