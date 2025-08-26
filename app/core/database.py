"""
Database configuration and connection management.

Handles SQLAlchemy 2.x async setup, connection pooling, and database operations
for the multi-tenant cryptocurrency trading platform.
"""

import asyncio
from typing import AsyncGenerator, Optional

import sqlalchemy
from sqlalchemy import MetaData, event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings

settings = get_settings()

# Convert sync DATABASE_URL to async if needed
def get_async_database_url() -> str:
    """Convert database URL to async version."""
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://")
    elif db_url.startswith("sqlite://"):
        return db_url.replace("sqlite://", "sqlite+aiosqlite://")
    return db_url

# SQLAlchemy async engine
engine = create_async_engine(
    get_async_database_url(),
    poolclass=QueuePool if getattr(settings, 'ENVIRONMENT', 'production') != "test" else NullPool,
    pool_size=getattr(settings, 'DATABASE_POOL_SIZE', 20),
    max_overflow=getattr(settings, 'DATABASE_MAX_OVERFLOW', 0),
    pool_pre_ping=True,
    echo=getattr(settings, 'DATABASE_ECHO', False),
    future=True
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
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
    """Database connection and transaction manager using SQLAlchemy 2.x async."""
    
    def __init__(self):
        self._engine = engine
    
    async def connect(self) -> None:
        """Connect to database."""
        # Engine handles connections automatically
        pass
    
    async def disconnect(self) -> None:
        """Disconnect from database."""
        await self._engine.dispose()
    
    async def execute(self, query, values=None):
        """Execute a query."""
        async with self._engine.begin() as conn:
            if values:
                result = await conn.execute(text(query), values)
            else:
                result = await conn.execute(text(query))
            return result
    
    async def fetch_all(self, query, values=None):
        """Fetch all results."""
        async with self._engine.begin() as conn:
            if values:
                result = await conn.execute(text(query), values)
            else:
                result = await conn.execute(text(query))
            return result.fetchall()
    
    async def fetch_one(self, query, values=None):
        """Fetch one result."""
        async with self._engine.begin() as conn:
            if values:
                result = await conn.execute(text(query), values)
            else:
                result = await conn.execute(text(query))
            return result.fetchone()
    
    async def fetch_val(self, query, values=None):
        """Fetch single value."""
        async with self._engine.begin() as conn:
            if values:
                result = await conn.execute(text(query), values)
            else:
                result = await conn.execute(text(query))
            row = result.fetchone()
            return row[0] if row else None
    
    async def execute_many(self, query, values):
        """Execute many queries."""
        async with self._engine.begin() as conn:
            return await conn.execute(text(query), values)
    
    def transaction(self):
        """Start a database transaction."""
        return self._engine.begin()


# Database manager instance
db_manager = DatabaseManager()


# Dependency for getting database session
async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides database session.
    
    Yields:
        AsyncSession: SQLAlchemy async session instance
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            import structlog
            logger = structlog.get_logger()
            logger.error("Database operation failed", error=str(e))
            raise
        finally:
            await session.close()


# Dependency for getting database session with transaction
async def get_database_transaction():
    """
    Dependency that provides database session with transaction.
    
    Yields:
        AsyncSession: Database session with transaction
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            try:
                yield session
            except Exception as e:
                await session.rollback()
                import structlog
                logger = structlog.get_logger()
                logger.error("Database transaction failed", error=str(e))
                raise
            finally:
                await session.close()


class DatabaseHealthCheck:
    """Database health check utilities using SQLAlchemy 2.x."""
    
    @staticmethod
    async def check_connection() -> bool:
        """
        Check if database connection is healthy.
        
        Returns:
            bool: True if connection is healthy
        """
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
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
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                results["read"] = True
            
                # Test write (basic test)
                try:
                    await conn.execute(text("SELECT 1"))  # Simple test
                    results["write"] = True
                except Exception:
                    results["write"] = False
                
                # Test transaction
                async with conn.begin():
                    await conn.execute(text("SELECT 1"))
                    results["transaction"] = True
                
        except Exception:
            pass
        
        return results


# Health check instance
db_health = DatabaseHealthCheck()


# Database utilities
class DatabaseUtils:
    """Database utility functions using SQLAlchemy 2.x."""
    
    @staticmethod
    async def create_all_tables():
        """Create all database tables."""
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
    
    @staticmethod
    async def drop_all_tables():
        """Drop all database tables."""
        async with engine.begin() as conn:
            await conn.run_sync(metadata.drop_all)
    
    @staticmethod
    async def truncate_table(table_name: str):
        """Truncate a specific table."""
        query = f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"
        async with engine.begin() as conn:
            await conn.execute(text(query))
    
    @staticmethod
    async def get_table_count(table_name: str) -> int:
        """Get row count for a table."""
        query = f"SELECT COUNT(*) FROM {table_name}"
        async with engine.begin() as conn:
            result = await conn.execute(text(query))
            row = result.fetchone()
            return row[0] if row else 0
    
    @staticmethod
    async def get_database_size() -> dict:
        """Get database size information."""
        if "postgresql" in get_async_database_url():
            query = """
            SELECT 
                pg_size_pretty(pg_database_size(current_database())) as size,
                pg_database_size(current_database()) as size_bytes
            """
            async with engine.begin() as conn:
                result = await conn.execute(text(query))
                row = result.fetchone()
                if row:
                    return {
                        "size": row[0],
                        "size_bytes": row[1]
                    }
        return {"size": "Unknown", "size_bytes": 0}


# Database utils instance
db_utils = DatabaseUtils()
