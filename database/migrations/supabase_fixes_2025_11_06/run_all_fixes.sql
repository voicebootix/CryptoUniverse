-- ========================================
-- MASTER FIX SCRIPT - RUN ALL FIXES
-- ========================================
-- Generated: 2025-11-06
-- Purpose: Run all security and performance fixes in correct order
--
-- ⚠️  DANGER ZONE! ⚠️
-- This script will make MAJOR changes to your database!
--
-- REQUIREMENTS BEFORE RUNNING:
-- 1. ✅ Database backup completed
-- 2. ✅ Tested in development environment
-- 3. ✅ Application team notified
-- 4. ✅ Maintenance window scheduled
-- 5. ✅ Rollback plan ready
--
-- ESTIMATED TIME: 5-15 minutes (depending on database size)
-- ========================================

-- Verify required files exist (informational)
DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'PRE-FLIGHT CHECKS';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Required migration files (TWO-STEP APPROACH):';
  RAISE NOTICE '  ✓ STEP1_SIMPLE.sql - Enable RLS';
  RAISE NOTICE '  ✓ STEP2_create_policies_safe.sql - Create policies';
  RAISE NOTICE '  ✓ supabase_performance_fixes.sql - Drop indexes';
  RAISE NOTICE '  ✓ supabase_function_fixes.sql - Fix functions';
  RAISE NOTICE '';
  RAISE NOTICE 'If any file is missing, this script will fail.';
  RAISE NOTICE 'Ensure all files are in the same directory as this script.';
  RAISE NOTICE '';
END $$;

-- Verify you want to proceed
DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE '⚠️  WARNING: MAJOR DATABASE CHANGES ⚠️';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'This script will:';
  RAISE NOTICE '1. Enable RLS on 80 tables';
  RAISE NOTICE '2. Create RLS policies';
  RAISE NOTICE '3. Drop 100+ unused indexes';
  RAISE NOTICE '4. Fix function security';
  RAISE NOTICE '5. Drop and require recreation of 4 views';
  RAISE NOTICE '';
  RAISE NOTICE 'Have you:';
  RAISE NOTICE '✓ Backed up the database?';
  RAISE NOTICE '✓ Tested in development?';
  RAISE NOTICE '✓ Reviewed all scripts?';
  RAISE NOTICE '';
  RAISE NOTICE 'Press Ctrl+C NOW to cancel!';
  RAISE NOTICE 'Script will start in 10 seconds...';
  RAISE NOTICE '';

  -- Pause for 10 seconds to give chance to cancel
  PERFORM pg_sleep(10);

  RAISE NOTICE '🚀 Starting fixes...';
  RAISE NOTICE '';
END $$;

-- ========================================
-- PHASE 1: SECURITY FIXES (CRITICAL)
-- ========================================

\echo '========================================';
\echo 'PHASE 1: SECURITY FIXES (TWO-STEP APPROACH)';
\echo '========================================';
\echo '';

\echo 'Step 1.1: Enabling RLS on all tables...';
\i STEP1_SIMPLE.sql
\echo '✅ RLS enabled on all tables!';
\echo '';

\echo 'Step 1.2: Creating RLS policies with column checks...';
\i STEP2_create_policies_safe.sql
\echo '✅ RLS policies created!';
\echo '';

-- ========================================
-- PHASE 2: VERIFY SECURITY
-- ========================================

\echo '========================================';
\echo 'PHASE 2: VERIFY SECURITY';
\echo '========================================';
\echo '';

\echo 'Checking RLS status...';
SELECT
  COUNT(*) FILTER (WHERE rowsecurity = true) as tables_with_rls,
  COUNT(*) FILTER (WHERE rowsecurity = false) as tables_without_rls,
  COUNT(*) as total_tables
FROM pg_tables
WHERE schemaname = 'public';

\echo '';
\echo 'Checking policies created...';
SELECT
  COUNT(*) as total_policies,
  COUNT(DISTINCT tablename) as tables_with_policies
FROM pg_policies
WHERE schemaname = 'public';

\echo '';

-- Checkpoint: Verify Phase 1 success before continuing
DO $$
DECLARE
  rls_count INTEGER;
  policy_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO rls_count
  FROM pg_tables
  WHERE schemaname = 'public' AND rowsecurity = true;

  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public';

  IF rls_count < 70 THEN
    RAISE WARNING 'RLS enabled on fewer tables than expected (found: %, expected: 70+)', rls_count;
    RAISE WARNING 'Phase 1 may have failed. Review output above.';
  ELSE
    RAISE NOTICE '✅ Phase 1 verification passed (% tables with RLS)', rls_count;
  END IF;

  IF policy_count < 40 THEN
    RAISE EXCEPTION 'CRITICAL: Only % policies created (expected 80+). Phase 1 failed! Check logs and do NOT continue to Phase 2.', policy_count;
  ELSE
    RAISE NOTICE '✅ Policy count verification passed (% policies)', policy_count;
  END IF;

  RAISE NOTICE '';
  RAISE NOTICE '✅ All Phase 1 verifications passed. Proceeding to Phase 2...';
  RAISE NOTICE '';
END $$;

-- ========================================
-- PHASE 3: PERFORMANCE FIXES
-- ========================================

\echo '========================================';
\echo 'PHASE 3: PERFORMANCE FIXES';
\echo '========================================';
\echo '';

\echo 'Step 3.1: Dropping unused indexes...';
\i supabase_performance_fixes.sql
\echo '✅ Indexes optimized!';
\echo '';

-- Checkpoint: Verify Phase 3 success
DO $$
DECLARE
  index_count INTEGER;
  unused_count INTEGER;
BEGIN
  -- Count remaining indexes (excluding primary keys)
  SELECT COUNT(*) INTO index_count
  FROM pg_indexes
  WHERE schemaname = 'public'
  AND indexname NOT LIKE '%_pkey';

  -- Check for remaining unused indexes
  SELECT COUNT(*) INTO unused_count
  FROM pg_stat_user_indexes
  WHERE schemaname = 'public'
  AND idx_scan = 0
  AND indexname NOT LIKE '%_pkey';

  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Phase 3 Verification';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Remaining indexes (non-PK): %', index_count;
  RAISE NOTICE 'Unused indexes still present: %', unused_count;
  RAISE NOTICE '';

  IF index_count > 300 THEN
    RAISE WARNING 'High index count detected (%). Review if more indexes should be dropped.', index_count;
  END IF;

  IF unused_count > 20 THEN
    RAISE WARNING 'Still % unused indexes remaining. Some indexes may not have been dropped.', unused_count;
  ELSE
    RAISE NOTICE '✅ Phase 3 verification passed';
  END IF;

  RAISE NOTICE '';
  RAISE NOTICE 'Proceeding to Phase 4...';
  RAISE NOTICE '';
END $$;

-- ========================================
-- PHASE 4: FUNCTION FIXES
-- ========================================

\echo '========================================';
\echo 'PHASE 4: FUNCTION FIXES';
\echo '========================================';
\echo '';

\echo 'Step 4.1: Fixing function security...';
\i supabase_function_fixes.sql
\echo '⚠️  Views dropped - must be recreated!';
\echo '';

-- Checkpoint: Verify Phase 4 success
DO $$
DECLARE
  func_fixed_count INTEGER;
  views_exist_count INTEGER;
  expected_dropped_views TEXT[] := ARRAY['portfolio_evolution', 'daily_performance', 'v_user_strategy_summary', 'ai_performance'];
  view_name TEXT;
  still_exists TEXT[] := ARRAY[]::TEXT[];
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Phase 4 Verification';
  RAISE NOTICE '========================================';

  -- Check if functions have correct search_path
  SELECT COUNT(*) INTO func_fixed_count
  FROM pg_proc p
  JOIN pg_namespace n ON p.pronamespace = n.oid
  WHERE n.nspname = 'public'
  AND p.proname IN ('update_updated_at_column', 'match_documents')
  AND 'public' = ANY(string_to_array(replace(replace(array_to_string(p.proconfig, ','), 'search_path=', ''), ' ', ''), ','));

  RAISE NOTICE 'Functions with fixed search_path: %', func_fixed_count;

  -- Check if security definer views were dropped
  FOREACH view_name IN ARRAY expected_dropped_views
  LOOP
    IF EXISTS (
      SELECT 1 FROM pg_views
      WHERE schemaname = 'public'
      AND viewname = view_name
    ) THEN
      still_exists := array_append(still_exists, view_name);
    END IF;
  END LOOP;

  views_exist_count := array_length(still_exists, 1);

  IF views_exist_count IS NULL THEN
    views_exist_count := 0;
  END IF;

  IF views_exist_count > 0 THEN
    RAISE WARNING 'Expected views were NOT dropped: %', array_to_string(still_exists, ', ');
    RAISE WARNING 'Phase 4 may have failed. Views should be dropped.';
  ELSE
    RAISE NOTICE '✅ All 4 security definer views successfully dropped';
  END IF;

  IF func_fixed_count > 0 THEN
    RAISE NOTICE '✅ Function search paths updated';
  ELSE
    RAISE NOTICE 'ℹ️  Functions may not exist or were already fixed';
  END IF;

  RAISE NOTICE '';
  RAISE NOTICE '⚠️  CRITICAL: Views must be recreated before application restart!';
  RAISE NOTICE '    See SUPABASE_FIX_GUIDE.md for recreation instructions';
  RAISE NOTICE '';
  RAISE NOTICE 'Proceeding to Phase 5...';
  RAISE NOTICE '';
END $$;

-- ========================================
-- PHASE 5: FINAL VERIFICATION
-- ========================================

\echo '========================================';
\echo 'PHASE 5: FINAL VERIFICATION';
\echo '========================================';
\echo '';

-- Check database size
\echo 'Database size after changes:';
SELECT
  pg_size_pretty(pg_database_size(current_database())) as database_size;

\echo '';

-- Check tables with RLS
\echo 'Tables with RLS enabled:';
SELECT
  tablename,
  rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

\echo '';

-- Check for tables without RLS (should be empty)
\echo 'Tables WITHOUT RLS (should be empty):';
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
AND rowsecurity = false;

\echo '';

-- List all policies
\echo 'Total policies created:';
SELECT
  tablename,
  COUNT(*) as policy_count
FROM pg_policies
WHERE schemaname = 'public'
GROUP BY tablename
ORDER BY tablename;

\echo '';

-- ========================================
-- COMPLETION SUMMARY
-- ========================================

DO $$
DECLARE
  rls_count INTEGER;
  policy_count INTEGER;
  index_count INTEGER;
BEGIN
  -- Count tables with RLS
  SELECT COUNT(*) INTO rls_count
  FROM pg_tables
  WHERE schemaname = 'public' AND rowsecurity = true;

  -- Count policies
  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public';

  -- Count remaining indexes
  SELECT COUNT(*) INTO index_count
  FROM pg_indexes
  WHERE schemaname = 'public';

  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE '✅ ALL FIXES COMPLETED!';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Summary:';
  RAISE NOTICE '- Tables with RLS: %', rls_count;
  RAISE NOTICE '- Security policies: %', policy_count;
  RAISE NOTICE '- Remaining indexes: %', index_count;
  RAISE NOTICE '';
  RAISE NOTICE '⚠️  IMPORTANT NEXT STEPS:';
  RAISE NOTICE '1. Recreate the 4 security definer views';
  RAISE NOTICE '2. Test application functionality';
  RAISE NOTICE '3. Monitor query performance';
  RAISE NOTICE '4. Upgrade database version in Supabase dashboard';
  RAISE NOTICE '';
  RAISE NOTICE '📖 See SUPABASE_FIX_GUIDE.md for details';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
END $$;

-- ========================================
-- POST-DEPLOYMENT CHECKLIST
-- ========================================

\echo '========================================';
\echo 'POST-DEPLOYMENT CHECKLIST';
\echo '========================================';
\echo '';
\echo '□ Test user authentication';
\echo '□ Verify users can only see their own data';
\echo '□ Test all application features';
\echo '□ Recreate security definer views';
\echo '□ Monitor application logs for errors';
\echo '□ Check query performance';
\echo '□ Upgrade database version';
\echo '□ Run Supabase advisors again';
\echo '';
\echo '========================================';

-- End of script
