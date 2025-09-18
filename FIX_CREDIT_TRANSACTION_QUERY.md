# Fix for CreditTransaction Query Error

## Problem
The code in `/workspace/app/api/v1/endpoints/credits.py` at line 640 is trying to query `CreditTransaction.reference_id`, but this column doesn't exist in the model. The correct field is `stripe_payment_intent_id`.

## Root Cause
This is preventing:
1. Credit account creation during onboarding
2. Strategy provisioning (due to "Insufficient credits")
3. Opportunity discovery (no strategies to scan with)

## Fix Required

### File: `/workspace/app/api/v1/endpoints/credits.py`
### Line: 640

**Current (broken):**
```python
tx_stmt = select(CreditTransaction).where(
    CreditTransaction.reference_id == payment_id
).with_for_update()
```

**Fixed:**
```python
tx_stmt = select(CreditTransaction).where(
    CreditTransaction.stripe_payment_intent_id == payment_id
).with_for_update()
```

## Impact
This single-line fix will:
1. ✅ Allow credit accounts to be created
2. ✅ Enable strategy provisioning 
3. ✅ Unblock opportunity discovery
4. ✅ Fix the "Onboarding failed: 'user_id'" error

## Deployment Priority
**CRITICAL** - This is blocking all functionality