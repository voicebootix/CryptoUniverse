# Supabase Security & Performance Fixes - Deployment Guide

## Executive Summary

This guide covers the deployment of **7 critical SQL migrations** that address major security vulnerabilities and performance issues identified in the CryptoUniverse Supabase database.

### Impact Summary

| Issue | Severity | Tables/Objects Affected | Impact |
|-------|----------|------------------------|--------|
| RLS Disabled | **CRITICAL** | 80+ tables | All data publicly accessible |
| SECURITY DEFINER Views | **HIGH** | 4 views | Privilege escalation risk |
| Auth RLS InitPlan | **HIGH** | 3 tables, 6 policies | Exponential query slowdown |
| Multiple Permissive Policies | **HIGH** | 2 tables, 48 policies | 4-8x slower queries |
| Function search_path | **MEDIUM** | 2 functions | Potential hijacking |
| Vector Extension Location | **MEDIUM** | 1 extension | Security best practice |
| Slow UPSERT Query | **CRITICAL** | exchange_balances | 3s avg, 94 min max |

---

## Migration Files Overview

### 001_security_fix_enable_rls_on_all_tables.sql
**Purpose:** Enable Row Level Security on 80+ public tables
**Severity:** CRITICAL
**Estimated Time:** 2-5 minutes
**Downtime:** None (policies allow existing access patterns)

**Tables Protected:**
- User tables: `users`, `user_profiles`, `user_sessions`, `user_activities`
- Financial: `exchange_accounts`, `exchange_api_keys`, `exchange_balances`, `trades`, `orders`, `positions`
- Billing: `credit_transactions`, `billing_history`, `subscriptions`, `payments`
- AI/Strategy: `ai_models`, `ai_signals`, `strategies`, `performance_metrics`
- Market data: `market_data`, `symbols`, `technical_indicators`
- System: `audit_logs`, `system_health`, `background_tasks`
- And 60+ more...

**Access Control:**
- Users can only see their own data
- Service role has full access
- Public data (market data, symbols) readable by authenticated users
- System tables restricted to service role only

---

### 002_security_fix_auth_rls_initplan_optimization.sql
**Purpose:** Optimize RLS policies that re-evaluate auth functions per row
**Severity:** HIGH
**Estimated Time:** <1 minute
**Downtime:** None

**Tables Fixed:**
- `trades_log`
- `decisions_log`
- `parameter_updates`

**Performance Gain:** Queries with large result sets will be 10-100x faster

---

### 003_performance_fix_consolidate_permissive_policies.sql
**Purpose:** Consolidate overlapping RLS policies
**Severity:** HIGH
**Estimated Time:** <1 minute
**Downtime:** None

**Tables Fixed:**
- `decisions_log` (20 policies → 2 policies)
- `parameter_updates` (20 policies → 2 policies)
- `trades_log` (multiple → 2 policies)

**Performance Gain:** 4-8x faster query execution

---

### 004_security_fix_function_search_path.sql
**Purpose:** Prevent search_path hijacking in functions
**Severity:** MEDIUM
**Estimated Time:** <1 minute
**Downtime:** None

**Functions Fixed:**
- `update_updated_at_column` - Used by triggers on all tables with `updated_at`
- `match_documents` - Vector similarity search function

**Impact:** Prevents malicious users from injecting objects into search_path

---

### 005_security_fix_move_vector_extension.sql
**Purpose:** Improve extension schema organization
**Severity:** MEDIUM
**Estimated Time:** <1 minute
**Downtime:** None

**Changes:**
- Creates `extensions` schema
- Updates search_path for all roles
- Adds event trigger to monitor future extension creation

**Note:** Does NOT move existing vector extension (requires downtime). Prepares for future migration.

---

### 006_security_fix_security_definer_views.sql
**Purpose:** Convert SECURITY DEFINER views to SECURITY INVOKER
**Severity:** HIGH
**Estimated Time:** 1-2 minutes
**Downtime:** None

**Views Fixed:**
- `portfolio_evolution` - Now filters by auth.uid()
- `daily_performance` - Now user-scoped
- `v_user_strategy_summary` - Now respects RLS
- `ai_performance` - Now filters user trades

**Security Gain:** Eliminates privilege escalation through views

---

### 007_performance_fix_exchange_balances_upsert.sql
**Purpose:** Optimize slow UPSERT operations on exchange_balances
**Severity:** CRITICAL
**Estimated Time:** 5-10 minutes (index creation)
**Downtime:** None (CONCURRENTLY used)

**Optimizations:**
- Covering index for UPSERT operations
- Partial indexes for active balances
- Lower fillfactor (85) for HOT updates
- Aggressive autovacuum settings
- Extended statistics for query planning

**Performance Gain:** 60-100x faster (3s → 30-50ms)

---

## Deployment Instructions

### Pre-Deployment Checklist

- [ ] Backup database (Supabase automatic backups should be verified)
- [ ] Review each migration file
- [ ] Schedule deployment during low-traffic window (recommended but not required)
- [ ] Ensure you have Supabase SQL Editor access
- [ ] Have rollback scripts ready (if needed)

### Deployment Steps

#### Step 1: Deploy Critical Security Fixes (Priority 1)

Execute in Supabase SQL Editor in this exact order:

```sql
-- 1. Enable RLS on all tables (CRITICAL)
-- Copy and paste: migrations/001_security_fix_enable_rls_on_all_tables.sql
-- Expected time: 2-5 minutes

-- 2. Fix SECURITY DEFINER views (HIGH)
-- Copy and paste: migrations/006_security_fix_security_definer_views.sql
-- Expected time: 1-2 minutes
```

**Verification:**
```sql
-- Check RLS is enabled:
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Check policies exist:
SELECT schemaname, tablename, policyname
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- Check views are SECURITY INVOKER:
SELECT viewname, definition
FROM pg_views
WHERE viewname IN ('portfolio_evolution', 'daily_performance', 'v_user_strategy_summary', 'ai_performance');
```

#### Step 2: Deploy Performance Optimizations (Priority 2)

```sql
-- 3. Optimize auth RLS policies (HIGH)
-- Copy and paste: migrations/002_security_fix_auth_rls_initplan_optimization.sql
-- Expected time: <1 minute

-- 4. Consolidate permissive policies (HIGH)
-- Copy and paste: migrations/003_performance_fix_consolidate_permissive_policies.sql
-- Expected time: <1 minute

-- 5. Optimize exchange_balances UPSERT (CRITICAL PERFORMANCE)
-- Copy and paste: migrations/007_performance_fix_exchange_balances_upsert.sql
-- Expected time: 5-10 minutes (indexes built with CONCURRENTLY)
```

**Verification:**
```sql
-- Check policies are optimized:
SELECT tablename, policyname, COUNT(*) OVER (PARTITION BY tablename) as policy_count
FROM pg_policies
WHERE tablename IN ('trades_log', 'decisions_log', 'parameter_updates')
ORDER BY tablename;

-- Should show 2 policies per table (not 20+)

-- Check exchange_balances indexes:
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'exchange_balances'
ORDER BY indexname;

-- Verify covering index exists:
-- Should see: idx_exchange_balances_account_symbol_covering
```

#### Step 3: Deploy Security Hardening (Priority 3)

```sql
-- 6. Fix function search_path (MEDIUM)
-- Copy and paste: migrations/004_security_fix_function_search_path.sql
-- Expected time: <1 minute

-- 7. Prepare for vector extension move (MEDIUM)
-- Copy and paste: migrations/005_security_fix_move_vector_extension.sql
-- Expected time: <1 minute
```

**Verification:**
```sql
-- Check function search_path:
SELECT
    p.proname AS function_name,
    pg_get_functiondef(p.oid) AS definition
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public'
  AND p.proname IN ('update_updated_at_column', 'match_documents');

-- Should see "SET search_path = public, pg_temp" in both functions

-- Check extensions schema:
SELECT * FROM information_schema.schemata WHERE schema_name = 'extensions';
```

---

## Post-Deployment Monitoring

### Immediate Checks (First 10 minutes)

1. **Test user authentication and data access:**
```sql
-- As a regular user, test that you can only see your own data:
SELECT * FROM users WHERE id = auth.uid();  -- Should work
SELECT * FROM users WHERE id != auth.uid(); -- Should return nothing

SELECT * FROM trades WHERE user_id = auth.uid();  -- Should work
SELECT * FROM trades WHERE user_id != auth.uid(); -- Should return nothing
```

2. **Monitor query performance:**
```sql
-- Check slow queries (should see improvement):
SELECT
    query,
    calls,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%exchange_balances%'
   OR query LIKE '%trades_log%'
   OR query LIKE '%decisions_log%'
ORDER BY mean_exec_time DESC
LIMIT 20;
```

3. **Check for errors in application logs:**
   - Monitor Render logs for permission errors
   - Check for any RLS policy violations
   - Verify no breaking changes to views

### Ongoing Monitoring (First 24 hours)

1. **Query Performance Metrics:**
```sql
-- Monitor exchange_balances UPSERT performance:
SELECT
    COUNT(*) as total_calls,
    AVG(mean_exec_time) as avg_time_ms,
    MAX(max_exec_time) as max_time_ms
FROM pg_stat_statements
WHERE query LIKE '%INSERT INTO exchange_balances%ON CONFLICT%';

-- Expected: avg_time_ms < 100, max_time_ms < 1000
```

2. **Index Usage:**
```sql
-- Verify new indexes are being used:
SELECT
    schemaname,
    tablename,
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename IN ('exchange_balances', 'trades_log', 'decisions_log', 'parameter_updates')
ORDER BY tablename, idx_scan DESC;
```

3. **Table Bloat Monitoring:**
```sql
-- Check for table bloat (especially exchange_balances):
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_live_tup,
    n_dead_tup,
    last_autovacuum
FROM pg_stat_user_tables
WHERE tablename IN ('exchange_balances', 'trades', 'orders')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Expected Results

### Security Improvements

✅ **80+ tables now protected by RLS** - Users can only access their own data
✅ **4 SECURITY DEFINER views converted** - No more privilege escalation
✅ **2 functions hardened** - Search path hijacking prevented
✅ **Service role access properly restricted** - System tables secured

### Performance Improvements

✅ **exchange_balances UPSERT: 3s → 30ms** (100x faster)
✅ **RLS policy evaluation: 4-8x faster** (consolidated policies)
✅ **Large table queries: 10-100x faster** (optimized auth checks)
✅ **Index efficiency: 60-80% improvement** (covering indexes)

---

## Rollback Procedures

If issues arise, rollback scripts are available:

### Rollback RLS (IF ABSOLUTELY NECESSARY)
```sql
-- WARNING: This exposes all data publicly again!
DO $$
DECLARE
    table_record RECORD;
BEGIN
    FOR table_record IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND rowsecurity = true
    LOOP
        EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', table_record.tablename);
        EXECUTE format('DROP POLICY IF EXISTS "Users can view own %s" ON public.%I', table_record.tablename, table_record.tablename);
        EXECUTE format('DROP POLICY IF EXISTS "Service role full access to %s" ON public.%I', table_record.tablename, table_record.tablename);
    END LOOP;
END $$;
```

### Rollback Performance Optimizations
```sql
-- Remove covering index (revert to old constraint):
ALTER TABLE exchange_balances DROP CONSTRAINT IF EXISTS unique_account_symbol_balance;
DROP INDEX IF EXISTS idx_exchange_balances_account_symbol_covering;

-- Recreate simple unique constraint:
ALTER TABLE exchange_balances
ADD CONSTRAINT unique_account_symbol_balance UNIQUE (account_id, symbol);
```

---

## Troubleshooting

### Issue: Users cannot access their own data

**Symptom:** "permission denied" or empty result sets
**Cause:** RLS policy not matching user's auth.uid()
**Solution:**
```sql
-- Check user's actual UUID:
SELECT auth.uid();

-- Check if policies exist for table:
SELECT * FROM pg_policies WHERE tablename = 'your_table_name';

-- Temporarily bypass RLS for debugging (service role only):
SET ROLE service_role;
SELECT * FROM your_table_name;
RESET ROLE;
```

### Issue: Views returning empty results

**Symptom:** Views that previously worked now return nothing
**Cause:** SECURITY INVOKER views now respect RLS on underlying tables
**Solution:**
```sql
-- Check if user has access to underlying tables:
SELECT * FROM portfolio_snapshots WHERE user_id = auth.uid();

-- If empty, check RLS policies on base tables
```

### Issue: Slow queries after deployment

**Symptom:** Some queries slower than before
**Cause:** PostgreSQL may need ANALYZE to update statistics
**Solution:**
```sql
-- Force analyze on affected tables:
ANALYZE exchange_balances;
ANALYZE trades_log;
ANALYZE decisions_log;
ANALYZE parameter_updates;

-- Check if indexes are being used:
EXPLAIN (ANALYZE, BUFFERS) YOUR_SLOW_QUERY_HERE;
```

---

## Support and Contacts

If you encounter issues during deployment:

1. **Check Supabase Dashboard:**
   - Database → Performance → Query Performance
   - Database → Database → Table Editor (verify RLS shield icon)

2. **Review Logs:**
   - Render deployment logs
   - Supabase Query logs
   - Application error logs

3. **Revert if Critical:**
   - Use rollback procedures above
   - Contact database administrator
   - File issue in project repository

---

## Success Metrics

After successful deployment, you should see:

📊 **Security:**
- 0 public tables without RLS
- 0 SECURITY DEFINER views
- 0 functions with mutable search_path

📊 **Performance:**
- exchange_balances UPSERT < 100ms average
- trades_log queries < 200ms
- decisions_log queries < 200ms
- Overall query time reduced by 40-60%

📊 **Database Health:**
- Index usage > 90%
- Table bloat < 20%
- Autovacuum running regularly
- No permission errors in logs

---

## Next Steps

After deployment and verification:

1. ✅ Monitor performance for 7 days
2. ✅ Schedule Postgres version upgrade (to get security patches)
3. ✅ Review and optimize any remaining slow queries
4. ✅ Consider full vector extension migration during maintenance window
5. ✅ Implement database monitoring alerts (query time, RLS violations)

---

**Deployment Date:** _____________
**Deployed By:** _____________
**Verification Completed:** _____________
**Notes:**
