"""Opportunity discovery related database models."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func

from app.core.database import Base


class StrategyScanningPolicy(Base):
    """Persisted overrides for strategy scanning symbol limits and chunk sizes."""

    __tablename__ = "strategy_scanning_policies"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    strategy_key = Column(String(128), unique=True, nullable=False, index=True)
    max_symbols = Column(Integer, nullable=True)
    chunk_size = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=False, default=100)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_strategy_scanning_policies_enabled_priority", "enabled", "priority"),
    )

    def __repr__(self) -> str:
        return f"<StrategyScanningPolicy(strategy_key={self.strategy_key!r}, enabled={self.enabled})>"
