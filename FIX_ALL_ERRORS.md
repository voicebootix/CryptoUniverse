# Fixing All CryptoUniverse Errors

Based on our testing, here are the errors and their fixes:

## 1. Admin Endpoints - AsyncSession Errors (500)

**Error**: `'AsyncSession' object has no attribute 'query'`
**Files**: `/app/api/v1/endpoints/admin.py`

### Issues Found:
- Line 458: `query = db.query(User)`
- Line 482-483: `db.query(User).filter(...).count()`
- Line 505: `db.query(CreditAccount).filter(...)`
- Line 511: `db.query(Trade).filter(...).count()`
- Line 555: `db.query(User).filter(...).first()`
- Line 588: `db.query(CreditAccount).filter(...)`
- Line 672: `db.query(User).filter(...)`
- Line 677: `db.query(Trade).filter(...)`

## 2. Trade Model Error (500)

**Error**: `type object 'Trade' has no attribute 'amount'`
**File**: `/app/api/v1/endpoints/admin.py`
- Line 134: `Trade.amount` should be `Trade.quantity`

## 3. Telegram Error (500)

**Error**: `name 'self' is not defined`
**File**: `/app/api/v1/endpoints/telegram.py`
- Remove all `self.` references in endpoint functions

## 4. Missing Routes (404)

Many endpoints return 404 because the deployed code doesn't match local code.
Need to ensure latest code is deployed.

Let me create the fixes now...