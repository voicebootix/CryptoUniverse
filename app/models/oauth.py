"""
OAuth Provider Models

Contains models for OAuth authentication providers, user OAuth connections,
and social login integration for the CryptoUniverse platform.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class OAuthProvider(str, enum.Enum):
    """OAuth provider enumeration."""
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    APPLE = "apple"


class UserOAuthConnection(Base):
    """
    User OAuth provider connections.
    
    Links users to their OAuth provider accounts (Google, GitHub, etc.)
    for social login functionality.
    """
    
    __tablename__ = "user_oauth_connections"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # OAuth provider info
    provider = Column(String(20), nullable=False, index=True)  # google, github, etc.
    provider_user_id = Column(String(100), nullable=False)  # OAuth provider's user ID
    provider_username = Column(String(100), nullable=True)  # Username from provider
    provider_email = Column(String(255), nullable=True)  # Email from provider
    
    # OAuth tokens (encrypted in production)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Provider profile data
    profile_data = Column(JSON, nullable=True)  # Raw profile data from provider
    avatar_url = Column(String(500), nullable=True)
    profile_url = Column(String(500), nullable=True)
    
    # Connection metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="oauth_connections")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
        Index("idx_oauth_provider", "provider"),
        Index("idx_oauth_provider_user_id", "provider_user_id"),
        Index("idx_oauth_user_id", "user_id"),
        Index("idx_oauth_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<UserOAuthConnection(id={self.id}, user_id={self.user_id}, provider={self.provider})>"


class OAuthState(Base):
    """
    OAuth state tracking for CSRF protection.
    
    Stores temporary OAuth state tokens to prevent CSRF attacks
    during the OAuth flow.
    """
    
    __tablename__ = "oauth_states"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # State data
    state_token = Column(String(64), unique=True, nullable=False, index=True)
    provider = Column(String(20), nullable=False)
    redirect_url = Column(String(500), nullable=True)  # Where to redirect after auth
    
    # Request metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Expiration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    is_used = Column(Boolean, default=False, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_oauth_state_token", "state_token"),
        Index("idx_oauth_state_expires", "expires_at"),
        Index("idx_oauth_state_used", "is_used"),
    )
    
    def __repr__(self):
        return f"<OAuthState(id={self.id}, provider={self.provider}, used={self.is_used})>"
