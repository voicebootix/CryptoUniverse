# Fixes for CryptoUniverse Endpoint Errors

## Issues Found During Testing

### 1. ❌ Admin Endpoints (500 Errors)
- **File**: `app/api/v1/endpoints/admin.py`
- **Error**: `'AsyncSession' object has no attribute 'query'`
- **Lines**: 458, 482, 483, 505, 511, 555, 588, 672, 677, 682, 741, 781

### 2. ❌ Telegram Endpoint (500 Error)
- **File**: `app/api/v1/endpoints/telegram.py`
- **Error**: `name 'self' is not defined`
- **Fix**: Remove `self.` references in function-based endpoints

### 3. ❌ Trade Model Error
- **File**: `app/api/v1/endpoints/admin.py`
- **Lines**: 134, 682
- **Fix**: Change `Trade.amount` to `Trade.quantity`

## Manual Fixes Required

### Fix 1: admin.py - Replace sync queries with async

**Line 458** - Replace:
```python
query = db.query(User)
```
With:
```python
from sqlalchemy import select
stmt = select(User)
# Then later: result = await db.execute(stmt)
```

**Lines 482-483** - Replace:
```python
active_count = db.query(User).filter(User.status == UserStatus.ACTIVE).count()
```
With:
```python
active_count_result = await db.execute(
    select(func.count()).select_from(User).filter(User.status == UserStatus.ACTIVE)
)
active_count = active_count_result.scalar()
```

**Line 505** - Replace:
```python
credit_account = db.query(CreditAccount).filter(
    CreditAccount.user_id == user.id
).first()
```
With:
```python
credit_result = await db.execute(
    select(CreditAccount).filter(CreditAccount.user_id == user.id)
)
credit_account = credit_result.scalar_one_or_none()
```

**Line 511** - Replace:
```python
trade_count = db.query(Trade).filter(Trade.user_id == user.id).count()
```
With:
```python
trade_count_result = await db.execute(
    select(func.count()).select_from(Trade).filter(Trade.user_id == user.id)
)
trade_count = trade_count_result.scalar()
```

### Fix 2: telegram.py - Remove self references

Search and replace all `self.` with nothing in the endpoint functions.

### Fix 3: Add missing /prices endpoint to market_analysis.py

Add this endpoint:
```python
@router.get("/prices")
async def get_market_prices(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get current market prices for all tracked symbols."""
    try:
        from app.services.market_data_feeds import market_data_feeds
        from datetime import datetime
        
        symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "MATIC"]
        prices = {}
        
        for symbol in symbols:
            price_data = await market_data_feeds.get_real_time_price(symbol)
            if price_data and price_data.get("success"):
                prices[symbol] = price_data
        
        return {
            "success": True,
            "prices": prices,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get market prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## Files Changed
1. `app/api/v1/endpoints/admin.py` - Fix async queries and Trade.quantity
2. `app/api/v1/endpoints/telegram.py` - Remove self references
3. `app/api/v1/endpoints/market_analysis.py` - Add /prices endpoint

## Testing
After applying these fixes:
1. Test admin endpoints return 200 instead of 500
2. Test telegram connect works
3. Test market/prices returns data