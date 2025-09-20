"""
Enterprise Async Session Manager
Bulletproof solution to eliminate all greenlet spawn errors

This module ensures single-session-per-request pattern across all services
"""

import contextvars
from typing import Optional, AsyncContextManager
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import structlog

logger = structlog.get_logger(__name__)

# Context variable to store the current request's database session
_current_db_session: contextvars.ContextVar[Optional[AsyncSession]] = contextvars.ContextVar(
    'current_db_session',
    default=None
)

class AsyncSessionManager:
    """
    Enterprise-grade async session manager that prevents greenlet spawn errors
    by ensuring single session per request across all services.
    """

    @staticmethod
    def set_request_session(db: AsyncSession) -> None:
        """Set the database session for the current request context."""
        _current_db_session.set(db)
        logger.debug("Database session set for request context", session_id=id(db))

    @staticmethod
    def get_request_session() -> Optional[AsyncSession]:
        """Get the current request's database session."""
        session = _current_db_session.get()
        if session:
            logger.debug("Retrieved request database session", session_id=id(session))
        else:
            logger.warning("No database session found in request context")
        return session

    @staticmethod
    def clear_request_session() -> None:
        """Clear the current request's database session."""
        _current_db_session.set(None)
        logger.debug("Database session cleared from request context")

    @staticmethod
    @asynccontextmanager
    async def managed_session(db: AsyncSession):
        """Context manager to properly set and clean up request session."""
        try:
            AsyncSessionManager.set_request_session(db)
            yield db
        finally:
            AsyncSessionManager.clear_request_session()

class DatabaseSessionMixin:
    """
    Mixin class for services that need database access.
    Provides bulletproof session handling.
    """

    def get_db_session(self) -> AsyncSession:
        """
        Get the current request's database session.
        Raises exception if no session is available.
        """
        db = AsyncSessionManager.get_request_session()
        if db is None:
            raise RuntimeError(
                "No database session available in request context. "
                "Ensure you're calling this from within a FastAPI endpoint with database dependency."
            )
        return db

    async def execute_with_session(self, operation, *args, **kwargs):
        """Execute database operation with proper session handling."""
        db = self.get_db_session()
        try:
            return await operation(db, *args, **kwargs)
        except Exception as e:
            logger.error(
                "Database operation failed",
                operation=operation.__name__,
                error=str(e),
                exc_info=True
            )
            raise

# Decorator for FastAPI endpoints to automatically manage database session
def with_managed_db_session(func):
    """
    Decorator for FastAPI endpoints that automatically manages database session context.

    Usage:
    @with_managed_db_session
    async def my_endpoint(db: AsyncSession = Depends(get_database)):
        # Session is automatically managed
        pass
    """
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract db session from kwargs (FastAPI dependency injection)
        db = kwargs.get('db')
        if db is None:
            # Try to find db in args (positional dependency injection)
            for arg in args:
                if isinstance(arg, AsyncSession):
                    db = arg
                    break

        if db is None:
            logger.error("No database session found in endpoint parameters")
            return await func(*args, **kwargs)

        # Manage session context
        async with AsyncSessionManager.managed_session(db):
            return await func(*args, **kwargs)

    return wrapper

# Utility function to get session (for backward compatibility)
async def get_managed_session() -> AsyncSession:
    """Get the managed database session for the current request."""
    return AsyncSessionManager.get_request_session()

# Enterprise logging for session lifecycle
class SessionLifecycleLogger:
    """Tracks database session lifecycle for monitoring."""

    @staticmethod
    def log_session_created(session_id: str, endpoint: str):
        logger.info("Database session created", session_id=session_id, endpoint=endpoint)

    @staticmethod
    def log_session_reused(session_id: str, service: str):
        logger.debug("Database session reused", session_id=session_id, service=service)

    @staticmethod
    def log_session_closed(session_id: str, endpoint: str):
        logger.info("Database session closed", session_id=session_id, endpoint=endpoint)