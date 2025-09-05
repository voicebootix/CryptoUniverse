"""
Test cases for handling duplicate data entries
"""
import os
import pytest
from httpx import AsyncClient
from fastapi import status, HTTPException, Request
from fastapi.responses import JSONResponse
from datetime import datetime, UTC

from app.core.config import settings
from app.api.v1.endpoints.data import router as data_router
from app.core.database import get_database
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import pytest_asyncio
from unittest.mock import AsyncMock, patch

# Create mock database session
mock_db = AsyncMock(spec=AsyncSession)
mock_db.commit = AsyncMock()

# Create mock result
class MockResult:
    def __init__(self, value=None):
        self._value = value
    
    def scalar_one_or_none(self):
        return self._value

async def override_get_database():
    return mock_db

app = FastAPI()
app.include_router(data_router, prefix="/api/v1")
app.dependency_overrides[get_database] = override_get_database

@app.exception_handler(HTTPException)
async def special_char_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """Custom exception handler for data processing errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status": "error",
            "timestamp": datetime.now(UTC).isoformat()
        }
    )

@pytest.mark.asyncio
async def test_duplicate_entry_handling():
    """Test handling of duplicate data entries."""
    # Setup mock responses
    mock_db.execute = AsyncMock(return_value=MockResult(None))
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test data
        test_data = {"data": "test_duplicate_entry"}
        
        # First request - should succeed
        response1 = await client.post("/api/v1/data/process", json=test_data)
        assert response1.status_code == status.HTTP_200_OK
        assert response1.json()["status"] == "success"
        
        # Reset mock for second request to simulate duplicate
        mock_db.execute = AsyncMock(return_value=MockResult(mock_db))
        
        # Second request with same data - should return 409 Conflict
        response2 = await client.post("/api/v1/data/process", json=test_data)
        assert response2.status_code == status.HTTP_409_CONFLICT
        assert response2.json()["status"] == "error"
        assert "duplicate" in response2.json()["error"].lower()

@pytest.mark.asyncio
async def test_special_characters_handling():
    """Test handling of special characters in data."""
    # Setup mock response
    mock_db.execute = AsyncMock(return_value=MockResult(None))
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test data with special characters
        test_data = {"data": "@#$%^&*()_+=='/</> with spaces"}
        
        # Send request
        response = await client.post("/api/v1/data/process", json=test_data)
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert result["status"] == "success"
        assert result["original_data"] == test_data["data"]
        assert "<" not in result["processed_data"]  # Dangerous chars should be removed
        assert ">" not in result["processed_data"]

@pytest.mark.asyncio
async def test_duplicate_check_endpoint():
    """Test the dedicated duplicate check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        test_data = {"data": "unique_test_entry"}
        
        # Setup mock for first check (not exists)
        mock_db.execute = AsyncMock(return_value=MockResult(None))
        
        # Check if entry exists (should not)
        check1 = await client.post("/api/v1/data/check-duplicate", json=test_data)
        assert check1.status_code == status.HTTP_200_OK
        assert check1.json()["status"] == "unique"
        
        # Setup mock for create (not exists)
        mock_db.execute = AsyncMock(return_value=MockResult(None))
        
        # Create the entry
        create = await client.post("/api/v1/data/process", json=test_data)
        assert create.status_code == status.HTTP_200_OK
        
        # Setup mock for second check (exists)
        mock_db.execute = AsyncMock(return_value=MockResult(mock_db))
        
        # Check again (should exist now)
        check2 = await client.post("/api/v1/data/check-duplicate", json=test_data)
        assert check2.status_code == status.HTTP_200_OK
        assert check2.json()["status"] == "duplicate"
