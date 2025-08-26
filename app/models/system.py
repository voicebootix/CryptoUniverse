"""
System-related database models.

Contains models for system health, audit logs, configuration,
and background tasks for the enterprise platform.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    JSON,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class SystemHealthStatus(str, enum.Enum):
    """System health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditLogLevel(str, enum.Enum):
    """Audit log level enumeration."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TaskStatus(str, enum.Enum):
    """Background task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SystemHealth(Base):
    """System health tracking."""
    
    __tablename__ = "system_health"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    status = Column(Enum(SystemHealthStatus), nullable=False, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    health_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<SystemHealth(service={self.service_name}, status={self.status})>"


class AuditLog(Base):
    """Audit log for compliance and monitoring."""
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)
    level = Column(Enum(AuditLogLevel), default=AuditLogLevel.INFO, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_audit_event_created", "event_type", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog(event={self.event_type}, level={self.level})>"


class SystemConfiguration(Base):
    """System configuration settings."""
    
    __tablename__ = "system_configuration"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    key = Column(String(200), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<SystemConfiguration(key={self.key})>"


class BackgroundTask(Base):
    """Background task tracking."""
    
    __tablename__ = "background_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    task_name = Column(String(200), nullable=False, index=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    task_data = Column(JSON, nullable=True)
    result_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("idx_task_status_created", "status", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<BackgroundTask(name={self.task_name}, status={self.status})>"
