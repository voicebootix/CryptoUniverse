# Root Cause Analysis: Opportunity Scan Status Endpoint "not_found" Issue

## Problem Statement

The `/opportunities/status/{scan_id}` endpoint returns `"not_found"` immediately after scan initiation, even though:
- The scan was successfully initiated
- The scan_id is valid
- The lifecycle endpoint shows the scan is in progress
- The scan eventually completes successfully

## Evidence from Test Results

```
Test: Immediate status check (0.1s after initiation)
Result: Status = "not_found", Success = False
Lifecycle: ✅ Works correctly, shows scan in progress
Status becomes "scanning": After ~2 seconds
```

## Root Cause: Cache Entry Creation Timing

### The Problem Flow

1. **API Endpoint (`opportunity_discovery.py:229`)** - Synchronous lookup registration:
```python
# Line 229: Lookup is registered SYNCHRONOUSLY
await user_opportunity_discovery._register_scan_lookup(
    user_id_str,
    cache_key,
    scan_id,
)
```

2. **API Endpoint (`opportunity_discovery.py:255`)** - Background task scheduled:
```python
# Line 255: Background task scheduled (NOT awaited)
background_tasks.add_task(run_discovery_background)
```

3. **API Endpoint (`opportunity_discovery.py:258`)** - Returns immediately:
```python
# Line 258: Returns scan_id BEFORE cache entry exists
return {
    "success": True,
    "scan_id": scan_id,  # ← scan_id returned here
    ...
}
```

4. **Status Endpoint (`opportunity_discovery.py:298`)** - Tries to find cache entry:
```python
# Line 298: Tries to get cached entry
cached_entry = await user_opportunity_discovery._get_cached_scan_entry(
    str(current_user.id),
    scan_id=scan_id,
)

# Line 303: Returns "not_found" if cache entry doesn't exist
if not cached_entry:
    return {
        "success": False,
        "status": "not_found",  # ← Returns this!
        ...
    }
```

5. **Cache Entry Lookup (`user_opportunity_discovery.py:220`)** - Resolves cache key:
```python
# Line 220: Resolves cache_key from lookup (this works)
cache_key = await self._resolve_scan_cache_key(user_id=user_id, scan_id=scan_id)

# Line 225: Tries to get entry from in-memory cache (this fails!)
entry = self.opportunity_cache.get(cache_key)  # ← Returns None initially
```

6. **Background Task (`user_opportunity_discovery.py:867`)** - Creates cache entry LATER:
```python
# Line 867: Cache entry created INSIDE background task (2+ seconds later)
await self._update_cached_scan_result(
    cache_key,
    placeholder_payload,
    partial=True,  # ← Creates partial cache entry
)
```

### The Timing Gap

```
Time 0.0s:  API endpoint registers lookup (synchronous) ✅
Time 0.0s:  API endpoint returns scan_id ✅
Time 0.1s:  Status endpoint called
Time 0.1s:  Status endpoint finds lookup ✅
Time 0.1s:  Status endpoint checks cache ❌ (cache entry doesn't exist yet!)
Time 0.1s:  Status endpoint returns "not_found" ❌
Time 2.0s:  Background task creates cache entry ✅
Time 2.0s:  Status endpoint now works ✅
```

## Code Evidence

### 1. Lookup Registration (Synchronous)
**File:** `app/api/v1/endpoints/opportunity_discovery.py`
**Line:** 229
```python
await user_opportunity_discovery._register_scan_lookup(
    user_id_str,
    cache_key,
    scan_id,
)
```
✅ **This happens synchronously before returning scan_id**

### 2. Cache Entry Creation (Asynchronous)
**File:** `app/services/user_opportunity_discovery.py`
**Line:** 867
```python
await self._update_cached_scan_result(
    cache_key,
    placeholder_payload,
    partial=True,
)
```
❌ **This happens INSIDE the background task, 2+ seconds AFTER scan_id is returned**

### 3. Status Endpoint Cache Check
**File:** `app/services/user_opportunity_discovery.py`
**Line:** 225
```python
async with self._scan_cache_lock:
    entry = self.opportunity_cache.get(cache_key)  # ← In-memory cache
    if not isinstance(entry, _CachedOpportunityResult):
        return None  # ← Returns None if cache entry doesn't exist
```
❌ **This checks in-memory cache, which doesn't exist until background task runs**

### 4. Status Endpoint Failure Path
**File:** `app/api/v1/endpoints/opportunity_discovery.py`
**Line:** 303
```python
if not cached_entry:
    return {
        "success": False,
        "status": "not_found",  # ← This is what gets returned
        "message": "No scan found for this user. Please initiate a new scan."
    }
```

## Why Lifecycle Endpoint Works

The lifecycle endpoint uses **Redis** (persistent storage), not in-memory cache:

**File:** `app/api/v1/endpoints/scan_diagnostics.py`
**Line:** 397
```python
lifecycle_key = f"scan_lifecycle:{scan_id}"
lifecycle_data = await redis.hgetall(lifecycle_key)  # ← Redis, not in-memory
```

The lifecycle tracking is written to Redis **early** in the background task, so it's available immediately.

## The Real Problem

**The status endpoint depends on an in-memory cache entry that doesn't exist until the background task creates it.**

### Two Separate Systems:
1. **Lookup System** (`_scan_lookup` dict) - ✅ Synchronous, works immediately
2. **Cache System** (`opportunity_cache` dict) - ❌ Asynchronous, created later

The status endpoint needs BOTH:
- Lookup (to find cache_key) - ✅ Available immediately
- Cache entry (to get scan data) - ❌ Not available until background task runs

## Solution Options

### Option 1: Create Placeholder Cache Entry Synchronously (Recommended)
Create a minimal cache entry before returning scan_id:

```python
# In opportunity_discovery.py, after line 233:
placeholder_payload = {
    "success": True,
    "scan_id": scan_id,
    "user_id": user_id_str,
    "opportunities": [],
    "total_opportunities": 0,
    "metadata": {
        "scan_state": "initiated",
        "message": "Scan initiated, processing in background..."
    }
}
await user_opportunity_discovery._update_cached_scan_result(
    cache_key,
    placeholder_payload,
    partial=True,
)
```

### Option 2: Use Lifecycle as Fallback
Modify status endpoint to check lifecycle if cache entry not found:

```python
# In opportunity_discovery.py, after line 301:
if not cached_entry:
    # Fallback: Check lifecycle endpoint
    from app.core.redis import get_redis_client
    redis = await get_redis_client()
    if redis:
        lifecycle_key = f"scan_lifecycle:{scan_id}"
        lifecycle_data = await redis.hgetall(lifecycle_key)
        if lifecycle_data:
            return {
                "success": True,
                "status": "scanning",
                "scan_id": scan_id,
                "message": "Scan in progress (retrieved from lifecycle)",
                "progress": {"strategies_completed": 0, "total_strategies": 14}
            }
```

### Option 3: Use Redis for Cache (Long-term)
Move cache to Redis instead of in-memory for persistence across instances.

## Recommended Fix

**Option 1** is the cleanest solution - create a placeholder cache entry synchronously before returning the scan_id. This ensures the status endpoint works immediately while the background task processes the actual scan.

## Test Evidence Summary

| Check | Timing | Result | Evidence |
|-------|--------|--------|----------|
| Lookup registration | 0.0s | ✅ Works | Code line 229 executes synchronously |
| Cache entry creation | 2.0s+ | ❌ Delayed | Code line 867 executes in background task |
| Status endpoint (immediate) | 0.1s | ❌ Fails | Returns "not_found" |
| Status endpoint (after 2s) | 2.0s+ | ✅ Works | Cache entry now exists |
| Lifecycle endpoint | 0.1s | ✅ Works | Uses Redis, not in-memory cache |

## Conclusion

**The real problem is a timing issue:** The status endpoint requires an in-memory cache entry that isn't created until the background task runs (2+ seconds after scan initiation). The lookup registration works, but the cache entry creation is asynchronous, creating a gap where the status endpoint fails.

**Fix:** Create a placeholder cache entry synchronously before returning the scan_id from the API endpoint.
