# Opportunity Scan Diagnosis and Fix Plan

## Current Issue Summary

Based on the test results and code analysis:

1. **Intermittent "not_found" Status** (~50% failure rate)
   - Status endpoint returns "not_found" even after scan completion
   - Pattern: Alternates between "scanning" and "not_found"

2. **Results Endpoint 404**
   - Returns 404 after scan completion
   - Same root cause as status endpoint

3. **Cross-Worker Visibility Issues**
   - Different workers handle different requests
   - In-memory lookup cache (`self._scan_lookup`) is empty on worker handling the request
   - Redis lookup keys may be missing or expired

## Root Cause Analysis

### Issue 1: Race Condition in Lookup Key Registration

**Problem:** `_register_scan_lookup` is called at line 1470, but the placeholder is created at line 1537 (`_prime_scan_placeholder`). The placeholder creation also calls `_update_cached_scan_result` which persists lookup keys, but there's a timing window where:

1. Scan is initiated
2. `_register_scan_lookup` is called (persists lookup keys)
3. Status endpoint is called before placeholder is created
4. `_resolve_scan_cache_key` finds lookup keys but `_get_cached_scan_entry` returns None because placeholder doesn't exist yet

**Code Flow:**
```python
# Line 1470: Register lookup
await self._register_scan_lookup(user_id, cache_key, scan_id_local)

# Line 1537: Create placeholder (which also persists lookup keys)
placeholder_payload = await self._prime_scan_placeholder(...)
```

### Issue 2: TTL Calculation Inconsistency

**Problem:** Lookup TTL is calculated differently in `_register_scan_lookup` vs `_update_cached_scan_result`:

- `_register_scan_lookup` (line 658): `lookup_ttl = base_ttl + 300`
- `_update_cached_scan_result` (line 443): `lookup_ttl = max(ttl_seconds, base_ttl) + 300`

If `ttl_seconds` (partial cache TTL) is small, the lookup TTL might be inconsistent.

### Issue 3: Missing Lookup Keys on Status Check

**Problem:** When status endpoint is called:
1. `_get_cached_scan_entry` calls `_resolve_scan_cache_key`
2. If lookup keys don't exist in Redis (expired or not persisted), it returns None
3. Status endpoint returns "not_found"

**Code Flow:**
```python
# app/api/v1/endpoints/opportunity_discovery.py:313
cached_entry = await user_opportunity_discovery._get_cached_scan_entry(
    user_id_str,
    scan_id=scan_id,
)

# app/services/user_opportunity_discovery.py:331
cache_key = await self._resolve_scan_cache_key(user_id=user_id, scan_id=scan_id)
if not cache_key:
    return None  # This causes "not_found"
```

### Issue 4: Cross-Worker Cache Inconsistency

**Problem:** 
- Worker A initiates scan and creates lookup keys
- Worker B handles status request
- Worker B's in-memory cache is empty
- Worker B checks Redis but lookup keys might be missing/expired
- Returns "not_found"

## Proposed Fixes

### Fix 1: Ensure Lookup Keys Are Always Persisted Before Returning

**Location:** `app/services/user_opportunity_discovery.py:1470`

**Change:** Ensure `_register_scan_lookup` is called AND verified before proceeding.

```python
# After line 1470
await self._register_scan_lookup(user_id, cache_key, scan_id_local)

# Add verification
if self.redis:
    redis_lookup_key = f"opportunity_scan_lookup:{scan_id_local}"
    verify_key = await self.redis.get(redis_lookup_key)
    if not verify_key:
        self.logger.warning(
            "Lookup key not found after registration, retrying",
            scan_id=scan_id_local,
            cache_key=cache_key
        )
        await self._register_scan_lookup(user_id, cache_key, scan_id_local)
```

### Fix 2: Standardize TTL Calculation

**Location:** `app/services/user_opportunity_discovery.py:656-658` and `443`

**Change:** Create a helper method for consistent TTL calculation:

```python
def _calculate_lookup_ttl(self, cache_ttl: Optional[int] = None) -> int:
    """Calculate lookup TTL to ensure it outlives cache entries."""
    if cache_ttl is None:
        base_ttl = max(self._partial_cache_ttl, self._scan_cache_ttl)
    else:
        base_ttl = max(cache_ttl, self._partial_cache_ttl, self._scan_cache_ttl)
    return base_ttl + 300  # 5 minute buffer
```

### Fix 3: Add Fallback Lookup Strategy

**Location:** `app/services/user_opportunity_discovery.py:905-917`

**Change:** Implement Method 3 (direct result check) as a last resort:

```python
# Method 3: Check if result exists directly (last resort)
# Try to find any cache_key for this user that might contain the scan_id
lookup_context["lookup_method"] = "redis_direct_result_check"

# Search for scan results by scanning user's cache keys
if self.redis:
    try:
        # Use SCAN to find opportunity_scan_result keys for this user
        pattern = f"opportunity_scan_result:{user_id}:*"
        cursor = 0
        found_cache_key = None
        
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                # Get the result and check if scan_id matches
                result_data = await self.redis.get(key)
                if result_data:
                    try:
                        if isinstance(result_data, bytes):
                            result_data = result_data.decode('utf-8')
                        scan_data = json.loads(result_data)
                        payload = scan_data.get("payload", {})
                        if payload.get("scan_id") == scan_id:
                            found_cache_key = key.replace("opportunity_scan_result:", "")
                            break
                    except:
                        continue
            if cursor == 0 or found_cache_key:
                break
        
        if found_cache_key:
            # Restore lookup keys
            await self._register_scan_lookup(user_id, found_cache_key, scan_id)
            lookup_context["success"] = True
            self.logger.info(
                "Scan cache key resolved via direct result search",
                **lookup_context,
                cache_key=found_cache_key
            )
            return found_cache_key
    except Exception as scan_error:
        self.logger.debug(
            "Direct result search failed",
            **lookup_context,
            error=str(scan_error)
        )
```

### Fix 4: Add Enhanced Logging

**Location:** `app/services/user_opportunity_discovery.py:779-965`

**Change:** Add more detailed logging to track lookup failures:

```python
# Add at the start of _resolve_scan_cache_key
self.logger.debug(
    "Resolving scan cache key",
    user_id=user_id,
    scan_id=scan_id,
    in_memory_lookup_size=len(self._scan_lookup),
    redis_available=bool(self.redis)
)

# Add after each lookup method failure
self.logger.warning(
    "Lookup method failed",
    method=lookup_context["lookup_method"],
    reason=lookup_context.get("failure_reason"),
    user_id=user_id,
    scan_id=scan_id,
    redis_keys_checked=[
        f"opportunity_scan_lookup:{scan_id}" if scan_id else None,
        f"opportunity_scan_result_index:{scan_id}" if scan_id else None,
        f"opportunity_user_latest_scan:{user_id}"
    ]
)
```

### Fix 5: Increase Lookup Key TTL Buffer

**Location:** `app/services/user_opportunity_discovery.py:658`

**Change:** Increase buffer from 300s to 600s (10 minutes) to ensure lookup keys outlive cache entries even with delays:

```python
lookup_ttl = base_ttl + 600  # 600s = 10 minutes buffer (increased from 300s)
```

## Testing Plan

1. **Test Scan Initiation**
   - Verify lookup keys are created immediately
   - Check Redis for all three lookup keys
   - Verify TTL values

2. **Test Status Endpoint**
   - Call status endpoint immediately after initiation
   - Verify it returns "scanning" not "not_found"
   - Poll status endpoint multiple times
   - Verify no intermittent "not_found" responses

3. **Test Results Endpoint**
   - Wait for scan completion
   - Call results endpoint
   - Verify it returns results, not 404

4. **Test Cross-Worker**
   - Initiate scan on one worker
   - Check status/results from different worker
   - Verify lookup keys are found

## Immediate Actions

1. **Add logging** to `_resolve_scan_cache_key` to track why lookups fail
2. **Increase lookup TTL buffer** from 300s to 600s
3. **Add verification** after `_register_scan_lookup` to ensure keys are persisted
4. **Implement fallback lookup** strategy (Method 3)

## Monitoring

After fixes are deployed, monitor:
- Status endpoint success rate (should be >95%)
- Results endpoint success rate (should be >95%)
- Redis lookup key TTL values
- Log messages for "Failed to resolve scan cache key"
- Log messages for "all_lookup_methods_failed"
