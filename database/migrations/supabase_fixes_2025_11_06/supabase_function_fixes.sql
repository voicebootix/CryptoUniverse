-- ========================================
-- SUPABASE FUNCTION & VIEW SECURITY FIXES
-- ========================================
-- Generated: 2025-11-06
-- Purpose: Fix function search paths and security definer views
--
-- IMPORTANT: Review before running!
-- ========================================

BEGIN;

-- ========================================
-- PART 1: FIX FUNCTION SEARCH PATHS
-- ========================================

-- Fix update_updated_at_column function
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public' AND p.proname = 'update_updated_at_column'
  ) THEN
    ALTER FUNCTION public.update_updated_at_column()
    SET search_path = public, pg_temp;
    RAISE NOTICE '✅ Fixed search_path for update_updated_at_column';
  ELSE
    RAISE NOTICE '⚠️  Function update_updated_at_column not found';
  END IF;
END $$;

-- Fix match_documents function (dynamic signature detection)
DO $$
DECLARE
  func_signature TEXT;
  func_oid OID;
  alter_sql TEXT;
BEGIN
  -- Find the function OID and signature
  SELECT p.oid, pg_get_function_identity_arguments(p.oid)
  INTO func_oid, func_signature
  FROM pg_proc p
  JOIN pg_namespace n ON p.pronamespace = n.oid
  WHERE n.nspname = 'public' AND p.proname = 'match_documents'
  LIMIT 1;

  IF func_oid IS NOT NULL THEN
    -- Build and execute ALTER FUNCTION statement with correct signature
    alter_sql := format('ALTER FUNCTION public.match_documents(%s) SET search_path = public, pg_temp', func_signature);
    EXECUTE alter_sql;
    RAISE NOTICE '✅ Fixed search_path for match_documents(%)', func_signature;
  ELSE
    RAISE NOTICE 'ℹ️  Function match_documents not found (may not exist in this database)';
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    RAISE WARNING '⚠️  Could not fix match_documents: % (SQLSTATE: %)', SQLERRM, SQLSTATE;
    IF func_signature IS NOT NULL THEN
      RAISE WARNING '    Detected signature: match_documents(%)', func_signature;
      RAISE WARNING '    Try manually: ALTER FUNCTION public.match_documents(%) SET search_path = public, pg_temp;', func_signature;
    END IF;
END $$;

-- ========================================
-- PART 2: PRE-MIGRATION - EXTRACT VIEW DEFINITIONS
-- ========================================

-- ⚠️  RUN THIS FIRST - BEFORE DROPPING VIEWS!
-- This query extracts and displays current view definitions.
-- Save this output to a file for later recreation.
--
-- To save to file in psql:
--   \o view_backup.sql
--   <run query below>
--   \o
--
-- Or save output manually and store in version control.

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'EXTRACTING VIEW DEFINITIONS';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Copy the output from the following query and save to a file!';
  RAISE NOTICE 'You will need these definitions to recreate the views.';
  RAISE NOTICE '';
END $$;

-- Extract view definitions
SELECT
  '-- View: ' || viewname AS section,
  'DROP VIEW IF EXISTS public.' || viewname || ' CASCADE;' AS drop_statement,
  'CREATE VIEW public.' || viewname || ' AS' || E'\n' || definition AS create_statement,
  '' AS separator
FROM pg_views
WHERE schemaname = 'public'
AND viewname IN ('portfolio_evolution', 'daily_performance', 'v_user_strategy_summary', 'ai_performance')
ORDER BY viewname;

-- ========================================
-- PART 3: FIX SECURITY DEFINER VIEWS
-- ========================================

-- ⚠️  CRITICAL WARNING:
-- The following views will be DROPPED and must be recreated manually!
-- This is a BLOCKING operation that will break application functionality
-- until views are recreated.
--
-- BEFORE proceeding, you MUST:
-- 1. Backup view definitions from your application repository or database
-- 2. Understand the original view logic and dependencies
-- 3. Plan view recreation with proper security (auth.uid() checks or security_invoker)
-- 4. Schedule deployment window where application can tolerate missing views
--
-- To get original view definitions, run this query BEFORE running this migration:
-- SELECT viewname, definition
-- FROM pg_views
-- WHERE schemaname = 'public'
-- AND viewname IN ('portfolio_evolution', 'daily_performance', 'v_user_strategy_summary', 'ai_performance');

DO $$
BEGIN
  RAISE WARNING '';
  RAISE WARNING '========================================';
  RAISE WARNING '⚠️  DROPPING SECURITY DEFINER VIEWS';
  RAISE WARNING '========================================';
  RAISE WARNING '';
  RAISE WARNING 'The following views will be DROPPED:';
  RAISE WARNING '  1. portfolio_evolution';
  RAISE WARNING '  2. daily_performance';
  RAISE WARNING '  3. v_user_strategy_summary';
  RAISE WARNING '  4. ai_performance';
  RAISE WARNING '';
  RAISE WARNING 'These views MUST be recreated after this migration!';
  RAISE WARNING 'Application functionality will be BROKEN until views are recreated.';
  RAISE WARNING '';
  RAISE WARNING 'See VIEW_RECREATION_GUIDE.md for detailed instructions.';
  RAISE WARNING 'Original definitions should be in your app repository or backup.';
  RAISE WARNING '';
END $$;

-- portfolio_evolution view
DROP VIEW IF EXISTS public.portfolio_evolution CASCADE;

-- You'll need to recreate this view with your actual query
-- Example structure:
-- CREATE VIEW public.portfolio_evolution AS
-- SELECT
--   p.user_id,
--   p.portfolio_id,
--   ps.timestamp,
--   ps.total_value
-- FROM portfolios p
-- JOIN portfolio_snapshots ps ON p.id = ps.portfolio_id
-- WHERE p.user_id = auth.uid(); -- Add proper auth check

-- daily_performance view
DROP VIEW IF EXISTS public.daily_performance CASCADE;

-- You'll need to recreate this view with your actual query
-- Example structure:
-- CREATE VIEW public.daily_performance AS
-- SELECT
--   user_id,
--   DATE(created_at) as date,
--   SUM(profit_loss) as daily_profit
-- FROM trades
-- WHERE user_id = auth.uid() -- Add proper auth check
-- GROUP BY user_id, DATE(created_at);

-- v_user_strategy_summary view
DROP VIEW IF EXISTS public.v_user_strategy_summary CASCADE;

-- You'll need to recreate this view with your actual query
-- Example structure:
-- CREATE VIEW public.v_user_strategy_summary AS
-- SELECT
--   ts.user_id,
--   ts.id as strategy_id,
--   ts.name,
--   COUNT(t.id) as total_trades,
--   SUM(t.profit_loss) as total_profit
-- FROM trading_strategies ts
-- LEFT JOIN trades t ON ts.id = t.strategy_id
-- WHERE ts.user_id = auth.uid() -- Add proper auth check
-- GROUP BY ts.user_id, ts.id, ts.name;

-- ai_performance view
DROP VIEW IF EXISTS public.ai_performance CASCADE;

-- You'll need to recreate this view with your actual query
-- Example structure:
-- CREATE VIEW public.ai_performance AS
-- SELECT
--   model_id,
--   COUNT(*) as predictions,
--   AVG(confidence) as avg_confidence,
--   SUM(CASE WHEN was_correct THEN 1 ELSE 0 END)::float / COUNT(*) as accuracy
-- FROM ai_signals
-- GROUP BY model_id;

COMMIT;

-- ========================================
-- PART 3: RECREATE VIEWS WITH PROPER SECURITY
-- ========================================

-- ⚠️ IMPORTANT: Replace the templates below with actual view definitions!
-- Use the backup from Part 2 and add proper security.

-- SECURITY MODEL: We recommend using security_invoker (PostgreSQL 15+)
-- This runs views with the permissions of the calling user, respecting RLS policies.

BEGIN;

-- Template 1: portfolio_evolution
-- Replace this with your actual view definition from backup
/*
CREATE VIEW public.portfolio_evolution
WITH (security_invoker = true) AS
SELECT
  p.user_id,
  p.id as portfolio_id,
  ps.timestamp,
  ps.total_value,
  ps.total_equity,
  ps.total_cash,
  ps.profit_loss,
  ps.profit_loss_percentage
FROM portfolios p
JOIN portfolio_snapshots ps ON p.id = ps.portfolio_id
WHERE p.user_id = auth.uid()  -- Security: only user's own data
ORDER BY ps.timestamp DESC;
*/

-- Template 2: daily_performance
-- Replace this with your actual view definition from backup
/*
CREATE VIEW public.daily_performance
WITH (security_invoker = true) AS
SELECT
  user_id,
  DATE(created_at) as date,
  COUNT(*) as trade_count,
  SUM(profit_loss) as daily_profit,
  AVG(profit_loss) as avg_profit_per_trade,
  SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END)::float / COUNT(*) as win_rate
FROM trades
WHERE user_id = auth.uid()  -- Security: only user's own trades
  AND status = 'closed'
GROUP BY user_id, DATE(created_at)
ORDER BY date DESC;
*/

-- Template 3: v_user_strategy_summary
-- Replace this with your actual view definition from backup
/*
CREATE VIEW public.v_user_strategy_summary
WITH (security_invoker = true) AS
SELECT
  ts.user_id,
  ts.id as strategy_id,
  ts.name,
  ts.description,
  ts.status,
  ts.visibility,
  COUNT(t.id) as total_trades,
  SUM(t.profit_loss) as total_profit,
  AVG(t.profit_loss) as avg_profit_per_trade,
  SUM(CASE WHEN t.profit_loss > 0 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(t.id), 0) as win_rate,
  MAX(t.created_at) as last_trade_at
FROM trading_strategies ts
LEFT JOIN trades t ON ts.id = t.strategy_id AND t.status = 'closed'
WHERE ts.user_id = auth.uid()  -- Security: only user's own strategies
GROUP BY ts.user_id, ts.id, ts.name, ts.description, ts.status, ts.visibility;
*/

-- Template 4: ai_performance
-- Replace this with your actual view definition from backup
-- Note: This view may not need user restriction if it shows aggregate AI model stats
/*
CREATE VIEW public.ai_performance
WITH (security_invoker = true) AS
SELECT
  am.id as model_id,
  am.name as model_name,
  am.provider,
  COUNT(ais.id) as total_signals,
  AVG(ais.confidence) as avg_confidence,
  SUM(CASE WHEN ais.was_correct THEN 1 ELSE 0 END)::float / NULLIF(COUNT(ais.id), 0) as accuracy,
  MAX(ais.created_at) as last_signal_at
FROM ai_models am
LEFT JOIN ai_signals ais ON am.id = ais.model_id
WHERE am.is_active = true
GROUP BY am.id, am.name, am.provider
ORDER BY accuracy DESC NULLS LAST;
*/

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE '⚠️  ACTION REQUIRED: RECREATE VIEWS';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Views have been DROPPED but templates are commented out above.';
  RAISE NOTICE '';
  RAISE NOTICE 'TO COMPLETE THIS MIGRATION:';
  RAISE NOTICE '1. Use the backup from Part 2 (view definitions)';
  RAISE NOTICE '2. Uncomment and customize the templates in PART 3';
  RAISE NOTICE '3. Add auth.uid() checks or use WITH (security_invoker = true)';
  RAISE NOTICE '4. Test each view with SELECT * FROM view_name;';
  RAISE NOTICE '5. Verify users can only see their own data';
  RAISE NOTICE '';
  RAISE NOTICE 'SECURITY OPTIONS:';
  RAISE NOTICE '  Option A: WITH (security_invoker = true) - Recommended';
  RAISE NOTICE '  Option B: WHERE user_id = auth.uid() - Explicit check';
  RAISE NOTICE '  Option C: Both for defense in depth';
  RAISE NOTICE '';
  RAISE NOTICE 'See SUPABASE_FIX_GUIDE.md section "Recreating Dropped Views"';
  RAISE NOTICE '';
END $$;

COMMIT;

-- ========================================
-- PART 4: MOVE VECTOR EXTENSION (OPTIONAL)
-- ========================================
-- This moves the vector extension to a separate schema for better security

BEGIN;

-- Create extensions schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS extensions;

-- Grant usage to appropriate roles
GRANT USAGE ON SCHEMA extensions TO postgres, anon, authenticated, service_role;

-- Move vector extension with improved error handling
DO $$
DECLARE
  dep_count INTEGER;
BEGIN
  -- Check if vector extension exists
  IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
    RAISE NOTICE 'ℹ️  Vector extension not installed in this database';
    RETURN;
  END IF;

  -- Check for dependencies before attempting move
  SELECT COUNT(*) INTO dep_count
  FROM pg_depend d
  JOIN pg_extension e ON d.refobjid = e.oid
  WHERE e.extname = 'vector'
  AND d.deptype = 'n'; -- normal dependencies

  IF dep_count > 0 THEN
    RAISE WARNING 'Vector extension has % dependent objects. Move may fail.', dep_count;
    RAISE WARNING 'To see dependencies, run:';
    RAISE WARNING 'SELECT classid::regclass, objid, objsubid FROM pg_depend WHERE refobjid = (SELECT oid FROM pg_extension WHERE extname = ''vector'');';
  END IF;

  -- Attempt to move the extension
  ALTER EXTENSION vector SET SCHEMA extensions;
  RAISE NOTICE '✅ Successfully moved vector extension to extensions schema';

EXCEPTION
  WHEN dependent_objects_still_exist THEN
    RAISE WARNING '⚠️  Cannot move vector extension: dependent objects still exist';
    RAISE WARNING '    SQLSTATE: %, Message: %', SQLSTATE, SQLERRM;
    RAISE WARNING '    ';
    RAISE WARNING '    To resolve, query dependent objects:';
    RAISE WARNING '    SELECT n.nspname, c.relname, a.attname';
    RAISE WARNING '    FROM pg_attribute a';
    RAISE WARNING '    JOIN pg_class c ON a.attrelid = c.oid';
    RAISE WARNING '    JOIN pg_namespace n ON c.relnamespace = n.oid';
    RAISE WARNING '    JOIN pg_type t ON a.atttypid = t.oid';
    RAISE WARNING '    WHERE t.typname = ''vector'';';
    RAISE WARNING '    ';
    RAISE WARNING '    You may need to drop/recreate objects using vector type.';
  WHEN OTHERS THEN
    RAISE WARNING '⚠️  Unexpected error moving vector extension';
    RAISE WARNING '    SQLSTATE: %, Message: %', SQLSTATE, SQLERRM;
    RAISE WARNING '    Skipping vector extension move.';
END $$;

COMMIT;

-- ========================================
-- VERIFICATION QUERIES
-- ========================================

-- Check function search paths
SELECT
  n.nspname as schema,
  p.proname as function_name,
  pg_get_function_identity_arguments(p.oid) as arguments,
  p.prosecdef as security_definer,
  p.proconfig as config
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public'
  AND p.proname IN ('update_updated_at_column', 'match_documents');

-- Check for remaining security definer views
SELECT
  schemaname,
  viewname,
  definition
FROM pg_views
WHERE schemaname = 'public'
  AND viewname IN ('portfolio_evolution', 'daily_performance', 'v_user_strategy_summary', 'ai_performance');

-- Check extension location
SELECT
  e.extname,
  n.nspname as schema
FROM pg_extension e
JOIN pg_namespace n ON e.extnamespace = n.oid
WHERE e.extname = 'vector';

-- ========================================
-- SUCCESS MESSAGE
-- ========================================
DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE '✅ Function security paths have been fixed!';
  RAISE NOTICE '⚠️  IMPORTANT: Views have been dropped!';
  RAISE NOTICE '⚠️  You MUST recreate them with proper security!';
  RAISE NOTICE '';
  RAISE NOTICE 'Next steps:';
  RAISE NOTICE '1. Get original view definitions';
  RAISE NOTICE '2. Add proper security checks (auth.uid() or security_invoker)';
  RAISE NOTICE '3. Recreate the views';
  RAISE NOTICE '4. Test thoroughly!';
  RAISE NOTICE '========================================';
END $$;
