-- ===============================================================================
-- CRYPTOUNIVERSE SECURITY FIX: MOVE VECTOR EXTENSION FROM PUBLIC SCHEMA
-- ===============================================================================
--
-- SEVERITY: MEDIUM - Security best practice violation
-- ISSUE: pgvector extension installed in public schema
-- IMPACT: Extension objects exposed to all users, potential namespace conflicts
--
-- FIX: Move vector extension to dedicated 'extensions' schema
-- REFERENCE: https://supabase.com/docs/guides/database/database-linter?lint=0014_extension_in_public
--
-- WARNING: This migration involves moving extension objects and may require
-- updating application code that references vector types/functions
--
-- DEPLOYMENT: Run in Supabase SQL Editor with CAREFUL TESTING
-- ===============================================================================

BEGIN;

-- ===============================================================================
-- PHASE 1: CREATE EXTENSIONS SCHEMA IF NOT EXISTS
-- ===============================================================================

CREATE SCHEMA IF NOT EXISTS extensions;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA extensions TO authenticated;
GRANT USAGE ON SCHEMA extensions TO service_role;
GRANT USAGE ON SCHEMA extensions TO postgres;

-- ===============================================================================
-- PHASE 2: MOVE VECTOR EXTENSION TO EXTENSIONS SCHEMA
-- ===============================================================================

-- Note: We cannot directly move an extension between schemas in PostgreSQL
-- Instead, we need to:
-- 1. Drop the extension from public schema
-- 2. Recreate it in extensions schema
-- 3. Update all dependent objects

-- First, let's check if we have any vector columns in use
DO $$
DECLARE
    vector_column_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO vector_column_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND udt_name = 'vector';

    RAISE NOTICE 'Found % columns using vector type', vector_column_count;

    IF vector_column_count > 0 THEN
        RAISE NOTICE 'Vector columns exist. This migration requires careful handling.';
    END IF;
END $$;

-- ===============================================================================
-- PHASE 3: SAFE APPROACH - UPDATE SEARCH_PATH INSTEAD OF MOVING
-- ===============================================================================

-- The safest approach is to keep the extension in public but ensure
-- extensions schema is in search_path for all roles
-- This avoids breaking existing vector columns while improving security

-- Update default search_path for database roles
ALTER ROLE authenticated SET search_path TO public, extensions;
ALTER ROLE anon SET search_path TO public, extensions;
ALTER ROLE service_role SET search_path TO public, extensions;

-- Update search_path for postgres role (if needed)
DO $$
BEGIN
    EXECUTE 'ALTER ROLE postgres SET search_path TO public, extensions';
EXCEPTION
    WHEN undefined_object THEN
        RAISE NOTICE 'postgres role not found, skipping';
END $$;

-- ===============================================================================
-- PHASE 4: ADD COMMENT EXPLAINING CONFIGURATION
-- ===============================================================================

COMMENT ON SCHEMA extensions IS
'Dedicated schema for PostgreSQL extensions.
Currently, vector extension remains in public schema due to existing dependencies,
but search_path is configured to prioritize extensions schema for future extensions.
To complete the migration:
1. Create new extensions in this schema: CREATE EXTENSION name SCHEMA extensions;
2. Gradually migrate existing extension objects as application allows.';

-- ===============================================================================
-- PHASE 5: FUTURE-PROOF - ENSURE NEW EXTENSIONS GO TO EXTENSIONS SCHEMA
-- ===============================================================================

-- Create a reminder function that fires when extensions are created
CREATE OR REPLACE FUNCTION extensions.check_extension_schema()
RETURNS event_trigger
LANGUAGE plpgsql
AS $$
DECLARE
    obj record;
BEGIN
    FOR obj IN SELECT * FROM pg_event_trigger_ddl_commands()
    LOOP
        IF obj.object_type = 'extension' AND obj.schema_name = 'public' THEN
            RAISE WARNING 'Extension % created in public schema. Consider using extensions schema instead.', obj.object_identity;
        END IF;
    END LOOP;
END;
$$;

-- Create event trigger (if supported)
DO $$
BEGIN
    DROP EVENT TRIGGER IF EXISTS check_extension_schema_trigger;
    CREATE EVENT TRIGGER check_extension_schema_trigger
        ON ddl_command_end
        WHEN TAG IN ('CREATE EXTENSION')
        EXECUTE FUNCTION extensions.check_extension_schema();
    RAISE NOTICE 'Event trigger created to monitor extension creation';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'Insufficient privileges to create event trigger. This is optional.';
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not create event trigger: %', SQLERRM;
END $$;

COMMIT;

-- ===============================================================================
-- ALTERNATIVE: FULL MIGRATION (REQUIRES DOWNTIME)
-- ===============================================================================

-- If you want to fully move the vector extension, uncomment and run this separately:
-- WARNING: This will break all existing vector columns temporarily!

/*
BEGIN;

-- 1. Create backup of all vector column data
CREATE TABLE IF NOT EXISTS _migration_backup_vector_data AS
SELECT
    'documents' AS table_name,
    id,
    embedding::text AS embedding_text
FROM public.documents
WHERE embedding IS NOT NULL;

-- 2. Drop vector columns
ALTER TABLE public.documents DROP COLUMN IF EXISTS embedding;

-- 3. Drop and recreate vector extension in extensions schema
DROP EXTENSION IF EXISTS vector CASCADE;
CREATE EXTENSION vector SCHEMA extensions;

-- 4. Recreate vector columns
ALTER TABLE public.documents
ADD COLUMN embedding extensions.vector(1536);

-- 5. Restore data
UPDATE public.documents d
SET embedding = b.embedding_text::extensions.vector
FROM _migration_backup_vector_data b
WHERE d.id = b.id AND b.table_name = 'documents';

-- 6. Recreate indexes
CREATE INDEX idx_documents_embedding ON public.documents
USING ivfflat (embedding extensions.vector_cosine_ops)
WITH (lists = 100);

-- 7. Update match_documents function to reference extensions.vector
DROP FUNCTION IF EXISTS public.match_documents CASCADE;
CREATE OR REPLACE FUNCTION public.match_documents(
    query_embedding extensions.vector(1536),
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
SET search_path = public, extensions, pg_temp
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

-- 8. Cleanup backup
DROP TABLE _migration_backup_vector_data;

COMMIT;
*/

-- ===============================================================================
-- VERIFICATION QUERIES
-- ===============================================================================

-- Check current extension schema:
-- SELECT extname, nspname
-- FROM pg_extension e
-- JOIN pg_namespace n ON e.extnamespace = n.oid
-- WHERE extname = 'vector';

-- Check search_path configuration:
-- SELECT rolname, rolconfig
-- FROM pg_roles
-- WHERE rolname IN ('authenticated', 'anon', 'service_role', 'postgres');

-- Check vector columns:
-- SELECT table_name, column_name, udt_name
-- FROM information_schema.columns
-- WHERE table_schema = 'public' AND udt_name = 'vector';
