#!/usr/bin/env python3
"""
Migration: Migrate existing Redis strategy data to database
Converts existing user_strategies:{user_id} Redis sets to database records
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set, List, Any
from uuid import UUID

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.strategy_access import UserStrategyAccess, StrategyAccessType, StrategyType
from app.models.user import User

# revision identifiers
revision = '002_migrate_redis_data'
down_revision = '001_user_strategy_access'
branch_labels = None
depends_on = None

settings = get_settings()


async def migrate_redis_to_database():
    """Migrate existing Redis strategy data to database"""

    print("🔄 Starting Redis to Database migration...")

    try:
        # Create async engine for migration
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # Get Redis client
        from app.core.redis import get_redis_client
        redis = await get_redis_client()

        if not redis:
            print("❌ Redis not available - skipping migration")
            return

        # Find all user strategy keys
        strategy_keys = []
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match="user_strategies:*", count=100)
            strategy_keys.extend(keys)
            if cursor == 0:
                break

        print(f"📊 Found {len(strategy_keys)} Redis strategy keys to migrate")

        migration_stats = {
            "total_keys": len(strategy_keys),
            "users_migrated": 0,
            "strategies_migrated": 0,
            "errors": 0,
            "ai_strategies": 0,
            "community_strategies": 0
        }

        async with async_session() as session:
            for key in strategy_keys:
                try:
                    # Extract user_id from key
                    user_id_str = key.decode('utf-8').replace('user_strategies:', '')

                    try:
                        user_uuid = UUID(user_id_str)
                    except ValueError:
                        print(f"⚠️  Invalid UUID format: {user_id_str}")
                        migration_stats["errors"] += 1
                        continue

                    # Check if user exists
                    user_result = await session.execute(
                        sa.select(User).where(User.id == user_uuid)
                    )
                    user = user_result.scalar_one_or_none()

                    if not user:
                        print(f"⚠️  User not found: {user_id_str}")
                        migration_stats["errors"] += 1
                        continue

                    # Get strategy IDs from Redis set
                    strategy_ids = await redis.smembers(key)
                    strategy_ids = [s.decode('utf-8') if isinstance(s, bytes) else s for s in strategy_ids]

                    if not strategy_ids:
                        continue

                    print(f"👤 Migrating user {user_id_str}: {len(strategy_ids)} strategies")

                    user_strategies_migrated = 0

                    for strategy_id in strategy_ids:
                        try:
                            # Determine strategy type and access type
                            if strategy_id.startswith('ai_'):
                                strategy_type = StrategyType.AI_STRATEGY
                                access_type = StrategyAccessType.ADMIN_GRANT if user.role.value == 'admin' else StrategyAccessType.PURCHASED
                                migration_stats["ai_strategies"] += 1
                            else:
                                # Assume community strategy
                                strategy_type = StrategyType.COMMUNITY_STRATEGY
                                access_type = StrategyAccessType.PURCHASED
                                migration_stats["community_strategies"] += 1

                            # Check if access record already exists
                            existing = await session.execute(
                                sa.select(UserStrategyAccess).where(
                                    sa.and_(
                                        UserStrategyAccess.user_id == user_uuid,
                                        UserStrategyAccess.strategy_id == strategy_id
                                    )
                                )
                            )

                            if existing.scalar_one_or_none():
                                print(f"  ⏭️  Already exists: {strategy_id}")
                                continue

                            # Create access record
                            access_record = UserStrategyAccess(
                                user_id=user_uuid,
                                strategy_id=strategy_id,
                                strategy_type=strategy_type,
                                access_type=access_type,
                                subscription_type="permanent" if user.role.value == 'admin' else "monthly",
                                credits_paid=0 if user.role.value == 'admin' else 25,
                                expires_at=None if user.role.value == 'admin' else None,
                                is_active=True,
                                metadata={
                                    "migrated_from_redis": True,
                                    "migration_date": datetime.utcnow().isoformat(),
                                    "original_redis_key": key.decode('utf-8')
                                }
                            )

                            session.add(access_record)
                            user_strategies_migrated += 1
                            migration_stats["strategies_migrated"] += 1

                            print(f"  ✅ Migrated: {strategy_id} ({strategy_type.value}, {access_type.value})")

                        except Exception as e:
                            print(f"  ❌ Failed to migrate strategy {strategy_id}: {e}")
                            migration_stats["errors"] += 1

                    if user_strategies_migrated > 0:
                        migration_stats["users_migrated"] += 1
                        print(f"  📝 User {user_id_str}: {user_strategies_migrated} strategies migrated")

                except Exception as e:
                    print(f"❌ Failed to process key {key}: {e}")
                    migration_stats["errors"] += 1

            # Commit all changes
            await session.commit()

        await engine.dispose()

        print("\n" + "="*60)
        print("🎉 REDIS TO DATABASE MIGRATION COMPLETED")
        print("="*60)
        print(f"📊 Total Redis keys processed: {migration_stats['total_keys']}")
        print(f"👥 Users migrated: {migration_stats['users_migrated']}")
        print(f"🎯 Total strategies migrated: {migration_stats['strategies_migrated']}")
        print(f"🤖 AI strategies: {migration_stats['ai_strategies']}")
        print(f"👥 Community strategies: {migration_stats['community_strategies']}")
        print(f"❌ Errors: {migration_stats['errors']}")
        print("="*60)

        return migration_stats

    except Exception as e:
        print(f"💥 Migration failed: {e}")
        raise e


async def create_admin_default_access():
    """Create default access records for admin users"""

    print("🔑 Creating default admin strategy access...")

    try:
        # Create async engine
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # Get AI strategy catalog
        ai_strategies = {
            "risk_management": "AI Risk Management",
            "portfolio_optimization": "AI Portfolio Optimization",
            "spot_momentum_strategy": "AI Spot Momentum",
            "futures_arbitrage": "AI Futures Arbitrage",
            "options_strategies": "AI Options Strategies",
            "statistical_arbitrage": "AI Statistical Arbitrage",
            "market_making": "AI Market Making",
            "pairs_trading": "AI Pairs Trading",
            "volatility_trading": "AI Volatility Trading",
            "news_sentiment": "AI News Sentiment"
        }

        async with async_session() as session:
            # Get all admin users
            admin_result = await session.execute(
                sa.select(User).where(User.role == 'admin')
            )
            admin_users = admin_result.scalars().all()

            print(f"👑 Found {len(admin_users)} admin users")

            total_granted = 0

            for admin_user in admin_users:
                print(f"🔧 Granting access to admin: {admin_user.email}")

                user_granted = 0

                for strategy_key, strategy_name in ai_strategies.items():
                    strategy_id = f"ai_{strategy_key}"

                    # Check if already exists
                    existing = await session.execute(
                        sa.select(UserStrategyAccess).where(
                            sa.and_(
                                UserStrategyAccess.user_id == admin_user.id,
                                UserStrategyAccess.strategy_id == strategy_id
                            )
                        )
                    )

                    if existing.scalar_one_or_none():
                        continue

                    # Create admin access record
                    access_record = UserStrategyAccess(
                        user_id=admin_user.id,
                        strategy_id=strategy_id,
                        strategy_type=StrategyType.AI_STRATEGY,
                        access_type=StrategyAccessType.ADMIN_GRANT,
                        subscription_type="permanent",
                        credits_paid=0,
                        expires_at=None,
                        is_active=True,
                        metadata={
                            "admin_default_grant": True,
                            "strategy_name": strategy_name,
                            "granted_date": datetime.utcnow().isoformat()
                        }
                    )

                    session.add(access_record)
                    user_granted += 1
                    total_granted += 1

                print(f"  ✅ Granted {user_granted} strategies to {admin_user.email}")

            await session.commit()

        await engine.dispose()

        print(f"🎉 Admin access setup complete: {total_granted} strategies granted")
        return total_granted

    except Exception as e:
        print(f"💥 Admin access setup failed: {e}")
        raise e


def upgrade():
    """Run the migration"""

    print("🚀 Starting unified strategy system migration...")

    # Run async migration
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Step 1: Migrate existing Redis data
        migration_stats = loop.run_until_complete(migrate_redis_to_database())

        # Step 2: Create default admin access
        admin_grants = loop.run_until_complete(create_admin_default_access())

        print("\n" + "="*70)
        print("🎊 UNIFIED STRATEGY SYSTEM MIGRATION COMPLETED")
        print("="*70)
        print(f"✅ Redis strategies migrated: {migration_stats['strategies_migrated']}")
        print(f"✅ Users migrated: {migration_stats['users_migrated']}")
        print(f"✅ Admin strategies granted: {admin_grants}")
        print("✅ Enterprise unified strategy system is now active!")
        print("="*70)

    except Exception as e:
        print(f"💥 Migration failed: {e}")
        raise e

    finally:
        loop.close()


def downgrade():
    """Reverse the migration (remove migrated data)"""

    print("⚠️  Downgrading: Removing migrated strategy access data...")

    # This would remove all migrated records
    # In production, you might want to be more selective
    op.execute("""
        DELETE FROM user_strategy_access
        WHERE metadata->>'migrated_from_redis' = 'true'
        OR metadata->>'admin_default_grant' = 'true'
    """)

    print("✅ Migration downgrade completed")