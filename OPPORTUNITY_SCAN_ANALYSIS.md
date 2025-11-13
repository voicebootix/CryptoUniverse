# Opportunity Scan Feature Analysis

## Test Results Summary

**Test Date:** 2025-11-12  
**Scan ID:** `scan_82aacbb97ca146e9a650ff50a51d55d6`  
**User ID:** `7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af`

### Scan Execution Status: ✅ SUCCESS

From server logs, the scan completed successfully:
- **Strategies Processed:** 14/14
- **Opportunities Found:** 19
- **Execution Time:** ~160 seconds (2.67 minutes)
- **Status:** Completed and persisted to Redis
- **Cache Key:** `7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af:b7131f12a6b6595f`
- **Redis Persistence:** Successfully persisted with `partial=False`

### Issues Identified

#### 1. Intermittent "not_found" Status Responses ⚠️

**Symptom:** Status endpoint intermittently returns `"status": "not_found"` even after scan completion.

**Observed Pattern:**
- Polls 1-8: Status = "scanning" (0/14 strategies)
- Poll 9: Status = "not_found"
- Polls 10-14: Status = "scanning" (0/14 strategies)
- Polls 15-19: Mix of "scanning" and "not_found"
- Polls 20-35: Mix of "scanning" and "not_found"
- Polls 35+: Status = "complete" but with 0/0 strategies

**Root Cause Analysis:**
- The status endpoint uses `_get_cached_scan_entry()` which calls `_resolve_scan_cache_key()`
- `_resolve_scan_cache_key()` checks:
  1. In-memory lookup (`self._scan_lookup`)
  2. Redis lookup (`opportunity_scan_lookup:{scan_id}`)
  3. User's latest scan (`opportunity_user_latest_scan:{user_id}`)
- The intermittent "not_found" suggests:
  - Cross-worker visibility issues (different workers handling requests)
  - Redis lookup may be failing intermittently
  - Cache key resolution may be timing out

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

#### 2. Results Endpoint Returns 404 ❌

**Symptom:** After scan completion, `/api/v1/opportunities/results/{scan_id}` returns 404.

**Error Message:**
```
"No scan results found. Please initiate a new scan."
```

**Root Cause Analysis:**
- The results endpoint uses the same `_get_cached_scan_entry()` method
- If `_resolve_scan_cache_key()` fails, `cached_entry` is `None`
- This triggers the 404 response

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

#### 3. Status Shows 0/0 Strategies After Completion ⚠️

**Symptom:** When status returns "complete", it shows `strategies_completed: 0` and `total_strategies: 0`.

**Root Cause Analysis:**
- The status endpoint may be returning a cached placeholder instead of the final result
- The metadata may not be properly populated in the cached entry

## Feature Validation

### ✅ What Works Correctly

1. **Scan Initiation:** Successfully initiates background scan
2. **Background Processing:** All 14 strategies are processed
3. **Opportunity Discovery:** 19 opportunities found and ranked
4. **Redis Persistence:** Results are persisted to Redis
5. **Scan Completion:** Scan lifecycle properly tracked

### ❌ What Needs Fixing

1. **Cross-Worker Lookup:** Redis lookup may be failing intermittently
2. **Results Retrieval:** Results endpoint cannot find completed scans
3. **Status Metadata:** Progress metadata not properly populated in status responses

## Recommendations

### Priority 1: Fix Results Retrieval

**Issue:** Results endpoint cannot find completed scans.

**Solution:**
1. Add fallback logic in `_resolve_scan_cache_key()` to search Redis directly for scan results
2. Add logging to track when Redis lookups fail
3. Consider increasing Redis TTL for completed scans (currently 300s = 5 minutes)

**Code Changes:**
```python
# In _resolve_scan_cache_key, add fallback:
if not cache_key and scan_id:
    # Try to find cache_key from Redis scan result directly
    pattern = f"opportunity_scan_result:*"
    # Search Redis for matching scan_id in cached results
```

### Priority 2: Fix Status Endpoint Reliability

**Issue:** Status endpoint intermittently returns "not_found".

**Solution:**
1. Add retry logic for Redis lookups
2. Improve error handling in `_resolve_scan_cache_key()`
3. Add fallback to check if scan is still active via `has_active_scan_task()`

### Priority 3: Fix Status Metadata

**Issue:** Status shows 0/0 strategies after completion.

**Solution:**
1. Ensure metadata is properly populated when scan completes
2. Verify that `cached_entry.payload.get("metadata")` contains correct values

## Codebase Understanding

### Key Components

1. **API Endpoints** (`app/api/v1/endpoints/opportunity_discovery.py`):
   - `POST /discover`: Initiates scan
   - `GET /status/{scan_id}`: Checks scan status
   - `GET /results/{scan_id}`: Retrieves final results

2. **Service Layer** (`app/services/user_opportunity_discovery.py`):
   - `discover_opportunities_for_user()`: Main discovery logic
   - `_get_cached_scan_entry()`: Retrieves cached scan results
   - `_resolve_scan_cache_key()`: Resolves scan_id to cache_key
   - `_register_scan_lookup()`: Registers scan_id → cache_key mapping

3. **Caching Strategy**:
   - In-memory cache: `self.opportunity_cache`
   - Redis cache: `opportunity_scan_result:{cache_key}`
   - Redis lookup: `opportunity_scan_lookup:{scan_id}` → `cache_key`
   - Redis user lookup: `opportunity_user_latest_scan:{user_id}` → `cache_key`

### Data Flow

1. **Scan Initiation:**
   - User calls `POST /discover`
   - Creates `scan_id` and `cache_key`
   - Registers lookup: `scan_id` → `cache_key` (in-memory + Redis)
   - Starts background task

2. **Scan Processing:**
   - Background task processes 14 strategies
   - Results stored in Redis with `partial=True` initially
   - Final results stored with `partial=False`

3. **Status Polling:**
   - User calls `GET /status/{scan_id}`
   - Resolves `scan_id` → `cache_key` via `_resolve_scan_cache_key()`
   - Retrieves cached entry via `_get_cached_scan_entry()`
   - Returns status and progress

4. **Results Retrieval:**
   - User calls `GET /results/{scan_id}`
   - Same lookup process as status
   - Returns full results if `partial=False`

## Conclusion

The opportunity scan feature **works correctly** for discovering opportunities, but has **reliability issues** with:
1. Cross-worker visibility (Redis lookups)
2. Results retrieval after completion
3. Status metadata population

The core discovery logic is sound, but the caching/lookup layer needs improvement for production reliability.

