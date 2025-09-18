# Nullable Fields Fix for Opportunity Discovery

## Problem
The opportunity scanners are failing because they try to convert `null` values to float, causing TypeErrors. When the API returns `{"take_profit": null}`, the code `float(risk_mgmt.get("take_profit", 100))` still tries to convert `None` to float because `get()` returns the actual value (None), not the default.

## Root Cause
`dict.get(key, default)` only returns the default if the key is MISSING, not if it's present with a `None` value.

## Fix Required

### File: `/workspace/app/services/user_opportunity_discovery.py`

#### Line 949 - Critical Fix
```python
# Current (broken):
profit_potential_usd=float(risk_mgmt.get("take_profit", 100))

# Fixed:
profit_potential_usd=float(risk_mgmt.get("take_profit") or 100)
```

#### Line 955 - Already Safe
```python
# Current (already handles None):
exit_price=float(risk_mgmt.get("take_profit_price", 0)) if risk_mgmt.get("take_profit_price") else None
```
This is already safe because it checks truthiness before converting.

## Additional Considerations

### Other Potential Issues
The following lines use similar patterns but may be safe if the upstream data never returns null for these fields:
- Line 720: `float(opp.get("profit_potential", 0))`
- Line 781: `float(opp.get("profit_potential", 0))`
- Line 851: `float(signals.get("expected_profit", 0))`
- Line 1025: `float(signals.get("reversion_target", 0))`
- Line 1098: `float(signals.get("profit_potential", 0))`

### Recommended Pattern
For any field that might be null:
```python
# Instead of:
value = float(data.get("field", default))

# Use:
value = float(data.get("field") or default)
```

## Testing
After applying the fix, test with:
```bash
curl -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force_refresh": true}'
```

The response should show non-zero opportunities.