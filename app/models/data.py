"""
Data models for handling special characters and input validation
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from app.core.database import Base

class DataEntry(Base):
    """Model for storing processed data entries."""
    __tablename__ = "data_entries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    data = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<DataEntry(id={self.id}, data={self.data[:30]}...)>"
