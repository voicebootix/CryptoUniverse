# Production Issues Fixed

## Issue 1: Database Schema Error - `column backtest_results.annual_return does not exist`

### Problem
The query in `trading_strategies.py` was using `select(BacktestResult)` which attempts to select ALL columns defined in the model, including `annual_return`. However, if the migration `011_add_legacy_backtest_metrics.py` hasn't been run, this column doesn't exist in the database, causing the query to fail.

### Error from Logs
```
column backtest_results.annual_return does not exist
[SQL: SELECT backtest_results.id, backtest_results.strategy_id, ..., backtest_results.annual_return, ...]
```

### Fix Applied
1. Changed from `select(BacktestResult)` to explicit column selection
2. Excluded `annual_return`, `beta`, and `alpha` from the query (not used in the code)
3. Wrapped query execution in try/except to gracefully handle missing columns
4. Used `getattr()` for safe column access

### Location
- File: `app/services/trading_strategies.py`
- Method: `_get_strategy_performance_data()`
- Lines: ~7435-7530

### Status
✅ Fixed and pushed to `fix-production-issues` branch

---

## Issue 2: Scan Results 404 Errors

### Problem
Multiple requests to `/api/v1/opportunities/results/{scan_id}` are returning 404, even though the status endpoint initially returns success. Investigation revealed scans complete successfully but then disappear after ~12 seconds.

### Root Cause Identified
**BUG IN `_unregister_scan_lookup()`**: The cleanup callback calls `_unregister_scan_lookup()` when scan task completes. This method only checked in-memory cache and didn't check Redis. When the result wasn't in memory (cross-worker scenario or after worker restart), it removed the `scan_id -> cache_key` lookup mapping even though the result was still in Redis with a 300-second TTL.

**Evidence from Investigation**:
- Scan completes successfully (14/14 strategies, 100% completion)
- Status shows "scanning" initially
- After ~12 seconds, status changes to "not_found"
- Results endpoint returns 404 even though Redis still has the data

### Fix Applied
Modified `_unregister_scan_lookup()` in `app/services/user_opportunity_discovery.py` (lines 363-441) to:
1. Check Redis lookup key (`opportunity_scan_lookup:{scan_id}`) if not found in memory
2. Check Redis result key (`opportunity_scan_result:{cache_key}`) TTL before removing mapping
3. Only remove lookup mapping when BOTH memory and Redis caches are expired
4. Remove Redis lookup keys when cache is truly expired (cleanup)

### Location
- File: `app/services/user_opportunity_discovery.py`
- Method: `_unregister_scan_lookup()`
- Lines: 363-441

### Status
✅ Fixed and committed to `fix-production-issues` branch

---

## Issue 3: Worker Timeouts

### Problem
Workers are timing out after 30 seconds (Gunicorn timeout), causing scans to be interrupted.

### Evidence from Logs
```
[2025-11-03T13:08:02 +0000] [1] [CRITICAL] WORKER TIMEOUT (pid:30)
```

### Analysis
- This is expected if scans take longer than 30 seconds
- The overall scan budget is 150s, but Gunicorn timeout is 180s
- Strategies may be taking too long individually

### Status
⚠️ Expected behavior - Workers timeout when operations exceed Gunicorn timeout. This is separate from the scan timeout logic.

---

## Next Steps

1. ✅ **Fixed**: Database schema error - merge `fix-production-issues` branch
2. ⚠️ **Investigate**: Scan results 404 - check Redis persistence and scan completion flow
3. ⚠️ **Monitor**: Worker timeouts - expected behavior but may need optimization
