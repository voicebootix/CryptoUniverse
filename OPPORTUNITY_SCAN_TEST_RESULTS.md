# Opportunity Scan Test Results - Post-Deployment

## Test Date: 2025-11-13
## Scan ID: `scan_743da51cf95c4399864b7a3408a0b21a`
## User ID: `7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af`

## Test Results Summary

### ✅ Scan Execution: SUCCESS
- **Strategies Processed:** 14/14 ✅
- **Opportunities Found:** 13 ✅
- **Execution Time:** ~160 seconds (2.67 minutes) ✅
- **Status:** Completed and persisted to Redis ✅
- **Cache Key:** `7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af:b7131f12a6b6595f` ✅

### ❌ Status Endpoint: INTERMITTENT FAILURES

**Pattern Observed:**
- Polls 1-3: Status = "not_found" (0/0 strategies)
- Polls 4-6: Status = "scanning" (0/14 strategies) ✅
- Polls 7-8: Status = "not_found" (0/0 strategies) ❌
- Polls 9-11: Status = "scanning" (0/14 strategies) ✅
- Polls 12-13: Status = "not_found" (0/0 strategies) ❌
- Polls 14-16: Status = "scanning" (0/14 strategies) ✅
- Polls 17-18: Status = "not_found" (0/0 strategies) ❌
- Polls 19-31: Mix of "scanning" and "not_found" ❌
- Polls 32-40: Status = "not_found" (0/0 strategies) ❌
- Poll 41: Status = "complete" (14/14 strategies, 13 opportunities) ✅
- Polls 42-60: Mix of "complete" and "not_found" ❌

**Success Rate:** ~50% (30/60 polls returned correct status)

### ❌ Results Endpoint: FAILURE

**Error:**
```text
404 Not Found: "No scan results found. Please initiate a new scan."
```

**Occurred:** After scan completion (poll 60)

## Root Cause Analysis

### Issue 1: Intermittent "not_found" Status

**Symptom:** Status endpoint returns "not_found" even after scan completion.

**Root Cause:**
- `_resolve_scan_cache_key()` is failing to find the scan_id mapping in Redis
- This happens when:
  1. Different workers handle different requests (cross-worker visibility issue)
  2. In-memory lookup cache (`self._scan_lookup`) is empty on the worker handling the request
  3. Redis lookup keys (`opportunity_scan_lookup:{scan_id}` or `opportunity_scan_result_index:{scan_id}`) are missing or expired
  4. Race condition where lookup keys are deleted before they're used

**Evidence from Logs:**
- Scan completed successfully at `07:43:12`
- Scan result persisted to Redis with cache_key `7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af:b7131f12a6b6595f`
- Multiple status endpoint calls returned 200 (success)
- But intermittent "not_found" responses suggest lookup keys are missing

**Code Flow:**
```python
# app/api/v1/endpoints/opportunity_discovery.py:310
cached_entry = await user_opportunity_discovery._get_cached_scan_entry(
    user_id_str,
    scan_id=scan_id,
)

# app/services/user_opportunity_discovery.py:326
async def _get_cached_scan_entry(self, user_id: str, scan_id: Optional[str] = None):
    cache_key = await self._resolve_scan_cache_key(user_id=user_id, scan_id=scan_id)
    if not cache_key:
        return None  # This causes "not_found"
```

### Issue 2: Results Endpoint 404

**Symptom:** Results endpoint returns 404 after scan completion.

**Root Cause:**
- Same as Issue 1: `_resolve_scan_cache_key()` fails to find the scan
- Results endpoint uses the same `_get_cached_scan_entry()` method
- If `cache_key` is `None`, the endpoint returns 404

**Code Flow:**
```python
# app/api/v1/endpoints/opportunity_discovery.py:422
cached_entry = await user_opportunity_discovery._get_cached_scan_entry(
    str(current_user.id),
    scan_id=scan_id,
)
if not cached_entry:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No scan results found. Please initiate a new scan."
    )
```

## What's Working

1. ✅ Scan execution completes successfully
2. ✅ Scan results are persisted to Redis
3. ✅ Status endpoint works ~50% of the time
4. ✅ When status endpoint works, it shows correct progress (14/14 strategies)

## What's Not Working

1. ❌ Status endpoint intermittently returns "not_found" (~50% failure rate)
2. ❌ Results endpoint returns 404 after scan completion
3. ❌ Cross-worker visibility is inconsistent

## Potential Fixes

### Fix 1: Ensure Lookup Keys Are Always Persisted

**Problem:** `_update_cached_scan_result` persists lookup keys, but `_register_scan_lookup` might not be called consistently.

**Solution:** Ensure `_register_scan_lookup` is called when scan is initiated, and verify lookup keys are persisted with sufficient TTL.

### Fix 2: Increase Lookup Key TTL

**Problem:** Lookup keys might be expiring before scan results.

**Solution:** Increase TTL for lookup keys to match or exceed scan result TTL.

**Current Code:**
```python
lookup_ttl = max(ttl_seconds, self._partial_cache_ttl, self._scan_cache_ttl) + 300
```

**Potential Issue:** If `ttl_seconds` is small (e.g., 60s for partial results), lookup TTL might be too short.

### Fix 3: Add Fallback Lookup Strategy

**Problem:** If primary lookup keys are missing, there's no fallback.

**Solution:** Add a fallback that searches Redis for scan results by scanning keys or using a different index.

**Current Fallback:** `opportunity_scan_result_index:{scan_id}` exists but might not be populated consistently.

### Fix 4: Add Logging for Lookup Failures

**Problem:** No visibility into why lookups are failing.

**Solution:** Add detailed logging in `_resolve_scan_cache_key` to track:
- Which lookup method was tried
- Why each lookup failed
- Redis key existence and TTL

## Recommendations

1. **Immediate:** Add detailed logging to `_resolve_scan_cache_key` to understand why lookups are failing
2. **Short-term:** Verify that `_register_scan_lookup` is being called when scans are initiated
3. **Medium-term:** Increase lookup key TTL to ensure they don't expire before scan results
4. **Long-term:** Implement a more robust fallback strategy for cross-worker visibility

## Conclusion

The opportunity scan **execution is working correctly**, but the **lookup mechanism has cross-worker visibility issues**. The fixes in `codex/fix-opportunity-scan-lookup-and-results` branch are partially working, but there's still an intermittent issue with Redis lookup keys not being found consistently across workers.

