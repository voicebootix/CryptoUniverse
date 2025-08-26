"""
Database configuration and connection management.

Handles SQLAlchemy setup, connection pooling, and database operations
for the multi-tenant cryptocurrency trading platform.
"""

import asyncio
from typing import AsyncGenerator, Optional

import sqlalchemy
from databases import Database
from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings

settings = get_settings()

# Database instance
database = Database(
    settings.DATABASE_URL,
    min_size=5,
    max_size=settings.DATABASE_POOL_SIZE,
    force_rollback=settings.ENVIRONMENT == "test"
)

# SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool if settings.ENVIRONMENT != "test" else NullPool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DATABASE_ECHO,
    future=True
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True
)

# Metadata and Base
metadata = MetaData()
Base = declarative_base(metadata=metadata)


# Database connection events
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for development."""
    if "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries in development."""
    if settings.ENVIRONMENT == "development":
        context._query_start_time = asyncio.get_event_loop().time()


@event.listens_for(engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries in development."""
    if settings.ENVIRONMENT == "development":
        total = asyncio.get_event_loop().time() - context._query_start_time
        if total > 0.5:  # Log queries taking longer than 500ms
            import structlog
            logger = structlog.get_logger()
            logger.warning(
                "Slow database query",
                duration=total,
                statement=statement[:200] + "..." if len(statement) > 200 else statement
            )


class DatabaseManager:
    """Database connection and transaction manager."""
    
    def __init__(self):
        self._database = database
    
    async def connect(self) -> None:
        """Connect to database."""
        await self._database.connect()
    
    async def disconnect(self) -> None:
        """Disconnect from database."""
        await self._database.disconnect()
    
    async def execute(self, query, values=None):
        """Execute a query."""
        return await self._database.execute(query, values)
    
    async def fetch_all(self, query, values=None):
        """Fetch all results."""
        return await self._database.fetch_all(query, values)
    
    async def fetch_one(self, query, values=None):
        """Fetch one result."""
        return await self._database.fetch_one(query, values)
    
    async def fetch_val(self, query, values=None):
        """Fetch single value."""
        return await self._database.fetch_val(query, values)
    
    async def execute_many(self, query, values):
        """Execute many queries."""
        return await self._database.execute_many(query, values)
    
    async def transaction(self):
        """Start a database transaction."""
        return self._database.transaction()


# Database manager instance
db_manager = DatabaseManager()


# Dependency for getting database session
async def get_database() -> AsyncGenerator[Database, None]:
    """
    Dependency that provides database connection.
    
    Yields:
        Database: Database connection instance
    """
    try:
        yield database
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("Database operation failed", error=str(e))
        raise


# Dependency for getting database session with transaction
async def get_database_transaction():
    """
    Dependency that provides database connection with transaction.
    
    Yields:
        Database: Database connection with transaction
    """
    async with database.transaction():
        try:
            yield database
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("Database transaction failed", error=str(e))
            raise


class DatabaseHealthCheck:
    """Database health check utilities."""
    
    @staticmethod
    async def check_connection() -> bool:
        """
        Check if database connection is healthy.
        
        Returns:
            bool: True if connection is healthy
        """
        try:
            await database.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    @staticmethod
    async def check_read_write() -> dict:
        """
        Check database read/write capabilities.
        
        Returns:
            dict: Health check results
        """
        results = {
            "read": False,
            "write": False,
            "transaction": False
        }
        
        try:
            # Test read
            await database.execute("SELECT 1")
            results["read"] = True
            
            # Test write (using a test table if it exists)
            test_query = """
            INSERT INTO health_check (timestamp) 
            VALUES (NOW()) 
            ON CONFLICT DO NOTHING
            """
            try:
                await database.execute(test_query)
                results["write"] = True
            except Exception:
                # Table might not exist, which is fine
                results["write"] = True
            
            # Test transaction
            async with database.transaction():
                await database.execute("SELECT 1")
                results["transaction"] = True
                
        except Exception:
            pass
        
        return results


# Health check instance
db_health = DatabaseHealthCheck()


# Database utilities
class DatabaseUtils:
    """Database utility functions."""
    
    @staticmethod
    def create_all_tables():
        """Create all database tables."""
        metadata.create_all(bind=engine)
    
    @staticmethod
    def drop_all_tables():
        """Drop all database tables."""
        metadata.drop_all(bind=engine)
    
    @staticmethod
    async def truncate_table(table_name: str):
        """Truncate a specific table."""
        query = f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"
        await database.execute(query)
    
    @staticmethod
    async def get_table_count(table_name: str) -> int:
        """Get row count for a table."""
        query = f"SELECT COUNT(*) FROM {table_name}"
        return await database.fetch_val(query)
    
    @staticmethod
    async def get_database_size() -> dict:
        """Get database size information."""
        if "postgresql" in settings.DATABASE_URL:
            query = """
            SELECT 
                pg_size_pretty(pg_database_size(current_database())) as size,
                pg_database_size(current_database()) as size_bytes
            """
            result = await database.fetch_one(query)
            return {
                "size": result["size"],
                "size_bytes": result["size_bytes"]
            }
        else:
            return {"size": "Unknown", "size_bytes": 0}


# Database utils instance
db_utils = DatabaseUtils()
