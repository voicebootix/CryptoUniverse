"""
Telegram Integration Models

Per-user Telegram integration for bi-directional communication.
Users connect their Telegram accounts to access trading via chat.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserTelegramConnection(Base):
    """
    User Telegram connection for bi-directional communication.
    
    Stores user's Telegram credentials and chat configuration
    for accessing trading platform via Telegram chat.
    """
    
    __tablename__ = "user_telegram_connections"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Telegram user information
    telegram_user_id = Column(String(50), nullable=False, unique=True, index=True)
    telegram_username = Column(String(100), nullable=True)
    telegram_first_name = Column(String(100), nullable=True)
    telegram_last_name = Column(String(100), nullable=True)
    telegram_chat_id = Column(String(50), nullable=False, index=True)
    
    # Connection settings
    is_active = Column(Boolean, default=True, nullable=False)
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    trading_enabled = Column(Boolean, default=False, nullable=False)  # Requires explicit opt-in
    voice_commands_enabled = Column(Boolean, default=False, nullable=False)
    signal_preferences = Column(JSON, default=dict, nullable=False)

    # Security settings
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    allowed_commands = Column(JSON, default=list, nullable=False)  # Specific commands allowed
    daily_trade_limit = Column(Integer, default=10, nullable=False)
    max_trade_amount_usd = Column(Integer, default=1000, nullable=False)
    
    # Usage tracking
    total_messages_sent = Column(Integer, default=0, nullable=False)
    total_commands_executed = Column(Integer, default=0, nullable=False)
    last_message_at = Column(DateTime, nullable=True)
    last_command_at = Column(DateTime, nullable=True)
    
    # Authentication
    auth_token = Column(String(64), nullable=True)  # For secure command authentication
    auth_expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    connected_at = Column(DateTime, default=func.now(), nullable=False)
    last_active_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="telegram_connections")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", name="unique_user_telegram"),
        Index("idx_telegram_user_chat", "telegram_user_id", "telegram_chat_id"),
        Index("idx_telegram_active", "is_active", "trading_enabled"),
    )
    
    def __repr__(self) -> str:
        return f"<UserTelegramConnection(user_id={self.user_id}, telegram_user_id={self.telegram_user_id})>"
    
    @property
    def is_authenticated(self) -> bool:
        """Check if Telegram connection is authenticated."""
        if not self.auth_token or not self.auth_expires_at:
            return False
        return datetime.utcnow() < self.auth_expires_at
    
    @property
    def can_trade(self) -> bool:
        """Check if user can execute trades via Telegram."""
        return (
            self.is_active and 
            self.trading_enabled and 
            self.is_authenticated
        )
    
    def has_command_permission(self, command: str) -> bool:
        """Check if user has permission for specific command."""
        if not self.allowed_commands:
            return True  # Empty list means all commands allowed
        return command in self.allowed_commands


class TelegramMessage(Base):
    """
    Telegram message history and processing.
    
    Stores all Telegram messages for audit trail and
    natural language processing improvement.
    """
    
    __tablename__ = "telegram_messages"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("user_telegram_connections.id"), nullable=False, index=True)
    
    # Message details
    telegram_message_id = Column(String(50), nullable=False, index=True)
    message_type = Column(String(20), nullable=False)  # text, command, voice, photo
    message_content = Column(Text, nullable=False)
    
    # Processing details
    is_command = Column(Boolean, default=False, nullable=False)
    command_name = Column(String(50), nullable=True, index=True)
    command_parameters = Column(JSON, nullable=True)
    
    # Natural language processing
    intent_detected = Column(String(100), nullable=True)
    confidence_score = Column(Integer, nullable=True)  # 0-100
    entities_extracted = Column(JSON, nullable=True)
    
    # Response details
    response_sent = Column(Boolean, default=False, nullable=False)
    response_content = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Processing status
    processed = Column(Boolean, default=False, nullable=False)
    processing_error = Column(Text, nullable=True)
    
    # Timestamps
    received_at = Column(DateTime, default=func.now(), nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    connection = relationship("UserTelegramConnection")
    
    # Indexes
    __table_args__ = (
        Index("idx_message_connection_received", "connection_id", "received_at"),
        Index("idx_message_command", "is_command", "command_name"),
        Index("idx_message_processed", "processed", "received_at"),
    )
    
    def __repr__(self) -> str:
        return f"<TelegramMessage(id={self.id}, command={self.command_name}, processed={self.processed})>"