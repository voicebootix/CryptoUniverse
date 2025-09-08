"""
Chat Models - Database models for persistent conversation memory

This module defines the database models for storing chat sessions and messages,
enabling persistent conversation memory across server restarts.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, DateTime, Text, JSON, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.database import Base


class ChatSession(Base):
    """
    Chat session model for storing conversation state.
    
    Each session represents a continuous conversation with the AI,
    maintaining context and user preferences across interactions.
    """
    __tablename__ = "chat_sessions"
    
    # Primary identifiers
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Session metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_activity = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Session context and state
    context = Column(JSON, default=dict)  # User preferences, active strategies, etc.
    portfolio_state = Column(JSON)  # Last known portfolio state for context
    active_strategies = Column(JSON, default=list)  # Currently active trading strategies
    
    # Session configuration
    is_active = Column(String, default="true")  # Active status
    session_type = Column(String, default="general")  # general, trading, analysis, etc.
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    user = relationship("User")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_chat_sessions_user_active', 'user_id', 'is_active'),
        Index('ix_chat_sessions_last_activity', 'last_activity'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary format."""
        return {
            "session_id": str(self.session_id),
            "user_id": str(self.user_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "context": self.context or {},
            "portfolio_state": self.portfolio_state,
            "active_strategies": self.active_strategies or [],
            "is_active": self.is_active,
            "session_type": self.session_type,
            "message_count": len(self.messages) if self.messages else 0
        }


class ChatMessage(Base):
    """
    Chat message model for storing individual conversation messages.
    
    Each message represents a single interaction (user or AI response)
    within a chat session, preserving the full conversation history.
    """
    __tablename__ = "chat_messages"
    
    # Primary identifiers
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.session_id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Message content
    content = Column(Text, nullable=False)
    message_type = Column(String, nullable=False)  # user, assistant, system, trade_notification, etc.
    
    # Message metadata
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    intent = Column(String)  # trade_execution, portfolio_analysis, etc.
    confidence = Column(Float)  # AI confidence score (0.0 - 1.0)
    metadata = Column(JSON)  # Additional message-specific data
    
    # Processing state
    processed = Column(String, default="true")  # Processing status
    error_message = Column(Text)  # Any processing errors
    
    # AI model information
    model_used = Column(String)  # Which AI model generated this response
    processing_time_ms = Column(Float)  # Time taken to generate response
    tokens_used = Column(Float)  # Number of tokens consumed
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_chat_messages_session_timestamp', 'session_id', 'timestamp'),
        Index('ix_chat_messages_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_chat_messages_intent', 'intent'),
        Index('ix_chat_messages_type', 'message_type'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return {
            "message_id": str(self.message_id),
            "session_id": str(self.session_id),
            "user_id": str(self.user_id),
            "content": self.content,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "intent": self.intent,
            "confidence": self.confidence,
            "metadata": self.metadata or {},
            "model_used": self.model_used,
            "processing_time_ms": self.processing_time_ms,
            "tokens_used": self.tokens_used,
            "processed": self.processed,
            "error_message": self.error_message
        }


class ChatSessionSummary(Base):
    """
    Chat session summary model for storing condensed conversation history.
    
    When sessions become very long, we create summaries to maintain context
    while reducing token usage in AI requests.
    """
    __tablename__ = "chat_session_summaries"
    
    # Primary identifiers
    summary_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.session_id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Summary content
    summary_text = Column(Text, nullable=False)
    messages_summarized = Column(Float, nullable=False)  # Number of messages included
    summary_type = Column(String, default="conversation")  # conversation, trading_activity, etc.
    
    # Summary metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    start_timestamp = Column(DateTime(timezone=True), nullable=False)  # First message timestamp
    end_timestamp = Column(DateTime(timezone=True), nullable=False)  # Last message timestamp
    
    # Summary statistics
    key_decisions = Column(JSON)  # Important decisions made
    trade_actions = Column(JSON)  # Trading actions performed
    portfolio_changes = Column(JSON)  # Portfolio changes discussed
    
    # Relationships
    user = relationship("User")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_chat_summaries_session_created', 'session_id', 'created_at'),
        Index('ix_chat_summaries_user_created', 'user_id', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary format."""
        return {
            "summary_id": str(self.summary_id),
            "session_id": str(self.session_id),
            "user_id": str(self.user_id),
            "summary_text": self.summary_text,
            "messages_summarized": self.messages_summarized,
            "summary_type": self.summary_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "start_timestamp": self.start_timestamp.isoformat() if self.start_timestamp else None,
            "end_timestamp": self.end_timestamp.isoformat() if self.end_timestamp else None,
            "key_decisions": self.key_decisions or [],
            "trade_actions": self.trade_actions or [],
            "portfolio_changes": self.portfolio_changes or []
        }