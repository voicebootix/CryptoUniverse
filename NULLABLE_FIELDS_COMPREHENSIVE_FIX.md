# Nullable Fields Comprehensive Fix

## Issue Identified
The `_scan_spot_momentum_opportunities` (and other scanners) were converting `risk_mgmt["take_profit"]` to a float without guarding against `None`. When the trading strategy service returns `null` for these fields, `float(None)` raises a `TypeError`, causing all opportunities to be dropped.

## Root Cause
Python's `dict.get("key", default)` returns `None` if the key exists with a `None` value, NOT the default. This means:
- `risk_mgmt.get("take_profit", 100)` returns `None` if `risk_mgmt["take_profit"]` is `None`
- `float(None)` raises `TypeError`

## Solution Applied
Changed all instances of `float(dict.get("key", default))` to `float(dict.get("key") or default)` throughout the file.

## Files Modified
- `/workspace/app/services/user_opportunity_discovery.py`

## Specific Fixes Applied (29 total):

### Critical Fix at Line 949 (Spot Momentum Scanner):
```python
# Before:
profit_potential_usd=float(risk_mgmt.get("take_profit", 100))

# After:
profit_potential_usd=float(risk_mgmt.get("take_profit") or 100)
```

### Other Key Fixes:
1. **All profit_potential_usd fields** - Fixed to handle None values
2. **All confidence_score fields** - Fixed to handle None values  
3. **All required_capital fields** - Fixed to handle None values
4. **Nested dictionary access** - Fixed pattern like `indicators.get("price", {}).get("current", 0)`

### Scanners Fixed:
- ✅ `_scan_spot_momentum_opportunities`
- ✅ `_scan_spot_mean_reversion_opportunities`
- ✅ `_scan_spot_breakout_opportunities`
- ✅ `_scan_scalping_opportunities`
- ✅ `_scan_pairs_trading_opportunities`
- ✅ `_scan_statistical_arbitrage_opportunities`
- ✅ `_scan_market_making_opportunities`
- ✅ `_scan_futures_trading_opportunities`
- ✅ `_scan_options_trading_opportunities`
- ✅ `_scan_portfolio_hedging_opportunities`
- ✅ `_scan_portfolio_rebalancing_opportunities`

## Impact
This fix ensures that when the trading strategy service returns `null` for numeric fields like `take_profit`, `stop_loss`, etc., the scanners will use the default values instead of crashing with `TypeError`. This should resolve the issue of 0 opportunities being returned.

## Testing Recommendations
After deployment:
1. Call `/api/v1/opportunities/discover` with `force_refresh: true`
2. Verify `total_opportunities` is greater than 0
3. Check that `opportunities` array contains actual opportunities
4. Monitor logs for any `TypeError` exceptions in scanners