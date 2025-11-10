# Fix Summary: Opportunity Scan Status Endpoint Race Condition

## Problem Identified

**Root Cause:** The status endpoint (`/opportunities/status/{scan_id}`) returns `"not_found"` immediately after scan initiation because the cache entry doesn't exist until the background task creates it (2+ seconds later).

## Evidence

### Test Results
```
Time 0.0s:  Scan initiated, lookup registered ✅
Time 0.1s:  Status endpoint called → Returns "not_found" ❌
Time 2.0s:  Background task creates cache entry ✅
Time 2.0s:  Status endpoint now works ✅
```

### Code Flow Evidence

1. **Lookup Registration** (Line 229) - ✅ Synchronous
   ```python
   await user_opportunity_discovery._register_scan_lookup(...)
   ```

2. **Cache Entry Creation** (Line 867 in background task) - ❌ Asynchronous (2+ seconds delay)
   ```python
   await self._update_cached_scan_result(...)  # Inside background task
   ```

3. **Status Endpoint Check** (Line 225) - ❌ Fails because cache entry doesn't exist
   ```python
   entry = self.opportunity_cache.get(cache_key)  # Returns None initially
   ```

## Solution Implemented

**Fix:** Create a placeholder cache entry synchronously before returning the scan_id.

### Code Change
**File:** `app/api/v1/endpoints/opportunity_discovery.py`  
**Location:** After line 233 (after lookup registration, before background task)

**Added:**
```python
# Create placeholder cache entry synchronously so status endpoint works immediately
# This fixes the race condition where status endpoint returns "not_found"
# because cache entry doesn't exist until background task creates it
placeholder_payload = {
    "success": True,
    "scan_id": scan_id,
    "user_id": user_id_str,
    "opportunities": [],
    "total_opportunities": 0,
    "metadata": {
        "scan_state": "initiated",
        "message": "Scan initiated, processing in background...",
        "strategies_completed": 0,
        "total_strategies": 14,
        "elapsed_seconds": 0
    },
    "user_profile": {},
    "strategy_performance": {},
    "asset_discovery": {},
    "strategy_recommendations": [],
    "execution_time_ms": 0,
    "last_updated": datetime.utcnow().isoformat()
}
await user_opportunity_discovery._update_cached_scan_result(
    cache_key,
    placeholder_payload,
    partial=True,
)
```

## How This Fixes the Problem

### Before Fix
```
Time 0.0s:  Lookup registered ✅
Time 0.0s:  scan_id returned ✅
Time 0.1s:  Status endpoint → Cache check → None → "not_found" ❌
Time 2.0s:  Background task creates cache entry ✅
```

### After Fix
```
Time 0.0s:  Lookup registered ✅
Time 0.0s:  Placeholder cache entry created ✅
Time 0.0s:  scan_id returned ✅
Time 0.1s:  Status endpoint → Cache check → Found! → "scanning" ✅
Time 2.0s:  Background task updates cache entry with progress ✅
```

## Expected Behavior After Fix

1. ✅ Status endpoint works immediately after scan initiation
2. ✅ Returns `"scanning"` status instead of `"not_found"`
3. ✅ Shows progress as background task updates cache entry
4. ✅ No timing gap - always works

## Testing

To verify the fix works:

1. Initiate a scan: `POST /opportunities/discover`
2. Immediately check status: `GET /opportunities/status/{scan_id}`
3. Should return `"scanning"` status (not `"not_found"`)

## Files Modified

- `app/api/v1/endpoints/opportunity_discovery.py` - Added placeholder cache entry creation

## Related Documentation

- `ROOT_CAUSE_ANALYSIS.md` - Detailed root cause analysis
- `PROBLEM_FLOW_DIAGRAM.md` - Visual flow diagrams
- `OPPORTUNITY_SCAN_TEST_REPORT.md` - Original test report
