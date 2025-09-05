"""
Data API Endpoints for handling special characters and input validation
"""

import html
import re
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_database
from app.models.data import DataEntry
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/data", tags=["Data"])

class DataRequest(BaseModel):
    """Request model for data processing."""
    data: str = Field(..., description="Data to process")
    
    class Config:
        json_schema_extra = {
            "example": {
                "data": "@#$%^&*()_+==='/</>"
            }
        }

def sanitize_input(data: str) -> str:
    """
    Sanitize input string by escaping HTML and removing dangerous patterns.
    
    Args:
        data: Input string to sanitize
        
    Returns:
        Sanitized string safe for processing
    """
    # HTML escape special characters
    escaped_data = html.escape(data)
    
    # Remove dangerous patterns
    sanitized = re.sub(r'[<>]', '', escaped_data)
    
    # Remove potential script injection patterns
    sanitized = re.sub(r'<script|javascript:', '', sanitized, flags=re.IGNORECASE)
    
    return sanitized

@router.post("/check-duplicate", response_model=Dict[str, Any])
async def check_duplicate_entry(
    request: DataRequest,
    db: AsyncSession = Depends(get_database)
) -> Dict[str, Any]:
    """
    Check if data entry already exists.
    
    Args:
        request: DataRequest containing data to check
        db: Database session
        
    Returns:
        Status indicating if entry is duplicate or unique
    """
    try:
        # Sanitize input
        clean_data = sanitize_input(request.data)
        
        # Check for duplicate
        result = await db.execute(
            select(DataEntry).filter(DataEntry.data == clean_data)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            return {
                "status": "duplicate",
                "message": "Entry already exists",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "status": "unique", 
            "message": "Entry is unique",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Duplicate check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check duplicate: {str(e)}"
        )

@router.post("/process", response_model=Dict[str, Any])
async def handle_special_characters(
    request: DataRequest,
    db: AsyncSession = Depends(get_database)
) -> Dict[str, Any]:
    """
    Process data containing special characters and store if unique.
    
    Args:
        request: DataRequest containing data to process
        db: Database session
        
    Returns:
        Processed data with original and sanitized versions
    """
    try:
        # Log incoming request
        logger.info(
            "Processing special characters",
            data_length=len(request.data),
            contains_special=bool(re.search(r'[^a-zA-Z0-9\s]', request.data))
        )
        
        # Sanitize input
        clean_data = sanitize_input(request.data)
        
        # Check for duplicate
        result = await db.execute(
            select(DataEntry).filter(DataEntry.data == clean_data)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info("Duplicate entry detected")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate entry detected"
            )
        
        # Create new entry
        entry = DataEntry(data=clean_data)
        db.add(entry)
        await db.commit()
        
        # Log processing result
        logger.info(
            "Special characters processed",
            original_length=len(request.data),
            processed_length=len(clean_data),
            entry_id=entry.id
        )
        
        return {
            "status": "success",
            "original_data": request.data,
            "processed_data": clean_data,
            "entry_id": entry.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error processing special characters",
            error=str(e),
            data_preview=request.data[:100] if request.data else None
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing special characters: {str(e)}"
        )

@router.exception_handler(HTTPException)
async def special_char_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """
    Custom exception handler for data processing errors.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status": "error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )