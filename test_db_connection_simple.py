"""
Simple database connection test - uses DATABASE_URL directly from environment.
"""
import asyncio
import os
import sys
from urllib.parse import urlparse

import asyncpg

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


async def test_connection():
    """Test database connection with various configurations."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        print("   Please set DATABASE_URL environment variable")
        return False
    
    parsed = urlparse(database_url)
    print("\n" + "=" * 80)
    print("Database Connection Diagnostic Test")
    print("=" * 80)
    print(f"\nDatabase Configuration:")
    print(f"   Host: {parsed.hostname}")
    print(f"   Port: {parsed.port or 5432}")
    print(f"   Database: {parsed.path.lstrip('/')}")
    print(f"   SSL in URL: {'sslmode=' in database_url.lower()}")
    if "pooler" in database_url.lower():
        print(f"   Using Supabase connection pooler")
    
    # Test 1: Simple connection (like old working code)
    print(f"\n[TEST 1] Simple connection (no parameters, 10s timeout)")
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(database_url),
            timeout=10.0
        )
        await conn.execute("SELECT 1")
        result = await conn.fetchval("SELECT version()")
        await conn.close()
        print(f"[OK] Test 1: SUCCESS - Simple connection works!")
        print(f"      PostgreSQL version: {result[:50]}...")
        return True
    except asyncio.TimeoutError:
        print(f"[FAIL] Test 1: Connection timeout (10s)")
    except Exception as e:
        print(f"[FAIL] Test 1: {type(e).__name__}: {e}")
    
    # Test 2: Connection with timeout parameters
    print(f"\n[TEST 2] Connection with timeout parameters (10s timeout)")
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(
                database_url,
                timeout=10.0,
                command_timeout=10.0,
            ),
            timeout=15.0
        )
        await conn.execute("SELECT 1")
        await conn.close()
        print(f"[OK] Test 2: SUCCESS - Connection with timeout works!")
        return True
    except asyncio.TimeoutError:
        print(f"[FAIL] Test 2: Connection timeout (15s)")
    except Exception as e:
        print(f"[FAIL] Test 2: {type(e).__name__}: {e}")
    
    # Test 3: TCP connection test
    print(f"\n[TEST 3] TCP port connectivity test (5s timeout)")
    try:
        host = parsed.hostname
        port = parsed.port or 5432
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=5.0
        )
        writer.close()
        await writer.wait_closed()
        print(f"[OK] Test 3: SUCCESS - TCP connection to {host}:{port} works!")
    except asyncio.TimeoutError:
        print(f"[FAIL] Test 3: TCP connection timeout to {host}:{port} (5s)")
        print(f"      This suggests network/firewall issues")
    except Exception as e:
        print(f"[FAIL] Test 3: {type(e).__name__}: {e}")
    
    # Test 4: Longer timeout
    print(f"\n[TEST 4] Simple connection with longer timeout (30s)")
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(database_url),
            timeout=30.0
        )
        await conn.execute("SELECT 1")
        await conn.close()
        print(f"[OK] Test 4: SUCCESS - Connection works with longer timeout!")
        return True
    except asyncio.TimeoutError:
        print(f"[FAIL] Test 4: Connection timeout even with 30s timeout")
    except Exception as e:
        print(f"[FAIL] Test 4: {type(e).__name__}: {e}")
    
    return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    
    print("\n" + "=" * 80)
    if success:
        print("[OK] At least one connection method succeeded!")
        print("     The database is reachable and responsive.")
    else:
        print("[FAIL] All connection methods failed!")
        print("\nPossible issues:")
        print("  1. Database is down or unreachable")
        print("  2. Network/firewall blocking connections")
        print("  3. Supabase pooler is slow/unresponsive")
        print("  4. Connection pool exhaustion")
        print("  5. Regional connectivity issues")
    print("=" * 80)

