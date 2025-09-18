#!/usr/bin/env python3
"""
Apply the missing simulation mode migration to the database.

This script safely applies the migration that adds simulation_mode, 
simulation_balance, and last_simulation_reset columns to the users table.
"""

import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import get_settings

async def apply_migration():
    """Apply the simulation mode migration to the database."""
    
    settings = get_settings()
    
    # Get async database URL
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        # Remove sslmode from URL if present
        if "?sslmode=" in db_url:
            db_url = db_url.split("?sslmode=")[0]
    
    # Create engine
    engine = create_async_engine(db_url, echo=True)
    
    async with engine.begin() as conn:
        # Check if columns already exist
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('simulation_mode', 'simulation_balance', 'last_simulation_reset')
        """)
        
        result = await conn.execute(check_query)
        existing_columns = [row[0] for row in result]
        
        if len(existing_columns) == 3:
            print("✅ All simulation columns already exist in the database")
            return
        
        print(f"Found {len(existing_columns)} existing columns: {existing_columns}")
        print("Applying migration to add missing columns...")
        
        # Add simulation_mode column if missing
        if 'simulation_mode' not in existing_columns:
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS simulation_mode BOOLEAN NOT NULL DEFAULT true
            """))
            print("✅ Added simulation_mode column")
        
        # Add simulation_balance column if missing  
        if 'simulation_balance' not in existing_columns:
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS simulation_balance INTEGER NOT NULL DEFAULT 10000
            """))
            print("✅ Added simulation_balance column")
        
        # Add last_simulation_reset column if missing
        if 'last_simulation_reset' not in existing_columns:
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS last_simulation_reset TIMESTAMP WITH TIME ZONE
            """))
            print("✅ Added last_simulation_reset column")
        
        # Create index for simulation_mode if it doesn't exist
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_users_simulation_mode 
            ON users (simulation_mode)
        """))
        print("✅ Created index on simulation_mode")
        
        # Update users with active exchange accounts to live mode
        await conn.execute(text("""
            UPDATE users
            SET simulation_mode = false
            WHERE id IN (
                SELECT DISTINCT user_id
                FROM exchange_accounts
                WHERE status = 'active'
                AND trading_enabled = true
            )
            AND simulation_mode = true
        """))
        print("✅ Updated users with active exchange accounts to live mode")
        
        # Update alembic version table to mark migration as applied
        await conn.execute(text("""
            INSERT INTO alembic_version (version_num)
            VALUES ('add_simulation_mode_to_users')
            ON CONFLICT (version_num) DO NOTHING
        """))
        print("✅ Updated alembic version table")
        
    await engine.dispose()
    print("\n🎉 Migration successfully applied!")

if __name__ == "__main__":
    try:
        asyncio.run(apply_migration())
    except Exception as e:
        print(f"❌ Error applying migration: {e}", file=sys.stderr)
        sys.exit(1)