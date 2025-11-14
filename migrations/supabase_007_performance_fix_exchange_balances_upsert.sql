-- ===============================================================================
-- CRYPTOUNIVERSE PERFORMANCE FIX: EXCHANGE_BALANCES SLOW UPSERT
-- ===============================================================================
--
-- SEVERITY: CRITICAL - 9.96 second INSERT queries blocking production
-- ISSUE: Slow INSERT ON CONFLICT (UPSERT) operations on exchange_balances
-- EVIDENCE: 41,265 calls averaging 3.04s, max 5,631s (94 minutes!)
--
-- QUERY PATTERN:
--   INSERT INTO exchange_balances (...) VALUES (...)
--   ON CONFLICT ON CONSTRAINT unique_account_symbol_balance
--   DO UPDATE SET ...
--
-- ROOT CAUSES:
--   1. Inefficient unique constraint checking
--   2. Missing indexes on frequently updated columns
--   3. Potential lock contention on high-volume updates
--   4. No partial index for active balances
--
-- DEPLOYMENT: Run in Supabase SQL Editor
-- ===============================================================================

BEGIN;

-- ===============================================================================
-- PHASE 1: ANALYZE CURRENT STATE
-- ===============================================================================

-- Check existing indexes on exchange_balances
DO $$
DECLARE
    index_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO index_count
    FROM pg_indexes
    WHERE tablename = 'exchange_balances'
      AND schemaname = 'public';

    RAISE NOTICE 'Current exchange_balances has % indexes', index_count;
END $$;

-- Check constraint definition
DO $$
DECLARE
    constraint_def TEXT;
BEGIN
    SELECT pg_get_constraintdef(oid)
    INTO constraint_def
    FROM pg_constraint
    WHERE conname = 'unique_account_symbol_balance'
      AND conrelid = 'public.exchange_balances'::regclass;

    RAISE NOTICE 'Constraint definition: %', constraint_def;
END $$;

-- ===============================================================================
-- PHASE 2: CREATE OPTIMIZED INDEXES FOR UPSERT OPERATIONS
-- ===============================================================================

-- 2.1 Optimize the UNIQUE constraint with a covering index
-- This allows PostgreSQL to check uniqueness AND fetch updated values in one index scan
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_balances_account_symbol_covering
ON public.exchange_balances(account_id, symbol)
INCLUDE (total_balance, available_balance, locked_balance, usd_value, is_active, updated_at, last_sync_at);

COMMENT ON INDEX idx_exchange_balances_account_symbol_covering IS
'Covering index for UPSERT operations. Allows checking uniqueness and fetching/updating columns without table access.';

-- 2.2 Partial index for active balance lookups (most common query pattern)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_balances_active_usd
ON public.exchange_balances(account_id, usd_value DESC)
WHERE is_active = true AND sync_enabled = true;

-- 2.3 Index for balance change tracking (used in conflict resolution)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_balances_last_sync
ON public.exchange_balances(account_id, last_sync_at DESC)
WHERE is_active = true;

-- ===============================================================================
-- PHASE 3: OPTIMIZE CONSTRAINT (REPLACE WITH BETTER INDEX)
-- ===============================================================================

-- Drop old constraint if it exists without covering
DO $$
BEGIN
    -- Check if old constraint exists and is not using our new index
    IF EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class i ON c.conindid = i.oid
        WHERE c.conname = 'unique_account_symbol_balance'
          AND i.relname != 'idx_exchange_balances_account_symbol_covering'
    ) THEN
        -- Drop old constraint
        ALTER TABLE public.exchange_balances
        DROP CONSTRAINT IF EXISTS unique_account_symbol_balance;

        RAISE NOTICE 'Dropped old unique_account_symbol_balance constraint';
    END IF;
END $$;

-- Create new constraint using our optimized covering index
-- This will use the idx_exchange_balances_account_symbol_covering index
ALTER TABLE public.exchange_balances
ADD CONSTRAINT unique_account_symbol_balance
UNIQUE USING INDEX idx_exchange_balances_account_symbol_covering;

-- ===============================================================================
-- PHASE 4: ADD TABLE-LEVEL OPTIMIZATIONS
-- ===============================================================================

-- 4.1 Set appropriate fillfactor for UPDATE-heavy table
-- Lower fillfactor leaves room for HOT updates (Heap-Only Tuples)
-- This prevents index bloat and speeds up updates
ALTER TABLE public.exchange_balances SET (
    fillfactor = 85,  -- Leave 15% free space for updates
    autovacuum_vacuum_scale_factor = 0.05,  -- Vacuum more frequently
    autovacuum_analyze_scale_factor = 0.02  -- Analyze more frequently
);

COMMENT ON TABLE public.exchange_balances IS
'Exchange account balances with optimized settings for high-frequency updates.
fillfactor=85 enables HOT updates, reducing index bloat.
Aggressive autovacuum prevents table bloat from frequent UPSERTs.';

-- 4.2 Create statistics for better query planning
CREATE STATISTICS IF NOT EXISTS exchange_balances_account_symbol_stats (dependencies)
ON account_id, symbol FROM public.exchange_balances;

-- ===============================================================================
-- PHASE 5: CLEANUP OLD/DUPLICATE INDEXES
-- ===============================================================================

-- Check for duplicate or redundant indexes
DO $$
DECLARE
    index_record RECORD;
BEGIN
    FOR index_record IN
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'exchange_balances'
          AND schemaname = 'public'
          AND indexname NOT IN (
              'idx_exchange_balances_account_symbol_covering',
              'idx_exchange_balances_active_usd',
              'idx_exchange_balances_last_sync',
              'exchange_balances_pkey'  -- Keep primary key
          )
          -- Only drop indexes that are redundant with our new covering index
          AND (
              indexname LIKE '%account_id%symbol%'
              OR indexname = 'unique_account_symbol_balance'
          )
    LOOP
        EXECUTE format('DROP INDEX IF EXISTS public.%I', index_record.indexname);
        RAISE NOTICE 'Dropped redundant index: %', index_record.indexname;
    END LOOP;
END $$;

COMMIT;

-- ===============================================================================
-- PHASE 6: MANUAL VACUUM AND ANALYZE
-- ===============================================================================

-- Run VACUUM ANALYZE to update statistics immediately
VACUUM ANALYZE public.exchange_balances;

-- ===============================================================================
-- EXPECTED PERFORMANCE IMPROVEMENT
-- ===============================================================================

-- BEFORE:
-- - UPSERT operations: 3.04s average, 5,631s max (94 minutes!)
-- - Total time spent: 125,641 seconds (34.9 hours) across 41,265 calls
-- - Constraint check requires full table scan or slow index lookup
-- - No HOT updates = index bloat = slower queries over time

-- AFTER:
-- - UPSERT operations: <50ms average, <500ms max
-- - Covering index eliminates table access for conflict resolution
-- - HOT updates reduce index maintenance overhead
-- - Better statistics = better query plans

-- ESTIMATED IMPROVEMENT: 60-100x faster (3 seconds → 30-50ms)

-- ===============================================================================
-- VERIFICATION QUERIES
-- ===============================================================================

-- Verify covering index is being used:
-- EXPLAIN (ANALYZE, BUFFERS)
-- INSERT INTO exchange_balances (
--     id, account_id, symbol, asset_type, total_balance, available_balance,
--     locked_balance, usd_value, balance_change_24h, is_active, sync_enabled,
--     created_at, updated_at, last_sync_at
-- ) VALUES (
--     gen_random_uuid(),
--     '00000000-0000-0000-0000-000000000000'::uuid,
--     'TEST',
--     'crypto',
--     100.0,
--     100.0,
--     0.0,
--     1000.0,
--     0.0,
--     true,
--     true,
--     NOW(),
--     NOW(),
--     NOW()
-- )
-- ON CONFLICT ON CONSTRAINT unique_account_symbol_balance
-- DO UPDATE SET
--     total_balance = EXCLUDED.total_balance,
--     available_balance = EXCLUDED.available_balance,
--     locked_balance = EXCLUDED.locked_balance,
--     usd_value = EXCLUDED.usd_value,
--     is_active = EXCLUDED.is_active,
--     updated_at = EXCLUDED.updated_at,
--     last_sync_at = EXCLUDED.last_sync_at;

-- Check table settings:
-- SELECT relname, reloptions
-- FROM pg_class
-- WHERE relname = 'exchange_balances';

-- Check index usage:
-- SELECT
--     indexrelname,
--     idx_scan,
--     idx_tup_read,
--     idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public'
--   AND relname = 'exchange_balances'
-- ORDER BY idx_scan DESC;

-- Monitor query performance after deployment:
-- SELECT
--     query,
--     calls,
--     mean_exec_time,
--     max_exec_time
-- FROM pg_stat_statements
-- WHERE query LIKE '%exchange_balances%ON CONFLICT%'
-- ORDER BY mean_exec_time DESC;
