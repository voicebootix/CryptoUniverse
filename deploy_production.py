#!/usr/bin/env python3
"""
CryptoUniverse Enterprise - Production Deployment Script

Complete production deployment script for Render.com with Supabase database.
Handles environment validation, database setup, service initialization,
and health verification.

Run this script in your Render deployment to ensure proper setup.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

import structlog

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.core.logging import configure_logging

# Initialize logging first
configure_logging("INFO", "production")
logger = structlog.get_logger(__name__)


async def validate_environment():
    """Validate all required environment variables are set."""
    logger.info("🔍 Validating production environment variables...")
    
    required_vars = {
        "SECRET_KEY": "JWT secret key",
        "DATABASE_URL": "Supabase database URL", 
        "REDIS_URL": "Redis connection URL",
        "ENCRYPTION_KEY": "API key encryption key"
    }
    
    optional_vars = {
        "OPENAI_API_KEY": "OpenAI API for AI trading",
        "ANTHROPIC_API_KEY": "Anthropic API for AI consensus",
        "GOOGLE_CLIENT_ID": "Google OAuth client ID",
        "GOOGLE_CLIENT_SECRET": "Google OAuth secret",
        "STRIPE_SECRET_KEY": "Stripe payment processing",
        "SUPABASE_URL": "Supabase project URL",
        "SUPABASE_KEY": "Supabase anon key"
    }
    
    missing_required = []
    missing_optional = []
    
    # Check required variables
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_required.append(f"{var} ({description})")
    
    # Check optional variables
    for var, description in optional_vars.items():
        if not os.getenv(var):
            missing_optional.append(f"{var} ({description})")
    
    if missing_required:
        logger.error(
            "❌ Missing required environment variables",
            missing=missing_required
        )
        return False
    
    if missing_optional:
        logger.warning(
            "⚠️ Missing optional environment variables - some features may be limited",
            missing=missing_optional
        )
    
    logger.info("✅ Environment validation passed")
    return True


async def verify_database_schema():
    """Verify database schema is properly set up."""
    logger.info("🔍 Verifying Supabase database schema...")
    
    try:
        from app.core.database import engine
        from sqlalchemy import text
        
        async with engine.begin() as conn:
            # Check if core tables exist
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN (
                    'users', 'tenants', 'exchange_accounts', 
                    'exchange_api_keys', 'exchange_balances', 
                    'trades', 'positions', 'orders',
                    'trading_strategies', 'portfolios', 
                    'credit_accounts', 'credit_transactions'
                )
                ORDER BY table_name
            """))
            
            existing_tables = [row[0] for row in result.fetchall()]
            
            required_tables = [
                'users', 'tenants', 'exchange_accounts', 'exchange_api_keys',
                'exchange_balances', 'trades', 'positions', 'orders',
                'trading_strategies', 'portfolios', 'credit_accounts', 'credit_transactions'
            ]
            
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if missing_tables:
                logger.error(
                    "❌ Missing database tables",
                    missing=missing_tables,
                    existing=existing_tables
                )
                return False
            
            logger.info("✅ Database schema verification passed", tables=existing_tables)
            return True
            
    except Exception as e:
        logger.error("❌ Database schema verification failed", error=str(e))
        return False


async def test_service_integrations():
    """Test all service integrations."""
    logger.info("🔍 Testing service integrations...")
    
    try:
        # Test user exchange service
        from app.services.user_exchange_service import user_exchange_service
        logger.info("✅ User exchange service loaded")
        
        # Test real market data service
        from app.services.real_market_data_service import real_market_data_service
        btc_price = await real_market_data_service.get_real_time_price("BTC")
        if btc_price.get("success"):
            logger.info("✅ Real market data service operational", btc_price=btc_price.get("price"))
        else:
            logger.warning("⚠️ Market data service issues", error=btc_price.get("error"))
        
        # Test trade execution service
        from app.services.trade_execution import TradeExecutionService
        trade_executor = TradeExecutionService()
        logger.info("✅ Trade execution service loaded")
        
        # Test production monitoring
        from app.services.production_monitoring import production_monitoring
        health = await production_monitoring.get_system_health()
        logger.info("✅ Production monitoring operational", health_score=health.get("health_score"))
        
        return True
        
    except Exception as e:
        logger.error("❌ Service integration test failed", error=str(e))
        return False


async def main():
    """Main deployment verification."""
    logger.info("🚀 CryptoUniverse Enterprise - Production Deployment Verification")
    logger.info(f"🕐 Started at: {datetime.utcnow().isoformat()}")
    
    checks = [
        ("Environment Variables", validate_environment),
        ("Database Schema", verify_database_schema),
        ("Service Integrations", test_service_integrations)
    ]
    
    failed_checks = []
    
    for check_name, check_func in checks:
        logger.info(f"🔄 Running: {check_name}")
        try:
            success = await check_func()
            if success:
                logger.info(f"✅ {check_name} - PASSED")
            else:
                logger.error(f"❌ {check_name} - FAILED")
                failed_checks.append(check_name)
        except Exception as e:
            logger.error(f"❌ {check_name} - ERROR", error=str(e))
            failed_checks.append(check_name)
    
    if failed_checks:
        logger.error(
            "❌ Deployment verification failed",
            failed_checks=failed_checks,
            success_rate=f"{((len(checks) - len(failed_checks)) / len(checks)) * 100:.1f}%"
        )
        return False
    
    logger.info("🎉 Production deployment verification completed successfully!")
    logger.info("🚀 System is ready for production traffic")
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if success:
            print("\n✅ DEPLOYMENT VERIFICATION PASSED")
            print("🚀 Your CryptoUniverse Enterprise is production-ready!")
            sys.exit(0)
        else:
            print("\n❌ DEPLOYMENT VERIFICATION FAILED")
            print("🔧 Please check the logs and fix the issues before deploying")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 DEPLOYMENT VERIFICATION CRASHED: {e}")
        sys.exit(1)