# Simple Explanation: Why You're Getting 0 Opportunities

## What's Happening

### Before Filters (It Worked):
1. You click "Scan Opportunities"
2. System scans ALL your strategies for ALL available assets
3. You get opportunities ✅

### After Adding Filters (It Stopped Working):
1. You click "Scan Opportunities" 
2. **You select filters** (tier levels, assets, strategies) from the UI
3. System filters everything FIRST, then scans only what matches
4. **If filters don't match anything → 0 opportunities** ❌

## The Problem

When you select filters in the UI, the code does this:

```python
# Line 1260-1279 in user_opportunity_discovery.py
if asset_tiers:
    # Filter to ONLY these tiers
    discovered_assets = {tier: assets for tier, assets in discovered_assets.items() 
                         if tier.lower() in allowed_tiers}

if symbols:
    # Filter to ONLY these symbols  
    filtered_assets = [asset for asset in assets 
                      if asset.symbol.upper() in symbol_filter]

if strategy_ids:
    # Filter to ONLY these strategies
    filtered_strategies = [strategy for strategy in active_strategies 
                          if strategy matches filter]
```

**If ANY filter returns empty → 0 opportunities**

## Why It's Happening

### Possible Reasons:

1. **Empty Arrays Problem**: 
   - UI sends `[]` (empty array) instead of `None` when nothing selected
   - Code treats `[]` as "filter to nothing" instead of "don't filter"
   - Result: Everything gets filtered out

2. **Case Mismatch**:
   - UI sends `"Tier_Retail"` but code looks for `"tier_retail"` (lowercase)
   - Symbol format mismatch (UI sends "BTC" but assets stored as "BTC/USDT")

3. **Filter Values Don't Exist**:
   - UI shows tier options that don't match actual tier names in database
   - Strategy IDs don't match actual strategy IDs

4. **All Filters Applied Together**:
   - If you select Tier A AND Symbol B AND Strategy C
   - It needs to find something that matches ALL THREE
   - If even one doesn't match → 0 results

## The Fix Needed

The code should treat **empty arrays** as "no filter" (same as `None`):

```python
# CURRENT (BROKEN):
symbols = request.symbols or []  # Empty array = filter to nothing
if symbols:  # This is False for []
    # filter...

# SHOULD BE:
symbols = request.symbols if request.symbols else None  # Empty = None
if symbols:  # This checks if there are actual values
    # filter...
```

OR check if arrays are actually empty:

```python
if symbols and len(symbols) > 0:  # Only filter if has values
    # filter...
```

## Quick Test

Try scanning **WITHOUT selecting any filters** (leave everything blank/default):
- If this works → filters are the problem
- If this doesn't work → different problem
