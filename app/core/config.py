"""
Application configuration management.

Handles environment variables, settings validation, and configuration for different
deployment environments (development, staging, production).
"""

import os
from functools import lru_cache
from typing import Dict, List, Optional

from pydantic import Field, field_validator, model_validator, computed_field
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
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, env="PORT", description="Server port")
    BASE_URL: str = Field(default="https://cryptouniverse.onrender.com", description="Base URL for the application")
    FRONTEND_URL: str = Field(default="https://cryptouniverse-frontend.onrender.com", description="Frontend URL for redirects")
    ALLOWED_HOSTS: str = Field(default="localhost,127.0.0.1", env="ALLOWED_HOSTS", description="Allowed hosts for the application (comma-separated or JSON list)")
    ADMIN_LOG_BUFFER_SIZE: int = Field(default=500, env="ADMIN_LOG_BUFFER_SIZE", description="Number of log entries to retain in memory for diagnostics")
    
    # Security settings
    SECRET_KEY: str = Field(..., env="SECRET_KEY", description="Secret key for JWT")
    ENCRYPTION_KEY: str = Field(default="", env="ENCRYPTION_KEY", description="Key for encrypting sensitive data like API keys")
    DEBUG_TOKEN: Optional[str] = Field(default=None, env="DEBUG_TOKEN", description="Optional token for accessing debug endpoints in production")
    SIGNALS_WEBHOOK_SECRET: Optional[str] = Field(
        default=None,
        env="SIGNALS_WEBHOOK_SECRET",
        description="HMAC secret for signal delivery webhook callbacks",
    )
    
    # JWT settings
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = Field(default=8, env="JWT_ACCESS_TOKEN_EXPIRE_HOURS", description="JWT access token expiration in hours")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS", description="JWT refresh token expiration in days")
    
    # Database settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL", description="Database connection URL")
    DATABASE_QUERY_TIMEOUT: int = Field(default=10, env="DATABASE_QUERY_TIMEOUT", description="Database query timeout in seconds")

    # Database SSL settings
    DATABASE_SSL_REQUIRE: bool = Field(default=False, env="DATABASE_SSL_REQUIRE", description="Force SSL connection to database")
    DATABASE_SSL_ROOT_CERT: Optional[str] = Field(default=None, env="DATABASE_SSL_ROOT_CERT", description="Path to custom CA certificate file for database SSL")
    DATABASE_SSL_INSECURE: bool = Field(default=False, env="DATABASE_SSL_INSECURE", description="Disable SSL certificate verification (use only for development/testing)")
    SSL_INSECURE_OVERRIDE_ACKNOWLEDGED: bool = Field(default=False, env="SSL_INSECURE_OVERRIDE_ACKNOWLEDGED", description="Acknowledge security risk for insecure SSL override")

    # Redis settings
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL", description="Redis connection URL")
    REDIS_HEALTH_CHECK_INTERVAL: int = Field(default=30, env="REDIS_HEALTH_CHECK_INTERVAL", description="Redis health check interval in seconds")
    
    # CORS settings
    BACKEND_CORS_ORIGINS: str = Field(default="*", env="BACKEND_CORS_ORIGINS", description="Allowed CORS origins (comma-separated or JSON list)")
    CORS_ORIGINS: str = Field(default="", env="CORS_ORIGINS", description="Alternative CORS origins env var")
    
    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from string to list."""
        # Try CORS_ORIGINS first, then fall back to BACKEND_CORS_ORIGINS
        v = self.CORS_ORIGINS or self.BACKEND_CORS_ORIGINS
        if not v or v == "":
            return ["*"]
        # Handle JSON array format
        if v.startswith('['):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        # Handle comma-separated format
        if ',' in v:
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        # Single value
        origins = [v.strip()] if v.strip() else ["*"]
        # Ensure production frontend and base URLs are present
        for url in [self.FRONTEND_URL, self.BASE_URL]:
            if url and url not in origins:
                origins.append(url)
        # If we have specific origins, drop wildcard to satisfy allow_credentials
        if len([o for o in origins if o != "*"]) > 0:
            origins = [o for o in origins if o != "*"]
        return origins
    
    # Enterprise Feature Flags
    CIRCUIT_BREAKER_ENABLED: bool = Field(default=True, env="CIRCUIT_BREAKER_ENABLED", description="Enable circuit breaker protection for external APIs")
    PARALLEL_EXCHANGE_FETCHING: bool = Field(default=True, env="PARALLEL_EXCHANGE_FETCHING", description="Enable parallel exchange balance fetching")
    AB_TESTING_DEMO_MODE: bool = Field(default=False, env="AB_TESTING_DEMO_MODE", description="Enable A/B testing demo mode (unsafe for production)")
    
    # Enterprise Performance Settings
    EXCHANGE_API_TIMEOUT: int = Field(default=15, env="EXCHANGE_API_TIMEOUT", description="Exchange API timeout in seconds")
    
    @computed_field
    @property
    def allowed_hosts(self) -> List[str]:
        """Parse allowed hosts from string to list."""
        v = self.ALLOWED_HOSTS
        if not v or v == "":
            hosts = ["localhost", "127.0.0.1"]
        else:
            # Handle JSON array format
            if v.startswith('['):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        hosts = parsed
                    else:
                        hosts = []
                except (json.JSONDecodeError, TypeError):
                    hosts = []
            elif ',' in v:
                hosts = [host.strip() for host in v.split(',') if host.strip()]
            else:
                hosts = [v.strip()] if v.strip() else ["localhost", "127.0.0.1"]
        # Ensure backend and frontend hosts are included
        for url in [self.BASE_URL, self.FRONTEND_URL]:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                host = parsed.netloc or parsed.path
                if host and host not in hosts:
                    hosts.append(host)
            except Exception:
                pass
        return hosts
    
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
    
    # Telegram settings
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None, env="TELEGRAM_BOT_TOKEN", description="Telegram bot token")
    OWNER_TELEGRAM_CHAT_ID: Optional[str] = Field(default=None, env="OWNER_TELEGRAM_CHAT_ID", description="Owner's Telegram chat ID")
    ALERTS_TELEGRAM_CHAT_ID: Optional[str] = Field(default=None, env="ALERTS_TELEGRAM_CHAT_ID", description="Alerts Telegram chat ID")
    TRADING_TELEGRAM_CHAT_ID: Optional[str] = Field(default=None, env="TRADING_TELEGRAM_CHAT_ID", description="Trading Telegram chat ID")
    
    # Market data API keys
    ALPHA_VANTAGE_API_KEY: Optional[str] = Field(default=None, env="ALPHA_VANTAGE_API_KEY", description="Alpha Vantage API key")
    COINGECKO_API_KEY: Optional[str] = Field(default=None, env="COINGECKO_API_KEY", description="CoinGecko API key")
    FINNHUB_API_KEY: Optional[str] = Field(default=None, env="FINNHUB_API_KEY", description="Finnhub API key")
    
    # OAuth settings
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, description="Google OAuth client ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, description="Google OAuth client secret")
    OAUTH_REDIRECT_URL: str = Field(
        default=os.environ.get(
            "OAUTH_REDIRECT_URL",
            "https://cryptouniverse-frontend.onrender.com/auth/callback"
        ),
        description="OAuth redirect URL"
    )
    API_V1_PREFIX: str = Field(default="https://cryptouniverse.onrender.com/api/v1", description="API v1 prefix URL")

    # Chat credit consumption settings
    CHAT_CREDIT_COST_DEFAULT: int = Field(
        default=1,
        env="CHAT_CREDIT_COST_DEFAULT",
        ge=0,
        description="Default number of credits consumed per chargeable chat interaction",
    )
    CHAT_CREDIT_COST_OVERRIDES: str = Field(
        default="{}",
        env="CHAT_CREDIT_COST_OVERRIDES",
        description="JSON object mapping chat intents or conversation modes to specific credit costs",
    )

    # Validator to prevent insecure SSL in production
    @model_validator(mode="after")
    def _validate_ssl_policy(self):
        """Prevent DATABASE_SSL_INSECURE=true in production unless explicitly acknowledged."""
        if (getattr(self, "ENVIRONMENT", "development") == "production" and
            getattr(self, "DATABASE_SSL_INSECURE", False) and
            not getattr(self, "SSL_INSECURE_OVERRIDE_ACKNOWLEDGED", False)):
            raise ValueError(
                "DATABASE_SSL_INSECURE=true is not allowed in production environment. "
                "This setting disables certificate verification and exposes connections to MITM attacks. "
                "For production, use DATABASE_SSL_ROOT_CERT with proper CA certificate instead. "
                "If you absolutely must override this (emergency only), set SSL_INSECURE_OVERRIDE_ACKNOWLEDGED=true"
            )
        return self

    @computed_field
    @property
    def chat_credit_cost_overrides(self) -> Dict[str, int]:
        """Parse chat credit cost overrides from JSON payload."""
        raw_value = getattr(self, "CHAT_CREDIT_COST_OVERRIDES", "{}")
        if not raw_value:
            return {}

        try:
            parsed = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
        except (TypeError, json.JSONDecodeError):
            return {}

        if not isinstance(parsed, dict):
            return {}

        normalized: Dict[str, int] = {}
        for key, value in parsed.items():
            try:
                normalized[str(key)] = max(0, int(value))
            except (TypeError, ValueError):
                continue

        return normalized

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore'  # Ignore extra environment variables


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
