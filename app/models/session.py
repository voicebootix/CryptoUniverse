"""
User Session Models

Contains models for tracking user sessions, login history,
and authentication state management.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserSession(Base):
    """User session tracking for authentication and security."""
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    refresh_token = Column(String(500), nullable=False, unique=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_refresh_token", "refresh_token"),
        Index("idx_user_sessions_expires_at", "expires_at"),
        Index("idx_user_sessions_active", "is_active", "expires_at"),
    )
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class LoginHistory(Base):
    """Login history tracking for security and analytics."""
    __tablename__ = "login_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    login_at = Column(DateTime(timezone=True), server_default=func.now())
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)  # Geolocation
    device_fingerprint = Column(String(100), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="login_history")
    
    # Indexes
    __table_args__ = (
        Index("idx_login_history_user_id", "user_id"),
        Index("idx_login_history_login_at", "login_at"),
        Index("idx_login_history_success", "success"),
        Index("idx_login_history_ip", "ip_address"),
    )
    
    def __repr__(self):
        return f"<LoginHistory(id={self.id}, user_id={self.user_id}, success={self.success})>"