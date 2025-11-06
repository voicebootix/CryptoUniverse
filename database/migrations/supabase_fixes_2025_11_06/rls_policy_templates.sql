-- ========================================
-- RLS POLICY TEMPLATES
-- ========================================
-- Use these templates to create custom policies for your business logic
-- Copy and modify as needed!
-- ========================================

-- ========================================
-- TEMPLATE 1: BASIC USER DATA POLICY
-- ========================================
-- Use this for tables where users should only see their own data

/*
CREATE POLICY "users_own_data_select"
ON your_table_name FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "users_own_data_insert"
ON your_table_name FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "users_own_data_update"
ON your_table_name FOR UPDATE
USING (auth.uid() = user_id);

CREATE POLICY "users_own_data_delete"
ON your_table_name FOR DELETE
USING (auth.uid() = user_id);
*/

-- ========================================
-- TEMPLATE 2: ADMIN OVERRIDE
-- ========================================
-- Allow admins to see/edit everything

/*
CREATE POLICY "admin_all_access"
ON your_table_name FOR ALL
USING (
  auth.jwt() ->> 'role' = 'admin' OR
  auth.uid() = user_id
);
*/

-- ========================================
-- TEMPLATE 3: MULTI-TENANT
-- ========================================
-- For systems with multiple tenants/organizations

/*
CREATE POLICY "tenant_isolation"
ON your_table_name FOR ALL
USING (
  tenant_id IN (
    SELECT tenant_id FROM user_tenants
    WHERE user_id = auth.uid()
  )
);
*/

-- ========================================
-- TEMPLATE 4: PUBLIC READ, OWNER WRITE
-- ========================================
-- Anyone can read, only owner can write

/*
CREATE POLICY "public_read"
ON your_table_name FOR SELECT
USING (
  visibility = 'public' OR
  auth.uid() = user_id
);

CREATE POLICY "owner_write"
ON your_table_name FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "owner_update"
ON your_table_name FOR UPDATE
USING (auth.uid() = user_id);

CREATE POLICY "owner_delete"
ON your_table_name FOR DELETE
USING (auth.uid() = user_id);
*/

-- ========================================
-- TEMPLATE 5: SUBSCRIPTION-BASED ACCESS
-- ========================================
-- Only users with active subscriptions can access

/*
CREATE POLICY "premium_feature_access"
ON your_table_name FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM subscriptions
    WHERE user_id = auth.uid()
    AND status = 'active'
    AND plan_id IN (SELECT id FROM subscription_plans WHERE tier >= 'premium')
  ) OR
  auth.uid() = user_id
);
*/

-- ========================================
-- TEMPLATE 6: TIME-BASED ACCESS
-- ========================================
-- Only access recent data

/*
CREATE POLICY "recent_data_only"
ON your_table_name FOR SELECT
USING (
  auth.uid() = user_id AND
  created_at >= NOW() - INTERVAL '30 days'
);
*/

-- ========================================
-- TEMPLATE 7: SHARED RESOURCE
-- ========================================
-- For resources shared between users (like trading strategies)

/*
CREATE POLICY "shared_strategies"
ON trading_strategies FOR SELECT
USING (
  -- Owner can see
  auth.uid() = user_id OR
  -- Public strategies
  visibility = 'public' OR
  -- Followers can see
  EXISTS (
    SELECT 1 FROM strategy_followers
    WHERE strategy_id = trading_strategies.id
    AND user_id = auth.uid()
  ) OR
  -- Purchased strategies
  EXISTS (
    SELECT 1 FROM user_strategy_access
    WHERE strategy_id = trading_strategies.id
    AND user_id = auth.uid()
    AND (expires_at IS NULL OR expires_at > NOW())
  )
);
*/

-- ========================================
-- TEMPLATE 8: HIERARCHICAL ACCESS
-- ========================================
-- Manager can see team data

/*
CREATE POLICY "team_hierarchy"
ON your_table_name FOR SELECT
USING (
  -- Own data
  auth.uid() = user_id OR
  -- Manager's team
  EXISTS (
    SELECT 1 FROM team_members tm
    JOIN teams t ON tm.team_id = t.id
    WHERE t.manager_id = auth.uid()
    AND tm.user_id = your_table_name.user_id
  )
);
*/

-- ========================================
-- TEMPLATE 9: RELATED RESOURCE ACCESS
-- ========================================
-- Access based on related table (e.g., orders from user's exchange account)

/*
CREATE POLICY "access_via_exchange_account"
ON orders FOR SELECT
USING (
  auth.uid() IN (
    SELECT user_id FROM exchange_accounts
    WHERE id = orders.account_id
  )
);
*/

-- ========================================
-- TEMPLATE 10: SERVICE ROLE BYPASS
-- ========================================
-- Allow service role (backend) to bypass RLS

/*
CREATE POLICY "service_role_bypass"
ON your_table_name FOR ALL
USING (
  auth.role() = 'service_role' OR
  auth.uid() = user_id
);
*/

-- ========================================
-- TEMPLATE 11: READ-ONLY PUBLIC DATA
-- ========================================
-- For reference tables that everyone can read

/*
CREATE POLICY "public_read_only"
ON reference_table FOR SELECT
USING (true);

-- No INSERT/UPDATE/DELETE policies = only service can modify
*/

-- ========================================
-- TEMPLATE 12: CONDITIONAL FIELD ACCESS
-- ========================================
-- Different access based on table fields

/*
CREATE POLICY "conditional_access"
ON your_table_name FOR SELECT
USING (
  CASE
    WHEN status = 'draft' THEN auth.uid() = user_id
    WHEN status = 'published' THEN true
    WHEN status = 'archived' THEN auth.uid() = user_id OR auth.jwt() ->> 'role' = 'admin'
    ELSE false
  END
);
*/

-- ========================================
-- SPECIFIC EXAMPLES FOR YOUR PROJECT
-- ========================================

-- Example 1: Exchange API Keys (Extra Secure!)
-- Using EXISTS for better performance on large tables
CREATE POLICY "users_own_api_keys_select"
ON exchange_api_keys FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM exchange_accounts
    WHERE id = exchange_api_keys.account_id
    AND user_id = auth.uid()
  )
);

CREATE POLICY "users_own_api_keys_insert"
ON exchange_api_keys FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1 FROM exchange_accounts
    WHERE id = exchange_api_keys.account_id
    AND user_id = auth.uid()
  )
);

-- NOTE: Ensure exchange_accounts has an index on user_id:
-- CREATE INDEX IF NOT EXISTS idx_exchange_accounts_user_id
-- ON exchange_accounts(user_id);

-- Example 2: Trading Strategies (Public + Private)
CREATE POLICY "strategies_visibility"
ON trading_strategies FOR SELECT
USING (
  auth.uid() = user_id OR
  visibility = 'public' OR
  EXISTS (
    SELECT 1 FROM strategy_followers
    WHERE strategy_id = trading_strategies.id
    AND user_id = auth.uid()
  )
);

-- Example 3: Chat Messages (Session Based)
CREATE POLICY "chat_messages_access"
ON chat_messages FOR ALL
USING (
  auth.uid() IN (
    SELECT user_id FROM chat_sessions
    WHERE id = chat_messages.session_id
  )
);

-- Example 4: Market Data (Public Read)
CREATE POLICY "market_data_public_read"
ON market_data FOR SELECT
USING (true);

-- Example 5: Billing History (User + Admin)
CREATE POLICY "billing_user_or_admin"
ON billing_history FOR SELECT
USING (
  auth.uid() = user_id OR
  auth.jwt() ->> 'role' = 'admin'
);

-- Example 6: Backtest Results (Owner Only)
CREATE POLICY "backtest_owner_only"
ON backtest_results FOR ALL
USING (auth.uid() = user_id);

-- Example 7: Credit Transactions (User Read-Only)
CREATE POLICY "credits_user_read"
ON credit_transactions FOR SELECT
USING (auth.uid() = user_id);

-- Only service role can insert/update
CREATE POLICY "credits_service_write"
ON credit_transactions FOR INSERT
WITH CHECK (auth.role() = 'service_role');

-- Example 8: Audit Logs (Admin + Own)
CREATE POLICY "audit_logs_access"
ON audit_logs FOR SELECT
USING (
  auth.uid() = user_id OR
  auth.jwt() ->> 'role' IN ('admin', 'auditor')
);

-- Example 9: Signal Subscriptions (User + Service)
CREATE POLICY "signal_subscriptions_access"
ON signal_subscriptions FOR SELECT
USING (
  auth.uid() = user_id OR
  auth.role() = 'service_role'
);

-- Example 10: Portfolio with Sharing
CREATE POLICY "portfolio_with_sharing"
ON portfolios FOR SELECT
USING (
  auth.uid() = user_id OR
  -- Shared portfolios
  id IN (
    SELECT portfolio_id FROM portfolio_shares
    WHERE shared_with_user_id = auth.uid()
    AND (expires_at IS NULL OR expires_at > NOW())
  )
);

-- ========================================
-- TESTING YOUR POLICIES
-- ========================================

-- Test 1: Try to access another user's data (should fail)
/*
SET ROLE authenticated;
SET request.jwt.claims.sub TO 'user-uuid-1';
SELECT * FROM users WHERE id = 'user-uuid-2'; -- Should return nothing
*/

-- Test 2: Try to access own data (should work)
/*
SET ROLE authenticated;
SET request.jwt.claims.sub TO 'user-uuid-1';
SELECT * FROM users WHERE id = 'user-uuid-1'; -- Should return data
*/

-- Test 3: Try as admin (should see all)
/*
SET ROLE authenticated;
SET request.jwt.claims.sub TO 'admin-uuid';
SET request.jwt.claims.role TO 'admin';
SELECT * FROM users; -- Should return all users
*/

-- ========================================
-- POLICY DEBUGGING
-- ========================================

-- Check what policies exist
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual,
  with_check
FROM pg_policies
WHERE schemaname = 'public'
AND tablename = 'your_table_name';

-- Check if RLS is enabled
SELECT
  schemaname,
  tablename,
  rowsecurity as rls_enabled,
  relforcerowsecurity as rls_forced
FROM pg_tables
WHERE schemaname = 'public'
AND tablename = 'your_table_name';

-- Explain query with RLS
EXPLAIN (ANALYZE, VERBOSE)
SELECT * FROM your_table_name
WHERE user_id = auth.uid();

-- ========================================
-- IMPORTANT NOTES
-- ========================================

/*
1. Always test policies with different user roles
2. Use USING clause for SELECT/UPDATE/DELETE
3. Use WITH CHECK clause for INSERT/UPDATE
4. Remember: No matching policy = NO ACCESS (by default)
5. Service role (backend) can bypass RLS with security check
6. Combine policies with OR logic, not AND
7. Keep policies simple for better performance
8. Index columns used in policies (like user_id)
9. Use auth.uid() not current_user
10. Test edge cases (null values, deleted users, etc.)
*/

-- ========================================
-- PERFORMANCE TIPS
-- ========================================

/*
1. Create indexes on columns used in policies
   CREATE INDEX idx_table_user_id ON table_name(user_id);

2. Keep policy conditions simple
   Bad:  auth.uid() = (SELECT user_id FROM ... complex query)
   Good: auth.uid() = user_id

3. Use EXISTS instead of IN for large subqueries
   Good: EXISTS (SELECT 1 FROM ... WHERE ...)
   Bad:  id IN (SELECT id FROM ...)

4. Cache auth.uid() if used multiple times
   Use: SECURITY DEFINER function with proper checks

5. Monitor slow queries
   SELECT * FROM pg_stat_statements WHERE mean_time > 1000;
*/
