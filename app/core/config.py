"""
Application configuration management.

Handles environment variables, settings validation, and configuration for different
deployment environments (development, staging, production).
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import json


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application settings
    ENVIRONMENT: str = Field(default="development", description="Deployment environment")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    HOST: str = Field(default="0.0.0.0", description="Host address")
    PORT: int = Field(default=8000, description="Port number")
    BASE_URL: str = Field(default="http://localhost:8000", description="Base URL for the application")

    # Security settings
    SECRET_KEY: str = Field(..., description="Secret key for JWT and encryption")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiration")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, description="Refresh token expiration")
    API_KEY_EXPIRE_DAYS: int = Field(default=365, description="API key expiration")

    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    ALLOWED_HOSTS: Optional[List[str]] = Field(default=None, description="Allowed hosts")

    # Database settings
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow connections")
    DATABASE_ECHO: bool = Field(default=False, description="Echo SQL queries")

    # Redis settings
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    REDIS_EXPIRE_SECONDS: int = Field(default=3600, description="Default Redis key expiration")

    # Celery settings
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", description="Celery result backend")

    # External service settings
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")

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
    
    @field_validator('CORS_ORIGINS', 'ALLOWED_HOSTS', mode='before')
    @classmethod
    def parse_string_lists(cls, v):
        """Parse string list fields from environment variables."""
        if isinstance(v, str):
            if not v.strip():  # Empty string
                return []
            try:
                # Try to parse as JSON first
                return json.loads(v)
            except json.JSONDecodeError:
                # If not JSON, split by comma
                return [item.strip() for item in v.split(',') if item.strip()]
        return v

    # Exchange API settings
    BINANCE_API_KEY: Optional[str] = Field(default=None, description="Binance API key")
    BINANCE_SECRET_KEY: Optional[str] = Field(default=None, description="Binance secret key")
    KRAKEN_API_KEY: Optional[str] = Field(default=None, description="Kraken API key")
    KRAKEN_SECRET_KEY: Optional[str] = Field(default=None, description="Kraken secret key")
    KUCOIN_API_KEY: Optional[str] = Field(default=None, description="KuCoin API key")
    KUCOIN_SECRET_KEY: Optional[str] = Field(default=None, description="KuCoin secret key")
    KUCOIN_PASSPHRASE: Optional[str] = Field(default=None, description="KuCoin passphrase")

    # Telegram settings
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None, description="Telegram bot token")
    TELEGRAM_CHAT_ID: Optional[str] = Field(default=None, description="Telegram chat ID")

    # Rate limiting settings
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Rate limit requests per window")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Rate limit window in seconds")

    # Credit system settings
    CREDIT_TO_USD_RATIO: float = Field(default=10.0, description="Credits to USD ratio (10 credits = $1)")
    MIN_CREDIT_PURCHASE: int = Field(default=100, description="Minimum credit purchase")
    MAX_CREDIT_PURCHASE: int = Field(default=100000, description="Maximum credit purchase")

    # Trading settings
    DEFAULT_SIMULATION_MODE: bool = Field(default=True, description="Default simulation mode")
    MAX_POSITION_SIZE_PERCENT: float = Field(default=10.0, description="Max position size as % of portfolio")
    DEFAULT_STOP_LOSS_PERCENT: float = Field(default=5.0, description="Default stop loss percentage")
    DEFAULT_TAKE_PROFIT_PERCENT: float = Field(default=10.0, description="Default take profit percentage")

    # Copy trading settings
    COPY_TRADING_FEE_PERCENT: float = Field(default=30.0, description="Platform fee for copy trading")
    MIN_STRATEGY_TRACK_RECORD_DAYS: int = Field(default=30, description="Minimum track record for strategies")
    MAX_COPY_TRADING_RISK_PERCENT: float = Field(default=20.0, description="Max risk per copy trading strategy")

    # File storage settings
    UPLOAD_DIR: str = Field(default="uploads", description="File upload directory")
    MAX_FILE_SIZE_MB: int = Field(default=10, description="Maximum file size in MB")

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_environments = ["development", "staging", "production"]
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of {valid_environments}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level setting."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings with caching.
    
    Returns:
        Settings: Application settings instance
    """
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
