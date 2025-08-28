"""
Test configuration settings parsing and validation.
"""
import os
import pytest
from app.core.config import Settings


class TestCORSParsing:
    """Test CORS origins parsing from various formats."""
    
    def test_empty_cors(self):
        """Test empty CORS defaults to ['*']."""
        settings = Settings(
            SECRET_KEY="test-key",
            DATABASE_URL="postgresql://test",
            BACKEND_CORS_ORIGINS=""
        )
        assert settings.cors_origins == ["*"]
    
    def test_single_origin(self):
        """Test single origin parsing."""
        settings = Settings(
            SECRET_KEY="test-key",
            DATABASE_URL="postgresql://test",
            BACKEND_CORS_ORIGINS="https://example.com"
        )
        assert settings.cors_origins == ["https://example.com"]
    
    def test_comma_separated_origins(self):
        """Test comma-separated origins parsing."""
        settings = Settings(
            SECRET_KEY="test-key",
            DATABASE_URL="postgresql://test",
            BACKEND_CORS_ORIGINS="https://url1.com,https://url2.com"
        )
        assert settings.cors_origins == ["https://url1.com", "https://url2.com"]
    
    def test_json_array_origins(self):
        """Test JSON array origins parsing."""
        settings = Settings(
            SECRET_KEY="test-key",
            DATABASE_URL="postgresql://test",
            BACKEND_CORS_ORIGINS='["https://url1.com", "https://url2.com"]'
        )
        assert settings.cors_origins == ["https://url1.com", "https://url2.com"]
    
    def test_wildcard_origin(self):
        """Test wildcard origin."""
        settings = Settings(
            SECRET_KEY="test-key",
            DATABASE_URL="postgresql://test",
            BACKEND_CORS_ORIGINS="*"
        )
        assert settings.cors_origins == ["*"]
    
    def test_extra_env_vars_ignored(self):
        """Test that extra environment variables are ignored."""
        # This should not raise an error even with extra fields
        settings = Settings(
            SECRET_KEY="test-key",
            DATABASE_URL="postgresql://test",
            BACKEND_CORS_ORIGINS="*",
            CORS_ORIGINS="ignored",  # Extra field
            RANDOM_VAR="also_ignored"  # Another extra field
        )
        assert settings.cors_origins == ["*"]
        # Verify the extra fields don't become attributes
        assert not hasattr(settings, 'CORS_ORIGINS')
        assert not hasattr(settings, 'RANDOM_VAR')
