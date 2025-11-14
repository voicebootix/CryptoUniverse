"""
Test TCP connectivity to Supabase database host.
This tests network connectivity without requiring credentials.
"""
import asyncio
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


async def test_tcp_connectivity():
    """Test TCP connectivity to Supabase database."""
    # From deployment logs: aws-0-ap-southeast-1.pooler.supabase.com:5432
    host = "aws-0-ap-southeast-1.pooler.supabase.com"
    port = 5432
    
    print("=" * 80)
    print("Supabase Database TCP Connectivity Test")
    print("=" * 80)
    print(f"\nTarget: {host}:{port}")
    print(f"Region: ap-southeast-1 (Singapore)")
    print(f"Type: Supabase Connection Pooler")
    
    # Test 1: Quick TCP connection (2s timeout)
    print(f"\n[TEST 1] Quick TCP connection test (2s timeout)")
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=2.0
        )
        writer.close()
        await writer.wait_closed()
        print(f"[OK] Test 1: SUCCESS - TCP connection established!")
        print(f"      The database host is reachable from this network.")
        return True
    except asyncio.TimeoutError:
        print(f"[FAIL] Test 1: TCP connection timeout (2s)")
        print(f"      The database host may be unreachable or slow.")
    except Exception as e:
        print(f"[FAIL] Test 1: {type(e).__name__}: {e}")
    
    # Test 2: Longer TCP connection (5s timeout)
    print(f"\n[TEST 2] TCP connection test with longer timeout (5s)")
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=5.0
        )
        writer.close()
        await writer.wait_closed()
        print(f"[OK] Test 2: SUCCESS - TCP connection established!")
        print(f"      The database host is reachable but slow.")
        return True
    except asyncio.TimeoutError:
        print(f"[FAIL] Test 2: TCP connection timeout (5s)")
        print(f"      The database host is not responding to TCP connections.")
    except Exception as e:
        print(f"[FAIL] Test 2: {type(e).__name__}: {e}")
    
    # Test 3: Even longer timeout (10s)
    print(f"\n[TEST 3] TCP connection test with extended timeout (10s)")
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=10.0
        )
        writer.close()
        await writer.wait_closed()
        print(f"[OK] Test 3: SUCCESS - TCP connection established!")
        print(f"      The database host is reachable but very slow.")
        return True
    except asyncio.TimeoutError:
        print(f"[FAIL] Test 3: TCP connection timeout (10s)")
        print(f"      The database host is not responding at all.")
    except Exception as e:
        print(f"[FAIL] Test 3: {type(e).__name__}: {e}")
    
    return False


if __name__ == "__main__":
    success = asyncio.run(test_tcp_connectivity())
    
    print("\n" + "=" * 80)
    if success:
        print("[OK] TCP connectivity test succeeded!")
        print("     The database host is reachable from this network.")
        print("     Connection issues may be due to:")
        print("     - Authentication/credentials")
        print("     - SSL/TLS handshake problems")
        print("     - Connection pool exhaustion")
        print("     - Database overload")
    else:
        print("[FAIL] TCP connectivity test failed!")
        print("     The database host is not reachable from this network.")
        print("\nPossible causes:")
        print("  1. Network firewall blocking connections")
        print("  2. Supabase pooler is down or unreachable")
        print("  3. Regional connectivity issues")
        print("  4. DNS resolution problems")
        print("\nNote: This test is from your local network.")
        print("      Render deployments may have different network conditions.")
    print("=" * 80)

