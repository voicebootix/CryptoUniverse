#!/usr/bin/env python3
"""
Debug script to test startup components individually
"""
import asyncio
import sys
import traceback

print("🔧 Testing CryptoUniverse startup components...")

# Test 1: Basic imports
print("\n1. Testing imports...")
try:
    from app.core.config import get_settings
    print("✅ Config import successful")

    from app.core.database import engine
    print("✅ Database import successful")

    from app.core.redis import get_redis_client
    print("✅ Redis import successful")

    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 2: Settings
print("\n2. Testing settings...")
try:
    settings = get_settings()
    print(f"✅ Settings loaded - Environment: {settings.ENVIRONMENT}")
    print(f"   Database URL: {settings.DATABASE_URL[:50]}...")
    print(f"   Redis URL: {settings.REDIS_URL}")
except Exception as e:
    print(f"❌ Settings failed: {e}")
    traceback.print_exc()

# Test 3: Redis connection (should be graceful)
print("\n3. Testing Redis connection...")
async def test_redis():
    try:
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            print("✅ Redis connected successfully")
            return True
        else:
            print("⚠️ Redis unavailable (graceful degradation)")
            return False
    except Exception as e:
        print(f"⚠️ Redis failed (expected): {e}")
        return False

# Test 4: Database connection
print("\n4. Testing database connection...")
async def test_database():
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Database connected successfully")
            return True
    except Exception as e:
        print(f"❌ Database failed: {e}")
        traceback.print_exc()
        return False

# Test 5: Table check
print("\n5. Testing database tables...")
async def test_tables():
    try:
        from sqlalchemy import inspect
        async with engine.connect() as conn:
            def check_tables(sync_conn):
                inspector = inspect(sync_conn)
                tables = inspector.get_table_names()
                return len(tables) > 0, tables

            has_tables, table_list = await conn.run_sync(check_tables)
            if has_tables:
                print(f"✅ Found {len(table_list)} database tables")
                return True
            else:
                print("⚠️ No database tables found")
                return False
    except Exception as e:
        print(f"❌ Table check failed: {e}")
        traceback.print_exc()
        return False

# Run all async tests
async def run_tests():
    print("\n🏃 Running async tests...")

    redis_ok = await test_redis()
    db_ok = await test_database()

    if db_ok:
        tables_ok = await test_tables()
    else:
        tables_ok = False

    print("\n📊 Test Summary:")
    print(f"   Redis: {'✅' if redis_ok else '⚠️'}")
    print(f"   Database: {'✅' if db_ok else '❌'}")
    print(f"   Tables: {'✅' if tables_ok else '⚠️'}")

    if db_ok:
        print("\n✅ Core components are working - startup should succeed")
    else:
        print("\n❌ Database issues detected - this may cause startup to hang")

if __name__ == "__main__":
    asyncio.run(run_tests())