# CryptoUniverse Database Migrations

This directory contains two types of database migrations with different purposes and deployment strategies.

---

## Migration Types

### 1. Alembic Python Migrations (`*.py`)
**Purpose:** Application-level schema changes
**Deployment:** Automatic via Alembic during application startup/deployment
**Examples:**
- `001_create_user_strategy_access.py` - Creates tables and columns
- `002_migrate_redis_strategy_data.py` - Data migrations
- `update_win_rate_data.py` - Data transformation scripts

**When to use:**
- Creating/modifying tables
- Adding/removing columns
- Creating indexes for application queries
- Data migrations and transformations
- Foreign key relationships

**Managed by:** Alembic (Python SQLAlchemy migrations)

---

### 2. Supabase SQL Migrations (`supabase_*.sql`)
**Purpose:** Supabase-specific security, RLS policies, and database-level optimizations
**Deployment:** Manual execution via Supabase SQL Editor (NOT auto-deployment)
**Examples:**
- `supabase_001_security_fix_enable_rls_on_all_tables.sql` - Row Level Security policies
- `supabase_006_security_fix_security_definer_views.sql` - View security properties
- `supabase_007_performance_fix_exchange_balances_upsert.sql` - Database-level optimizations

**When to use:**
- Enabling/modifying RLS policies
- Converting view security properties (SECURITY DEFINER/INVOKER)
- Database-level performance tuning (fillfactor, autovacuum settings)
- Supabase auth function optimizations
- Extension management

**Managed by:** Manual deployment via Supabase Dashboard → SQL Editor

---

## Why Two Migration Systems?

### Separation of Concerns

**Alembic (Application Layer)**
- ✅ Schema changes that application code depends on
- ✅ Automatically tracked with version control
- ✅ Can be rolled back with `alembic downgrade`
- ✅ Runs with application database user permissions

**Supabase SQL (Security/Optimization Layer)**
- ✅ Security policies using Supabase auth functions (`auth.uid()`, `auth.jwt()`)
- ✅ Requires elevated Supabase service role privileges
- ✅ Performance optimizations that need careful monitoring
- ✅ Changes that should be verified before application deployment

---

## Deployment Strategy

### Alembic Migrations (Automatic)

```bash
# Development
alembic upgrade head

# Production (automatic via deployment)
# Runs during application startup
```

### Supabase Migrations (Manual)

**DO NOT merge these to main for auto-deployment!**

Instead:

1. Open Supabase Dashboard → SQL Editor
2. Copy/paste each migration file in order
3. Execute one at a time
4. Verify with provided SQL queries
5. Monitor application logs between migrations

See `SUPABASE_SECURITY_FIXES_DEPLOYMENT_GUIDE.md` for detailed instructions.

---

## File Naming Convention

### Alembic Migrations
```
001_create_user_strategy_access.py
002_migrate_redis_strategy_data.py
003_add_new_feature.py
```

### Supabase Migrations
```
supabase_001_security_fix_enable_rls_on_all_tables.sql
supabase_002_security_fix_auth_rls_initplan_optimization.sql
supabase_003_performance_fix_consolidate_permissive_policies.sql
```

**Note:** The `supabase_` prefix prevents conflicts with Alembic migration numbers.

---

## Current Migration Files

### Alembic Python Migrations
- `001_create_user_strategy_access.py` - User strategy access table
- `002_migrate_redis_strategy_data.py` - Redis to PostgreSQL migration
- `update_win_rate_data.py` - Win rate calculation updates

### Supabase SQL Migrations (Pending Deployment)
- `supabase_001` - Enable RLS on 80+ tables (CRITICAL)
- `supabase_002` - Optimize auth RLS policies (HIGH)
- `supabase_003` - Consolidate permissive policies (HIGH)
- `supabase_004` - Fix function search_path (MEDIUM)
- `supabase_005` - Vector extension preparation (MEDIUM)
- `supabase_006` - Fix SECURITY DEFINER views (HIGH)
- `supabase_007` - Optimize exchange_balances UPSERT (CRITICAL)

**Status:** Ready for manual deployment via Supabase SQL Editor

---

## Creating New Migrations

### For Application Schema Changes (Use Alembic)

```bash
# Create new migration
alembic revision -m "add_new_column_to_users"

# Edit the generated file in migrations/
# Add upgrade() and downgrade() logic

# Test locally
alembic upgrade head

# Commit and deploy
git add migrations/003_add_new_column_to_users.py
git commit -m "feat: Add new column to users table"
```

### For Supabase Security/RLS Changes (Use SQL)

1. Create file: `migrations/supabase_008_your_change_description.sql`
2. Write SQL with proper comments and verification queries
3. Test in Supabase SQL Editor (development environment)
4. Document in deployment guide
5. Deploy manually to production
6. Commit for documentation purposes only

```bash
git add migrations/supabase_008_your_change_description.sql
git commit -m "docs: Add Supabase RLS policy for new feature"
```

---

## Best Practices

### ✅ DO
- Use Alembic for schema changes that code depends on
- Use Supabase SQL for RLS, security, and optimization
- Test Supabase migrations in development first
- Monitor query performance after Supabase migrations
- Document verification queries in migration files
- Keep migration files small and focused

### ❌ DON'T
- Don't auto-deploy Supabase SQL migrations
- Don't mix application schema and RLS in same migration
- Don't skip verification steps in Supabase migrations
- Don't modify existing migration files after deployment
- Don't create Alembic migrations for RLS policies

---

## Troubleshooting

### Issue: Alembic migration fails
**Solution:** Check database connection, ensure previous migrations ran, verify SQL syntax

### Issue: Supabase migration causes permission errors
**Solution:** Verify you're running in SQL Editor with service_role privileges, not application user

### Issue: RLS policy blocks application
**Solution:** Check policy logic, verify `auth.uid()` matches expected user IDs, test with service_role

### Issue: Migration naming conflict
**Solution:** Use `supabase_` prefix for all Supabase SQL migrations

---

## Documentation

- **Supabase Deployment Guide:** `SUPABASE_SECURITY_FIXES_DEPLOYMENT_GUIDE.md`
- **Supabase Fixes Summary:** `SUPABASE_FIXES_SUMMARY.md`
- **Alembic Documentation:** https://alembic.sqlalchemy.org/

---

Last Updated: 2025-11-06
Migration System Version: Alembic + Supabase Manual SQL
