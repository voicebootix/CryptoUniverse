"""
Application configuration management.

Handles environment variables, settings validation, and configuration for different
deployment environments (development, staging, production).
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import json


class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables and .env files.
    """
    # Project settings
    PROJECT_NAME: str = "CryptoUniverse Enterprise API"
    PROJECT_VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment settings
    ENVIRONMENT: str = Field(default="development", description="Application environment")
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # Security settings
    SECRET_KEY: str = Field(..., env="SECRET_KEY", description="Secret key for JWT")
    
    # Database settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL", description="Database connection URL")
    
    # Redis settings
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL", description="Redis connection URL")
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = Field(default=["*"], env="BACKEND_CORS_ORIGINS", description="Allowed CORS origins")
    
    # Supabase settings
    SUPABASE_URL: Optional[str] = Field(default=None, env="SUPABASE_URL", description="Supabase project URL")
    SUPABASE_KEY: Optional[str] = Field(default=None, env="SUPABASE_KEY", description="Supabase API key")
    
    # Email settings
    SMTP_SERVER: Optional[str] = Field(default=None, description="SMTP server")
    SMTP_PORT: int = Field(default=587, description="SMTP port")
    SMTP_USERNAME: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    FROM_EMAIL: str = Field(default="noreply@cryptouniverse.com", description="From email address")
    
    # Stripe settings
    STRIPE_SECRET_KEY: Optional[str] = Field(default=None, description="Stripe secret key")
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Stripe webhook secret")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = Field(default=None, description="Stripe publishable key")
    
    # AI service settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    GOOGLE_AI_API_KEY: Optional[str] = Field(default=None, description="Google AI API key")
    
    # OAuth settings
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, description="Google OAuth client ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, description="Google OAuth client secret")
    OAUTH_REDIRECT_URL: str = Field(default="https://cryptouniverse.onrender.com/auth/callback", description="OAuth redirect URL")
    API_V1_PREFIX: str = Field(default="https://cryptouniverse.onrender.com/api/v1", description="API v1 prefix URL")
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Environment-specific configurations
class DevelopmentSettings(Settings):
    """Development environment settings."""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_ECHO: bool = True


class ProductionSettings(Settings):
    """Production environment settings."""
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    DATABASE_ECHO: bool = False


def get_settings_for_environment(environment: str) -> Settings:
    """
    Get settings for specific environment.
    
    Args:
        environment: Environment name
        
    Returns:
        Settings: Environment-specific settings
    """
    if environment == "development":
        return DevelopmentSettings()
    elif environment == "production":
        return ProductionSettings()
    else:
        return Settings()


# Export commonly used settings
settings = get_settings()
