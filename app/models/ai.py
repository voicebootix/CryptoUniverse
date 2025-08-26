"""
AI-related database models.

Contains models for AI model management, consensus tracking,
and signal generation for the trading platform.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class AIModelProvider(str, enum.Enum):
    """AI model provider enumeration."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    CUSTOM = "custom"


class SignalType(str, enum.Enum):
    """Signal type enumeration."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class AIModel(Base):
    """AI model configurations and tracking."""
    
    __tablename__ = "ai_models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False)
    provider = Column(Enum(AIModelProvider), nullable=False, index=True)
    model_version = Column(String(50), nullable=False)
    configuration = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<AIModel(name={self.name}, provider={self.provider})>"


class AIConsensus(Base):
    """AI consensus decision tracking."""
    
    __tablename__ = "ai_consensus"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    consensus_signal = Column(Enum(SignalType), nullable=False)
    confidence_score = Column(Numeric(5, 2), nullable=False)
    model_responses = Column(JSON, nullable=False)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_consensus_symbol_created", "symbol", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<AIConsensus(symbol={self.symbol}, signal={self.consensus_signal}, confidence={self.confidence_score})>"


class AISignal(Base):
    """Individual AI model signals."""
    
    __tablename__ = "ai_signals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id"), nullable=False, index=True)
    consensus_id = Column(UUID(as_uuid=True), ForeignKey("ai_consensus.id"), nullable=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal = Column(Enum(SignalType), nullable=False)
    confidence = Column(Numeric(5, 2), nullable=False)
    reasoning = Column(Text, nullable=True)
    raw_response = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    model = relationship("AIModel")
    consensus = relationship("AIConsensus")
    
    __table_args__ = (
        Index("idx_signal_symbol_model_created", "symbol", "model_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<AISignal(symbol={self.symbol}, signal={self.signal}, confidence={self.confidence})>"
