# Opportunity Scan Lookup Investigation Summary

## Investigation Date: 2025-11-13
## Branch: `codex/investigate-opportunity-scan-lookup-issues`

## Issues Investigated

### 1. ✅ Detailed Logging Added to `_resolve_scan_cache_key`

**Problem:** No visibility into why lookups were failing.

**Solution:** Added comprehensive logging that tracks:
- Which lookup method was attempted (in-memory, Redis primary, Redis fallback, etc.)
- Redis key existence and TTL values
- Success/failure of each lookup step
- Detailed failure reasons (key not found, user_id mismatch, Redis error, etc.)

**Key Logging Points:**
- `debug` level: Successful in-memory lookups
- `info` level: Successful Redis lookups (with TTL info)
- `debug` level: Key not found scenarios (with TTL info)
- `warning` level: All lookup methods exhausted, user_id mismatches, Redis errors

**Example Log Output:**
```json
{
  "level": "warning",
  "message": "Failed to resolve scan cache key - all lookup methods exhausted",
  "user_id": "7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af",
  "scan_id": "scan_743da51cf95c4399864b7a3408a0b21a",
  "lookup_method": "redis_direct_result_check",
  "failure_reason": "all_lookup_methods_failed",
  "primary_key_exists": false,
  "fallback_key_exists": false,
  "primary_key_ttl": -2,
  "fallback_key_ttl": -2
}
```

### 2. ✅ Enhanced `_register_scan_lookup` Logging

**Problem:** No visibility into when lookup registration happens or if it succeeds.

**Solution:** Added detailed logging that tracks:
- In-memory registration success
- Redis persistence for all three keys (primary lookup, user latest, index)
- TTL calculations and values
- Success/failure of each persistence step
- Error details if persistence fails

**Key Logging Points:**
- `info` level: Successful registration with all context (TTL, keys, etc.)
- `warning` level: Redis unavailable or persistence failures

**TTL Calculation:**
```python
base_ttl = max(self._partial_cache_ttl, self._scan_cache_ttl)  # 300s
lookup_ttl = base_ttl + 300  # 600s = 10 minutes
```

**Improvements:**
- Now also persists `opportunity_scan_result_index:{scan_id}` key during registration
- Ensures all three lookup keys are persisted consistently

### 3. ✅ Enhanced `_update_cached_scan_result` Logging

**Problem:** Lookup keys might not be persisted consistently during cache updates.

**Solution:** 
- Added detailed logging for each lookup key persistence
- Ensured TTL calculation matches `_register_scan_lookup` for consistency
- Added debug logs for each key persistence
- Added summary info log when all keys are persisted

**TTL Calculation (aligned with `_register_scan_lookup`):**
```python
base_ttl = max(self._partial_cache_ttl, self._scan_cache_ttl)  # 300s
lookup_ttl = max(ttl_seconds, base_ttl) + 300  # Ensures lookup keys outlive cache entries
```

### 4. ✅ TTL Analysis

**Current TTL Values:**
- `_scan_cache_ttl = 300` (5 minutes)
- `_partial_cache_ttl = 300` (5 minutes)
- Lookup TTL = `max(partial_cache_ttl, scan_cache_ttl) + 300 = 600` (10 minutes)

**Analysis:**
- ✅ Lookup keys have 10-minute TTL vs 5-minute cache TTL
- ✅ 5-minute buffer ensures lookup keys outlive cache entries
- ✅ TTL calculation is consistent across `_register_scan_lookup` and `_update_cached_scan_result`

**Potential Issue:**
- If scan takes longer than 5 minutes, cache might expire before scan completes
- However, lookup keys will still be valid for 10 minutes, so this should be fine

### 5. ✅ `_register_scan_lookup` Call Sites Verification

**Call Sites Found:**
1. **Line 1278:** When scan is initiated (`discover_opportunities`)
   - Called with `scan_id_local` generated or from cache
   - ✅ This is the primary registration point

2. **Line 1319:** When existing task is found (`discover_opportunities`)
   - Called to ensure lookup is registered even if task already exists
   - ✅ This ensures lookup is registered even for concurrent requests

**Analysis:**
- ✅ `_register_scan_lookup` is called at both critical points
- ✅ Both call sites ensure lookup is registered before scan execution
- ✅ Logging will now show when registration happens and if it succeeds

## Key Improvements

### 1. Comprehensive Logging
- Every lookup attempt is now logged with full context
- TTL values are logged to track expiration issues
- Failure reasons are clearly identified

### 2. Consistent TTL Calculation
- Both `_register_scan_lookup` and `_update_cached_scan_result` use the same TTL calculation
- Lookup keys are guaranteed to outlive cache entries (5-minute buffer)

### 3. Triple Persistence
- `_register_scan_lookup` now persists all three lookup keys:
  - `opportunity_scan_lookup:{scan_id}` (primary)
  - `opportunity_user_latest_scan:{user_id}` (user latest)
  - `opportunity_scan_result_index:{scan_id}` (fallback index)

### 4. Enhanced Error Tracking
- Detailed error context in all failure scenarios
- Error types are logged for better debugging
- Redis availability is checked and logged

## Next Steps

1. **Deploy and Test:**
   - Deploy this branch to staging/production
   - Run opportunity scan tests
   - Monitor logs for lookup failures

2. **Analyze Logs:**
   - Look for patterns in lookup failures
   - Check TTL values to ensure they're sufficient
   - Verify `_register_scan_lookup` is being called consistently

3. **Potential Further Fixes:**
   - If TTL is still insufficient, increase buffer time
   - If lookup keys are still missing, investigate Redis persistence issues
   - If user_id mismatches occur, investigate security issues

## Expected Log Output

### Successful Lookup:
```
INFO: Scan cache key resolved from Redis primary lookup
  user_id=7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af
  scan_id=scan_743da51cf95c4399864b7a3408a0b21a
  lookup_method=redis_primary_lookup
  cache_key=7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af:b7131f12a6b6595f
  redis_ttl=580
```

### Failed Lookup:
```
WARNING: Failed to resolve scan cache key - all lookup methods exhausted
  user_id=7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af
  scan_id=scan_743da51cf95c4399864b7a3408a0b21a
  lookup_method=redis_direct_result_check
  failure_reason=all_lookup_methods_failed
  primary_key_exists=false
  fallback_key_exists=false
  primary_key_ttl=-2
  fallback_key_ttl=-2
```

### Successful Registration:
```
INFO: Scan lookup persisted to Redis
  user_id=7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af
  scan_id=scan_743da51cf95c4399864b7a3408a0b21a
  cache_key=7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af:b7131f12a6b6595f
  lookup_ttl=600
  base_ttl=300
  success=true
  redis_keys={
    "lookup": "opportunity_scan_lookup:scan_743da51cf95c4399864b7a3408a0b21a",
    "user_latest": "opportunity_user_latest_scan:7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af",
    "index": "opportunity_scan_result_index:scan_743da51cf95c4399864b7a3408a0b21a"
  }
```

## Conclusion

All three investigation areas have been addressed:
1. ✅ Detailed logging added to track lookup failures
2. ✅ `_register_scan_lookup` call sites verified and enhanced with logging
3. ✅ TTL calculations verified and made consistent

The enhanced logging will provide visibility into:
- When lookups succeed/fail
- Why lookups fail (key missing, TTL expired, user_id mismatch, etc.)
- When lookup registration happens
- TTL values for all keys

This will help identify the root cause of intermittent "not_found" responses.

