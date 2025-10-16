"""
Database configuration and connection management.

Handles SQLAlchemy 2.x async setup, connection pooling, and database operations
for the multi-tenant cryptocurrency trading platform.
"""

import asyncio
import logging
import os
import ssl
from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator, Optional

import sqlalchemy
from sqlalchemy import MetaData, event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings

settings = get_settings()

def create_ssl_context() -> ssl.SSLContext:
    """Create SSL context with secure defaults; trust a provided root CA; optional break-glass disable via flag."""
    import logging
    logger = logging.getLogger(__name__)

    # Debug logging to see what environment variables are being read
    ssl_require = getattr(settings, "DATABASE_SSL_REQUIRE", False)
    ssl_insecure = getattr(settings, "DATABASE_SSL_INSECURE", False)
    ssl_override = getattr(settings, "SSL_INSECURE_OVERRIDE_ACKNOWLEDGED", False)
    environment = getattr(settings, "ENVIRONMENT", "unknown")

    logger.warning(f"SSL Configuration Debug - ENV: {environment}, SSL_REQUIRE: {ssl_require}, SSL_INSECURE: {ssl_insecure}, SSL_OVERRIDE: {ssl_override}")

    cafile = getattr(settings, "DATABASE_SSL_ROOT_CERT", None)
    context = ssl.create_default_context(cafile=cafile) if cafile else ssl.create_default_context()

    # Secure defaults
    try:
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    except Exception:
        pass
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    # Explicit, opt-in insecure mode (avoid in prod)
    if ssl_insecure:
        logger.warning("DATABASE_SSL_INSECURE=true: disabling certificate and hostname verification")
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        logger.warning("SSL context configured for insecure mode")
    else:
        logger.warning("SSL context using secure mode (certificate verification enabled)")

    return context

# Convert sync DATABASE_URL to async if needed
def get_async_database_url() -> str:
    """Convert database URL to async version."""
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        # Convert to asyncpg format
        async_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        # Remove sslmode from URL if present (will be handled in connect_args)
        if "?sslmode=" in async_url:
            async_url = async_url.split("?sslmode=")[0]
        elif "&sslmode=" in async_url:
            parts = async_url.split("&sslmode=")
            async_url = parts[0] + ("&" + "&".join(parts[1].split("&")[1:]) if "&" in parts[1] else "")
        return async_url
    elif db_url.startswith("sqlite://"):
        return db_url.replace("sqlite://", "sqlite+aiosqlite://")
    return db_url

# ENTERPRISE SQLAlchemy async engine optimized for Render production
# Environment configurable pool size for proper scaling under load

# Configure execution options based on database type
async_db_url = get_async_database_url()
execution_options = {"compiled_cache": {}}  # Enable query compilation cache

# Only set isolation level for PostgreSQL (not supported by SQLite)
if "postgresql" in async_db_url:
    execution_options["isolation_level"] = "READ_COMMITTED"

# ENTERPRISE: Use QueuePool for production performance
poolclass = QueuePool if "postgresql" in async_db_url else NullPool

engine = create_async_engine(
    async_db_url,
    poolclass=poolclass,
    # ENTERPRISE: Connection pooling for production
    pool_size=20,          # Base number of connections
    max_overflow=30,       # Additional connections when needed
    pool_timeout=30,       # Timeout for getting connection
    pool_pre_ping=True,    # ENTERPRISE: Health check connections
    pool_recycle=1800,     # PRODUCTION: Recycle connections (30 min)
    echo=getattr(settings, 'DATABASE_ECHO', False),
    future=True,
    # ENTERPRISE: Production performance settings
    execution_options=execution_options,
    # PRODUCTION: Optimized settings for asyncpg driver
    connect_args={
        "command_timeout": 30,  # Command timeout in seconds
        "timeout": 60,  # Connection timeout in seconds
        **({"ssl": create_ssl_context()} if ("supabase" in get_async_database_url().lower() or getattr(settings, 'DATABASE_SSL_REQUIRE', False) or getattr(settings, 'DATABASE_SSL_ROOT_CERT', None)) else {}),
        # Server settings for asyncpg (keeping only safe settings)
        "server_settings": {
            "application_name": "cryptouniverse_production"
        }
    } if "postgresql" in async_db_url else {}
)

# Async session factory with proper session-level settings
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False  # Move autoflush to sessionmaker where it belongs
)

# Metadata and Base
metadata = MetaData()
Base = declarative_base(metadata=metadata)


# Database connection events for async engine
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for development."""
    if "sqlite" in get_async_database_url():
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@event.listens_for(engine.sync_engine, "connect")
def set_postgresql_timeouts(dbapi_connection, _connection_record):
    """Set PostgreSQL connection-level timeouts to avoid per-session overhead."""
    logger = logging.getLogger(__name__)

    if "postgresql" in get_async_database_url():
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("SET statement_timeout = '30s'")  # Production timeout
            cursor.execute("SET lock_timeout = '10s'")  # Production lock timeout
            cursor.execute("SET idle_in_transaction_session_timeout = '30s'")  # Clean up idle transactions
            cursor.close()
        except Exception as e:
            logger.debug("Failed to set PostgreSQL connection timeouts", exc_info=True)


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Track query performance for enterprise monitoring."""
    import time
    context._query_start_time = time.time()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries for enterprise performance monitoring."""
    import time
    import structlog
    
    total = time.time() - getattr(context, '_query_start_time', time.time())
    logger = structlog.get_logger()
    
    # ENTERPRISE: Log all slow queries regardless of environment
    if total > 0.5:  # ENTERPRISE: Error on queries >500ms
        logger.error(
            "Very slow database query",
            duration=total,
            statement=statement[:200] + "..." if len(statement) > 200 else statement
        )
    elif total > 0.2:  # ENTERPRISE STANDARD: Warn on queries >200ms
        logger.warning(
            "Slow database query",
            duration=total,
            statement=statement[:200] + "..." if len(statement) > 200 else statement
        )
    
    # Record metrics for monitoring
    try:
        from app.services.system_monitoring import system_monitoring_service
        system_monitoring_service.metrics_collector.record_metric(
            "database_query_time_ms", 
            total * 1000,
            {"statement_type": statement.split()[0].upper() if statement else "UNKNOWN"}
        )
    except Exception:
        # Don't fail queries if monitoring is unavailable
        pass


class DatabaseManager:
    """Database connection and transaction manager using SQLAlchemy 2.x async."""
    
    def __init__(self):
        self._engine = engine
        self._query_times = {}  # Track query performance
        self._slow_query_threshold = 1.0  # 1 second threshold
    
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
    
    async def execute_with_monitoring(self, query, values=None, query_name="unknown"):
        """Execute query with performance monitoring."""
        import time
        start_time = time.time()
        
        try:
            async with self._engine.begin() as conn:
                if values:
                    result = await conn.execute(text(query), values)
                else:
                    result = await conn.execute(text(query))
                
                execution_time = time.time() - start_time
                
                # Track query performance
                if query_name not in self._query_times:
                    self._query_times[query_name] = []
                self._query_times[query_name].append(execution_time)
                
                # Log slow queries
                if execution_time > self._slow_query_threshold:
                    import structlog
                    logger = structlog.get_logger()
                    logger.warning(
                        "Slow database query detected",
                        query_name=query_name,
                        execution_time=execution_time,
                        threshold=self._slow_query_threshold,
                        query_preview=query[:100] + "..." if len(query) > 100 else query
                    )
                
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            import structlog
            logger = structlog.get_logger()
            logger.error(
                "Database query failed",
                query_name=query_name,
                execution_time=execution_time,
                error=str(e),
                query_preview=query[:100] + "..." if len(query) > 100 else query
            )
            raise
    
    def get_query_performance_stats(self):
        """Get query performance statistics."""
        stats = {}
        for query_name, times in self._query_times.items():
            if times:
                stats[query_name] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "slow_queries": len([t for t in times if t > self._slow_query_threshold])
                }
        return stats
    
    def reset_performance_stats(self):
        """Reset query performance statistics."""
        self._query_times.clear()


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


@asynccontextmanager
async def get_database_session() -> AsyncIterator[AsyncSession]:
    """Context manager wrapper for obtaining a database session outside FastAPI dependencies."""

    session: AsyncSession = AsyncSessionLocal()
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


# ENTERPRISE: Database session dependencies removed - use the main get_database function above


async def get_optimized_database() -> AsyncSession:
    """
    Dependency to get optimized database session for heavy queries.
    
    Provides async database session optimized for analytical/reporting queries.
    """
    async with AsyncSessionLocal() as session:
        try:
            # ENTERPRISE: Optimize for analytical queries
            if "postgresql" in get_async_database_url():
                await session.execute(text("SET work_mem = '256MB'"))
                await session.execute(text("SET statement_timeout = '60s'"))
                await session.execute(text("SET random_page_cost = 1.1"))  # SSD optimization
            
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
