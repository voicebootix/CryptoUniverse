#!/usr/bin/env python3
"""
🎯 TARGETED QUERY OPTIMIZATION
Based on actual Supabase usage data from production

Your real performance issues:
1. exchange_accounts: 2,108 index scans (super hot!)
2. exchange_api_keys: 1,137 index scans  
3. exchange_balances: 919 index scans
4. user_sessions: 73 rows but very active

NOT data volume - you have tiny tables!
"""

# These are the actual slow queries based on your index usage stats:

OPTIMIZED_QUERIES = {
    "get_user_exchange_accounts": """
        -- OLD: Multiple queries + N+1 problem
        -- SELECT * FROM exchange_accounts WHERE user_id = ?
        -- SELECT * FROM exchange_api_keys WHERE account_id IN (...)
        
        -- NEW: Single optimized query
        SELECT 
            ea.*,
            eak.status as api_key_status,
            eak.expires_at as api_key_expires
        FROM exchange_accounts ea
        LEFT JOIN exchange_api_keys eak ON ea.id = eak.account_id 
        WHERE ea.user_id = ? 
        AND ea.status = 'ACTIVE'
        AND ea.trading_enabled = true
        ORDER BY ea.is_default DESC, ea.created_at;
        
        -- Uses new index: idx_exchange_accounts_user_status_optimized
    """,
    
    "get_active_balances": """
        -- OLD: Scanning all balances then filtering
        -- SELECT * FROM exchange_balances WHERE account_id = ?
        
        -- NEW: Only get non-zero balances (your real use case)
        SELECT 
            eb.*,
            ea.exchange_name,
            ea.user_id
        FROM exchange_balances eb
        JOIN exchange_accounts ea ON eb.account_id = ea.id
        WHERE eb.account_id = ?
        AND eb.total_balance > 0
        ORDER BY eb.usd_value DESC;
        
        -- Uses new index: idx_balances_account_nonzero
    """,
    
    "get_user_active_sessions": """
        -- OLD: Full table scan on sessions
        -- SELECT * FROM user_sessions WHERE user_id = ?
        
        -- NEW: Only active, non-expired sessions
        SELECT *
        FROM user_sessions 
        WHERE user_id = ?
        AND is_active = true 
        AND expires_at > NOW()
        ORDER BY expires_at DESC
        LIMIT 5;
        
        -- Uses new index: idx_sessions_user_active_expires
    """,
    
    "cleanup_expired_sessions": """
        -- Batch cleanup instead of row-by-row
        UPDATE user_sessions 
        SET is_active = false 
        WHERE expires_at < NOW() 
        AND is_active = true;
        
        -- Then delete old inactive sessions
        DELETE FROM user_sessions 
        WHERE is_active = false 
        AND expires_at < NOW() - INTERVAL '30 days';
    """
}

QUERY_TIPS = """
🎯 PERFORMANCE TIPS BASED ON YOUR DATA:

1. **Batch Operations**: You're doing too many single-row queries
   - Instead of N queries for N accounts, use 1 JOIN query
   
2. **Filter Early**: Add WHERE clauses for common filters
   - status = 'ACTIVE' 
   - trading_enabled = true
   - total_balance > 0
   
3. **Limit Results**: You probably don't need all 73 user sessions
   - Add LIMIT clauses
   - Order by most recent first
   
4. **Use Partial Indexes**: For boolean filters (is_active = true)
   - Smaller indexes
   - Faster lookups
   
5. **Connection Pooling**: With only 8 users, you're likely opening too many connections
   - Set max_connections = 5 in your app
   - Use connection pooling properly
"""

if __name__ == "__main__":
    print("🎯 TARGETED OPTIMIZATION QUERIES")
    print("=" * 50)
    
    for query_name, query in OPTIMIZED_QUERIES.items():
        print(f"\n📊 {query_name.upper()}:")
        print(query.strip())
    
    print("\n" + QUERY_TIPS)
