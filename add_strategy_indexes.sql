-- Add indexes to speed up strategy_submissions queries
-- Run this in your Supabase SQL Editor

-- Index for user_id (most common query)
CREATE INDEX IF NOT EXISTS idx_strategy_submissions_user_id
ON strategy_submissions(user_id);

-- Index for status (for filtering by status)
CREATE INDEX IF NOT EXISTS idx_strategy_submissions_status
ON strategy_submissions(status);

-- Composite index for user + status queries
CREATE INDEX IF NOT EXISTS idx_strategy_submissions_user_status
ON strategy_submissions(user_id, status);

-- Index for created_at (for sorting)
CREATE INDEX IF NOT EXISTS idx_strategy_submissions_created_at
ON strategy_submissions(created_at DESC);

-- Analyze table to update statistics
ANALYZE strategy_submissions;
