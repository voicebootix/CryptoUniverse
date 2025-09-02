#!/usr/bin/env python3
"""
Run database migrations for CryptoUniverse platform.

This script applies the necessary database schema updates to fix
production issues including missing user_id columns.
"""

import asyncio
import logging
import os
import sys
from alembic import command
from alembic.config import Config
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine

# Add app to path for imports
sys.path.append(os.path.dirname(__file__))

from app.core.config import get_settings
from app.core.database import get_async_database_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_and_fix_database():
    """Check database schema and apply fixes."""
    settings = get_settings()
    engine = create_async_engine(get_async_database_url())
    
    try:
        async with engine.begin() as conn:
            # Get current database state
            result = await conn.run_sync(inspect)
            
            logger.info("Checking database schema...")
            
            # Check if trades table exists
            if 'trades' in result.get_table_names():
                columns = [col['name'] for col in result.get_columns('trades')]
                logger.info(f"Trades table columns: {columns}")
                
                # Check for missing user_id column
                if 'user_id' not in columns:
                    logger.warning("trades.user_id column missing - migration needed")
                else:
                    logger.info("trades.user_id column exists")
            else:
                logger.warning("trades table does not exist")
            
            # Test a simple query to verify connectivity
            await conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        raise
    finally:
        await engine.dispose()

def run_alembic_migration():
    """Run alembic migrations."""
    try:
        # Create alembic config
        alembic_cfg = Config("alembic.ini")
        
        logger.info("Running database migrations...")
        
        # Run the migration
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

async def main():
    """Main migration script."""
    logger.info("Starting database migration process...")
    
    try:
        # Check current state
        await check_and_fix_database()
        
        # Run migrations
        run_alembic_migration()
        
        # Verify after migration
        await check_and_fix_database()
        
        logger.info("Database migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration process failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
