-- ===============================================================================
-- CRYPTOUNIVERSE SECURITY FIX: FUNCTION SEARCH PATH MUTABILITY
-- ===============================================================================
--
-- SEVERITY: MEDIUM - Potential search_path hijacking vulnerability
-- ISSUE: Functions without fixed search_path can be exploited
-- IMPACT: Malicious users could inject objects into search_path
--
-- AFFECTED FUNCTIONS:
--   - update_updated_at_column
--   - match_documents
--
-- FIX: Set explicit search_path to prevent hijacking
-- REFERENCE: https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable
--
-- DEPLOYMENT: Run in Supabase SQL Editor
-- ===============================================================================

BEGIN;

-- ===============================================================================
-- PHASE 1: FIX update_updated_at_column FUNCTION
-- ===============================================================================

-- Drop and recreate with explicit search_path
DROP FUNCTION IF EXISTS public.update_updated_at_column() CASCADE;

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp  -- Explicit search_path prevents hijacking
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION public.update_updated_at_column() TO authenticated;
GRANT EXECUTE ON FUNCTION public.update_updated_at_column() TO service_role;

-- Recreate triggers that use this function
-- (These were dropped by CASCADE above)

-- List of tables that use this trigger (add more as discovered):
DO $$
DECLARE
    table_record RECORD;
    trigger_exists BOOLEAN;
BEGIN
    -- Find all tables with updated_at column
    FOR table_record IN
        SELECT table_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND column_name = 'updated_at'
          AND table_name NOT LIKE 'pg_%'
          AND table_name NOT LIKE 'sql_%'
    LOOP
        -- Check if trigger already exists
        SELECT EXISTS (
            SELECT 1
            FROM pg_trigger t
            JOIN pg_class c ON t.tgrelid = c.oid
            WHERE c.relname = table_record.table_name
              AND t.tgname = 'update_' || table_record.table_name || '_updated_at'
        ) INTO trigger_exists;

        -- Create trigger if it doesn't exist
        IF NOT trigger_exists THEN
            EXECUTE format(
                'CREATE TRIGGER update_%I_updated_at
                BEFORE UPDATE ON public.%I
                FOR EACH ROW
                EXECUTE FUNCTION public.update_updated_at_column()',
                table_record.table_name,
                table_record.table_name
            );
            RAISE NOTICE 'Created trigger for table: %', table_record.table_name;
        END IF;
    END LOOP;
END $$;

-- ===============================================================================
-- PHASE 2: FIX match_documents FUNCTION (VECTOR SEARCH)
-- ===============================================================================

-- Drop and recreate with explicit search_path
DROP FUNCTION IF EXISTS public.match_documents(vector(1536), float, int) CASCADE;
DROP FUNCTION IF EXISTS public.match_documents(vector, float, int) CASCADE;

-- Recreate with explicit search_path and proper signature
CREATE OR REPLACE FUNCTION public.match_documents(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.78,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp  -- Explicit search_path prevents hijacking
AS $$
BEGIN
    RETURN QUERY
    SELECT
        documents.id,
        documents.content,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM public.documents
    WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
    ORDER BY documents.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.match_documents(vector(1536), float, int) TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_documents(vector(1536), float, int) TO service_role;

-- Add comment explaining the function
COMMENT ON FUNCTION public.match_documents IS
'Vector similarity search for documents using pgvector.
Security: DEFINER with explicit search_path to prevent hijacking.
Returns documents with similarity score above threshold.';

COMMIT;

-- ===============================================================================
-- VERIFICATION QUERIES
-- ===============================================================================

-- Verify functions have search_path set:
-- SELECT
--     p.proname AS function_name,
--     pg_get_function_identity_arguments(p.oid) AS arguments,
--     p.prosecdef AS is_security_definer,
--     pg_get_functiondef(p.oid) AS definition
-- FROM pg_proc p
-- JOIN pg_namespace n ON p.pronamespace = n.oid
-- WHERE n.nspname = 'public'
--   AND p.proname IN ('update_updated_at_column', 'match_documents');

-- Test function execution:
-- SELECT NOW(), updated_at FROM users LIMIT 1;
-- UPDATE users SET email = email WHERE id = auth.uid();  -- Should update updated_at
-- SELECT NOW(), updated_at FROM users WHERE id = auth.uid();  -- Should show new timestamp
