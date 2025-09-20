"""
Enterprise Database Service Layer - Bulletproof Architecture

This service provides a bulletproof abstraction layer over SQLAlchemy async operations
with comprehensive error handling, connection management, and query optimization.

Features:
- Bulletproof async query patterns
- Connection pool management
- Transaction management with rollback
- Query performance monitoring
- Enterprise error handling
- Model field validation
- Audit logging

Author: CTO Assistant
Date: September 20, 2025
"""

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any, Type, TypeVar, Union, Sequence
from uuid import UUID
import structlog

from sqlalchemy import select, update, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import (
    SQLAlchemyError, 
    IntegrityError, 
    DataError, 
    OperationalError,
    TimeoutError as SQLTimeoutError
)
from sqlalchemy.sql import Select
from pydantic import BaseModel

from app.core.database import get_database, Base, engine
from app.core.config import get_settings
from app.core.redis import get_redis_client

settings = get_settings()
logger = structlog.get_logger(__name__)

# Type variable for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=Base)


class DatabaseError(Exception):
    """Base database error with context."""
    def __init__(self, message: str, operation: str, model: str = None, context: Dict = None):
        self.message = message
        self.operation = operation
        self.model = model
        self.context = context or {}
        super().__init__(message)


class QueryMetrics(BaseModel):
    """Query performance metrics."""
    query_type: str
    model: str
    execution_time_ms: float
    rows_affected: int
    success: bool
    error_message: Optional[str] = None


class EnterpriseDatabase:
    """
    Enterprise Database Service - Bulletproof Operations
    
    Provides a robust abstraction layer over SQLAlchemy async operations
    with comprehensive error handling and performance monitoring.
    """
    
    def __init__(self):
        # Create async session factory bound to the existing engine
        self.async_session = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self.query_metrics: List[QueryMetrics] = []
        self.connection_pool_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_execution_time": 0.0
        }
    
    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        """Get database session with bulletproof error handling."""
        async with self.async_session() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.exception("Database session error", error=str(e))
                raise DatabaseError(
                    message=f"Database session error: {str(e)}",
                    operation="session_management",
                    context={"error_type": type(e).__name__}
                ) from e
    
    async def execute_query(
        self,
        query: Select,
        model_name: str,
        operation: str = "select",
        session: AsyncSession = None
    ) -> Any:
        """Execute query with bulletproof error handling and metrics."""
        start_time = time.perf_counter()
        rows_affected = 0
        success = False
        error_message = None
        
        try:
            if session:
                result = await session.execute(query)
            else:
                async with self.get_session() as db:
                    result = await db.execute(query)
            
            # Don't consume results - let callers handle them
            if getattr(result, "returns_rows", False):
                rows_affected = -1  # unknown without consumption
            else:
                rows_affected = getattr(result, "rowcount", 0) or 0
            
            success = True
            self.connection_pool_stats["successful_queries"] += 1
            return result
            
        except (IntegrityError, DataError) as e:
            error_message = f"Data integrity error: {str(e)}"
            logger.exception("Database integrity error", 
                           model=model_name, 
                           operation=operation,
                           error=str(e))
            raise DatabaseError(
                message=error_message,
                operation=operation,
                model=model_name,
                context={"error_type": "integrity", "original_error": str(e)}
            ) from e
            
        except (OperationalError, SQLTimeoutError) as e:
            error_message = f"Database operational error: {str(e)}"
            logger.exception("Database operational error", 
                           model=model_name, 
                           operation=operation,
                           error=str(e))
            raise DatabaseError(
                message=error_message,
                operation=operation,
                model=model_name,
                context={"error_type": "operational", "original_error": str(e)}
            ) from e
            
        except SQLAlchemyError as e:
            error_message = f"SQLAlchemy error: {str(e)}"
            logger.exception("SQLAlchemy error", 
                           model=model_name, 
                           operation=operation,
                           error=str(e))
            raise DatabaseError(
                message=error_message,
                operation=operation,
                model=model_name,
                context={"error_type": "sqlalchemy", "original_error": str(e)}
            ) from e
            
        except Exception as e:
            error_message = f"Unexpected database error: {str(e)}"
            logger.exception("Unexpected database error", 
                           model=model_name, 
                           operation=operation,
                           error=str(e))
            raise DatabaseError(
                message=error_message,
                operation=operation,
                model=model_name,
                context={"error_type": "unexpected", "original_error": str(e)}
            ) from e
            
        finally:
            execution_time = (time.perf_counter() - start_time) * 1000
            
            # Record metrics
            metric = QueryMetrics(
                query_type=operation,
                model=model_name,
                execution_time_ms=execution_time,
                rows_affected=rows_affected,
                success=success,
                error_message=error_message
            )
            self.query_metrics.append(metric)
            
            # Update connection pool stats
            self.connection_pool_stats["total_queries"] += 1
            if not success:
                self.connection_pool_stats["failed_queries"] += 1
            
            # Update average execution time
            total_time = (self.connection_pool_stats["avg_execution_time"] * 
                         (self.connection_pool_stats["total_queries"] - 1) + execution_time)
            self.connection_pool_stats["avg_execution_time"] = total_time / self.connection_pool_stats["total_queries"]
    
    async def get_by_id(
        self, 
        model: Type[ModelType], 
        id_value: Union[UUID, str, int],
        session: AsyncSession = None
    ) -> Optional[ModelType]:
        """Get single record by ID with bulletproof error handling."""
        query = select(model).where(model.id == id_value)
        
        try:
            result = await self.execute_query(query, model.__name__, "get_by_id", session)
            return result.scalar_one_or_none()
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get {model.__name__} by ID: {str(e)}",
                operation="get_by_id",
                model=model.__name__,
                context={"id": str(id_value)}
            ) from e
    
    async def get_by_field(
        self,
        model: Type[ModelType],
        field_name: str,
        field_value: Any,
        session: AsyncSession = None
    ) -> Optional[ModelType]:
        """Get single record by field with bulletproof error handling."""
        if not hasattr(model, field_name):
            raise DatabaseError(
                message=f"Field '{field_name}' does not exist on model {model.__name__}",
                operation="get_by_field",
                model=model.__name__,
                context={"field": field_name, "value": str(field_value)}
            )
        
        field = getattr(model, field_name)
        query = select(model).where(field == field_value)
        
        try:
            result = await self.execute_query(query, model.__name__, "get_by_field", session)
            return result.scalar_one_or_none()
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get {model.__name__} by {field_name}: {str(e)}",
                operation="get_by_field",
                model=model.__name__,
                context={"field": field_name, "value": str(field_value)}
            ) from e
    
    async def list_with_filters(
        self,
        model: Type[ModelType],
        filters: Dict[str, Any] = None,
        order_by: str = None,
        limit: int = None,
        offset: int = None,
        session: AsyncSession = None
    ) -> List[ModelType]:
        """List records with filters and bulletproof error handling."""
        query = select(model)
        
        # Apply filters
        if filters:
            for field_name, value in filters.items():
                if not hasattr(model, field_name):
                    logger.warning(f"Field '{field_name}' does not exist on model {model.__name__}")
                    continue
                
                field = getattr(model, field_name)
                if isinstance(value, list):
                    query = query.where(field.in_(value))
                elif isinstance(value, dict) and 'operator' in value:
                    # Support for complex filters: {'operator': 'gt', 'value': 100}
                    op = value['operator']
                    val = value['value']
                    if op == 'gt':
                        query = query.where(field > val)
                    elif op == 'gte':
                        query = query.where(field >= val)
                    elif op == 'lt':
                        query = query.where(field < val)
                    elif op == 'lte':
                        query = query.where(field <= val)
                    elif op == 'like':
                        query = query.where(field.like(f"%{val}%"))
                    elif op == 'ilike':
                        query = query.where(field.ilike(f"%{val}%"))
                    else:
                        query = query.where(field == val)
                else:
                    query = query.where(field == value)
        
        # Apply ordering
        if order_by:
            if hasattr(model, order_by):
                order_field = getattr(model, order_by)
                query = query.order_by(order_field)
            else:
                logger.warning(f"Order field '{order_by}' does not exist on model {model.__name__}")
        
        # Apply pagination
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        try:
            result = await self.execute_query(query, model.__name__, "list_with_filters", session)
            return result.scalars().all()
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to list {model.__name__} with filters: {str(e)}",
                operation="list_with_filters",
                model=model.__name__,
                context={"filters": filters, "order_by": order_by}
            ) from e
    
    async def create_record(
        self,
        model: Type[ModelType],
        data: Dict[str, Any],
        session: AsyncSession = None
    ) -> ModelType:
        """Create new record with bulletproof error handling."""
        try:
            # Validate fields exist on model
            for field_name in data.keys():
                if not hasattr(model, field_name):
                    raise DatabaseError(
                        message=f"Field '{field_name}' does not exist on model {model.__name__}",
                        operation="create_record",
                        model=model.__name__,
                        context={"invalid_field": field_name, "data": data}
                    )
            
            record = model(**data)
            
            if session:
                session.add(record)
                await session.flush()  # Get the ID without committing
                await session.refresh(record)
            else:
                async with self.get_session() as db:
                    db.add(record)
                    await db.commit()
                    await db.refresh(record)
            
            logger.info(f"Created {model.__name__}", record_id=str(record.id))
            return record
            
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create {model.__name__}: {str(e)}",
                operation="create_record",
                model=model.__name__,
                context={"data": data}
            ) from e
    
    async def update_record(
        self,
        model: Type[ModelType],
        id_value: Union[UUID, str, int],
        data: Dict[str, Any],
        session: AsyncSession = None
    ) -> Optional[ModelType]:
        """Update record with bulletproof error handling."""
        try:
            # Validate fields exist on model
            for field_name in data.keys():
                if not hasattr(model, field_name):
                    raise DatabaseError(
                        message=f"Field '{field_name}' does not exist on model {model.__name__}",
                        operation="update_record",
                        model=model.__name__,
                        context={"invalid_field": field_name, "data": data}
                    )
            
            query = update(model).where(model.id == id_value).values(**data)
            
            if session:
                await session.execute(query)
                # Get updated record
                updated_record = await self.get_by_id(model, id_value, session)
            else:
                async with self.get_session() as db:
                    await db.execute(query)
                    await db.commit()
                    updated_record = await self.get_by_id(model, id_value, db)
            
            if updated_record:
                logger.info(f"Updated {model.__name__}", record_id=str(id_value))
            
            return updated_record
            
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update {model.__name__}: {str(e)}",
                operation="update_record",
                model=model.__name__,
                context={"id": str(id_value), "data": data}
            ) from e
    
    async def delete_record(
        self,
        model: Type[ModelType],
        id_value: Union[UUID, str, int],
        session: AsyncSession = None
    ) -> bool:
        """Delete record with bulletproof error handling."""
        try:
            query = delete(model).where(model.id == id_value)
            
            if session:
                result = await session.execute(query)
                deleted = result.rowcount > 0
            else:
                async with self.get_session() as db:
                    result = await db.execute(query)
                    await db.commit()
                    deleted = result.rowcount > 0
            
            if deleted:
                logger.info(f"Deleted {model.__name__}", record_id=str(id_value))
            
            return deleted
            
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to delete {model.__name__}: {str(e)}",
                operation="delete_record",
                model=model.__name__,
                context={"id": str(id_value)}
            ) from e
    
    async def execute_raw_query(
        self,
        query: str,
        params: Dict[str, Any] = None,
        session: AsyncSession = None
    ) -> Any:
        """Execute raw SQL with bulletproof error handling."""
        try:
            sql_query = text(query)
            
            if session:
                if params:
                    result = await session.execute(sql_query, params)
                else:
                    result = await session.execute(sql_query)
            else:
                async with self.get_session() as db:
                    if params:
                        result = await db.execute(sql_query, params)
                    else:
                        result = await db.execute(sql_query)
            
            logger.info("Executed raw query", query=query[:100])
            return result
            
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to execute raw query: {str(e)}",
                operation="execute_raw_query",
                context={"query": query[:100], "params": params}
            ) from e
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions with bulletproof rollback."""
        async with self.get_session() as session:
            try:
                yield session
                await session.commit()
                logger.debug("Transaction committed successfully")
            except Exception as e:
                await session.rollback()
                logger.exception("Transaction rolled back due to error", error=str(e))
                raise
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics."""
        if not self.query_metrics:
            return {"message": "No metrics available"}
        
        successful_queries = [m for m in self.query_metrics if m.success]
        failed_queries = [m for m in self.query_metrics if not m.success]
        
        return {
            "connection_pool": self.connection_pool_stats,
            "query_performance": {
                "total_queries": len(self.query_metrics),
                "successful_queries": len(successful_queries),
                "failed_queries": len(failed_queries),
                "success_rate": len(successful_queries) / len(self.query_metrics) * 100,
                "avg_execution_time_ms": sum(m.execution_time_ms for m in successful_queries) / len(successful_queries) if successful_queries else 0,
                "slowest_query_ms": max((m.execution_time_ms for m in successful_queries), default=0),
                "fastest_query_ms": min((m.execution_time_ms for m in successful_queries), default=0)
            },
            "error_summary": {
                error.error_message: len([m for m in failed_queries if m.error_message == error.error_message])
                for error in failed_queries
            } if failed_queries else {}
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        try:
            start_time = time.time()
            async with self.get_session() as db:
                await db.execute(text("SELECT 1"))
            
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "connection_time_ms": execution_time,
                "pool_stats": self.connection_pool_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global enterprise database instance
enterprise_db = EnterpriseDatabase()