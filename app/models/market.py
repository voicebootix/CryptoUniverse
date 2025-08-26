"""
Market data-related database models.

Contains models for market data, symbols, and technical indicators
for the cryptocurrency trading platform.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class MarketData(Base):
    """Real-time market data storage."""
    
    __tablename__ = "market_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, index=True)
    price = Column(Numeric(25, 8), nullable=False)
    volume_24h = Column(Numeric(25, 8), nullable=False)
    market_cap = Column(Numeric(20, 2), nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_market_symbol_exchange_time", "symbol", "exchange", "timestamp"),
    )
    
    def __repr__(self) -> str:
        return f"<MarketData(symbol={self.symbol}, exchange={self.exchange}, price={self.price})>"


class Symbol(Base):
    """Trading symbol definitions."""
    
    __tablename__ = "symbols"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    symbol = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<Symbol(symbol={self.symbol}, name={self.name})>"


class TechnicalIndicator(Base):
    """Technical indicator calculations."""
    
    __tablename__ = "technical_indicators"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    indicator_name = Column(String(50), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    value = Column(Numeric(25, 8), nullable=False)
    meta_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_indicator_symbol_name_time", "symbol", "indicator_name", "timestamp"),
    )
    
    def __repr__(self) -> str:
        return f"<TechnicalIndicator(symbol={self.symbol}, indicator={self.indicator_name}, value={self.value})>"
