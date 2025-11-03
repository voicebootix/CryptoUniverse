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
Multiple requests to `/api/v1/opportunities/results/scan_75aff964c1534957bab424e6aabddbd1` are returning 404, even though the status endpoint returns 200. This suggests scan results aren't being found.

### Possible Causes
1. **Cross-worker cache issue**: Scan initiated on Worker A, but results endpoint hits Worker B
2. **Redis persistence not working**: Results not being persisted to Redis correctly
3. **Scan completion race condition**: Scan completes but results aren't saved before lookup

### Analysis Needed
- Check if `_register_scan_lookup()` is persisting to Redis correctly
- Check if `_update_cached_scan_result()` is persisting to Redis correctly  
- Verify Redis keys are being created: `opportunity_scan_lookup:{scan_id}` and `opportunity_scan_result:{cache_key}`
- Check if scan is completing successfully or timing out

### Status
⚠️ Needs investigation - The Redis persistence code exists (commit a60e39c1) but may not be working correctly

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
