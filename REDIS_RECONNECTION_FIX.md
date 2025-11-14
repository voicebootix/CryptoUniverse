# Redis Reconnection Fix for Opportunity Scan

## Problem Identified

After deploying previous fixes for the opportunity scan feature, Render logs showed intermittent warnings:
```
[warning] Failed to resolve scan cache key - Redis not available [UserOpportunityDiscoveryService] failure_reason=redis_not_available
```

## Root Cause

The `UserOpportunityDiscoveryService` initializes Redis once during `async_init()` and stores it in `self.redis`. However, in multi-worker environments (like Render), Redis connections can drop due to:
- Network transient issues
- Redis server restarts
- Connection pool exhaustion
- Worker restarts/redeployments

When `self.redis` becomes `None` or disconnected, the service would fail Redis operations without attempting to re-initialize the connection.

## Solution Implemented

### 1. Added `_ensure_redis_available()` Helper Method

A new method that:
- **Verifies connection**: Pings Redis to check if the existing client is still connected
- **Re-initializes on failure**: If Redis is `None` or disconnected, attempts to get a new client via `get_redis_client()`
- **Validates new connection**: Pings the new client to ensure it's working before returning
- **Returns boolean**: Indicates whether Redis is available for operations

**Location**: `app/services/user_opportunity_discovery.py` (lines 1266-1317)

### 2. Updated Critical Redis Operations

Updated the following methods to use `_ensure_redis_available()` instead of simple `if not self.redis:` checks:

1. **`_resolve_scan_cache_key()`** (line 822)
   - Used by status and results endpoints
   - Now attempts reconnection before failing

2. **`_register_scan_lookup()`** (line 642)
   - Persists lookup keys for cross-worker visibility
   - Critical for scan ID → cache key mapping

3. **`_update_cached_scan_result()`** (line 423)
   - Persists scan results to Redis
   - Critical for result storage

4. **`_get_cached_scan_entry()`** (line 345)
   - Retrieves cached scan results
   - Used by API endpoints

5. **`_peek_cached_scan_entry()`** (line 1086)
   - Alternative method for retrieving cached results
   - Also updated for consistency

## Benefits

1. **Automatic Recovery**: Service automatically recovers from transient Redis connection failures
2. **Multi-Worker Resilience**: Handles cases where Redis connection drops between requests
3. **Better Logging**: Provides detailed logging about reconnection attempts
4. **Graceful Degradation**: Still fails gracefully if Redis is truly unavailable, but only after attempting reconnection

## Testing Recommendations

1. **Monitor Render Logs**: Watch for "Redis client re-initialized successfully" messages indicating recovery
2. **Test Status Endpoint**: Verify `/opportunities/status/{scan_id}` works consistently
3. **Test Results Endpoint**: Verify `/opportunities/results/{scan_id}` works consistently
4. **Cross-Worker Testing**: If possible, test scans initiated on one worker and checked from another

## Expected Behavior

- **Before**: "Redis not available" warnings → "not_found" responses
- **After**: Automatic reconnection attempts → successful lookups if Redis recovers

## Deployment Notes

- No database migrations required
- No configuration changes required
- Backward compatible (gracefully degrades if Redis unavailable)
- Low performance impact (ping check is fast, ~2s timeout)
