"""
Test cases for handling duplicate data entries
"""
import os
import pytest
from httpx import AsyncClient
from fastapi import status

from app.core.config import settings
from app.main import app

@pytest.mark.asyncio
async def test_duplicate_entry_handling():
    """Test handling of duplicate data entries."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test data
        test_data = {"data": "test_duplicate_entry"}
        
        # First request - should succeed
        response1 = await client.post("/api/v1/data/process", json=test_data)
        assert response1.status_code == status.HTTP_200_OK
        assert response1.json()["status"] == "success"
        
        # Second request with same data - should return 409 Conflict
        response2 = await client.post("/api/v1/data/process", json=test_data)
        assert response2.status_code == status.HTTP_409_CONFLICT
        assert response2.json()["status"] == "error"
        assert "duplicate" in response2.json()["error"].lower()

@pytest.mark.asyncio
async def test_special_characters_handling():
    """Test handling of special characters in data."""
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
        
        # Check if entry exists (should not)
        check1 = await client.post("/api/v1/data/check-duplicate", json=test_data)
        assert check1.status_code == status.HTTP_200_OK
        assert check1.json()["status"] == "unique"
        
        # Create the entry
        create = await client.post("/api/v1/data/process", json=test_data)
        assert create.status_code == status.HTTP_200_OK
        
        # Check again (should exist now)
        check2 = await client.post("/api/v1/data/check-duplicate", json=test_data)
        assert check2.status_code == status.HTTP_200_OK
        assert check2.json()["status"] == "duplicate"
