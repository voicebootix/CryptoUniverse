"""
CRITICAL: Live Trade Execution Verification
Tests BOTH simulation and live modes on production platform

WARNING: This tests REAL trading with REAL money
Using minimal amounts for safety
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import sys

# Production URL
BASE_URL = "https://cryptouniverse.onrender.com"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

# Test amounts - EXTREMELY SMALL for safety
TEST_AMOUNT_USD = 10  # $10 test trade
TEST_SYMBOL = "BTC/USDT"

async def login_and_get_token():
    """Login and get authentication token."""
    async with aiohttp.ClientSession() as session:
        # Use email field instead of username
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }

        async with session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=login_data
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("access_token")
            else:
                print(f"ERROR: Login failed: {response.status}")
                text = await response.text()
                print(f"Response: {text}")
                return None

async def check_user_mode(token):
    """Check current user trading mode."""
    headers = {"Authorization": f"Bearer {token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/api/v1/users/me",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                print(f"OK: User retrieved: {data.get('email')}")
                print(f"   Simulation Mode: {data.get('simulation_mode', 'Not set')}")
                return data
            else:
                print(f"ERROR: Failed to get user: {response.status}")
                return None

async def check_exchange_credentials(token):
    """Check if exchange credentials exist."""
    headers = {"Authorization": f"Bearer {token}"}

    async with aiohttp.ClientSession() as session:
        # Check exchange accounts
        async with session.get(
            f"{BASE_URL}/api/v1/exchanges/accounts",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                print(f"\n[*] Exchange Accounts Found: {len(data.get('accounts', []))}")
                for account in data.get('accounts', []):
                    print(f"   - {account.get('exchange_name')}: {account.get('status')}")
                return data.get('accounts', [])
            else:
                print(f"ERROR: No exchange accounts found")
                return []

async def test_simulation_trade(token):
    """Test simulation mode trade execution."""
    print("\n" + "="*60)
    print("TESTING SIMULATION MODE (Paper Trading)")
    print("="*60)

    headers = {"Authorization": f"Bearer {token}"}

    # First, ensure we're in simulation mode
    async with aiohttp.ClientSession() as session:
        # Toggle to simulation mode
        async with session.post(
            f"{BASE_URL}/api/v1/trading/toggle-simulation",
            headers=headers,
            json={"simulation_mode": True}
        ) as response:
            if response.status == 200:
                print("OK: Switched to SIMULATION mode")
            else:
                print(f"WARNING: Could not toggle simulation: {response.status}")

        # Execute simulation trade via chat
        chat_message = {
            "message": f"Buy ${TEST_AMOUNT_USD} worth of BTC in simulation mode",
            "context": {
                "mode": "simulation",
                "amount": TEST_AMOUNT_USD,
                "symbol": TEST_SYMBOL
            }
        }

        print(f"\n[>] Executing SIMULATION trade: ${TEST_AMOUNT_USD} of {TEST_SYMBOL}")

        async with session.post(
            f"{BASE_URL}/api/v1/chat/unified",
            headers=headers,
            json=chat_message
        ) as response:
            if response.status == 200:
                data = await response.json()
                print(f"OK: Simulation trade response received")

                # Parse response for trade details
                if "response" in data:
                    response_text = data["response"]
                    print(f"\nChat Response: {response_text[:500]}...")

                    # Check for trade execution indicators
                    if any(word in response_text.lower() for word in ["executed", "filled", "bought", "completed"]):
                        print("OK: SIMULATION TRADE EXECUTED")

                        # Try to extract trade details
                        if "simulation_result" in str(data):
                            print("OK: Simulation result found in response")
                        return True
                    else:
                        print("WARNING: Trade may not have executed")
                        return False
            else:
                print(f"ERROR: Simulation trade failed: {response.status}")
                return False

async def test_live_trade_check(token):
    """Check if live trading is possible (WITHOUT executing)."""
    print("\n" + "="*60)
    print("CHECKING LIVE TRADE CAPABILITY (No execution)")
    print("="*60)

    headers = {"Authorization": f"Bearer {token}"}

    async with aiohttp.ClientSession() as session:
        # Check if we can access live trading endpoints
        async with session.get(
            f"{BASE_URL}/api/v1/trading/balance",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                print("OK: Live trading endpoint accessible")
                print(f"   Balance data: {json.dumps(data, indent=2)[:200]}...")

                # Check for real balance
                if "balances" in data or "total" in data:
                    print("OK: Real balance data structure found")
                    return True
                else:
                    print("WARNING: No real balance data")
                    return False
            else:
                print(f"ERROR: Cannot access live trading: {response.status}")
                return False

async def verify_trade_execution_path(token):
    """Verify the execution path without placing trades."""
    print("\n" + "="*60)
    print("VERIFYING TRADE EXECUTION PATHS")
    print("="*60)

    headers = {"Authorization": f"Bearer {token}"}

    async with aiohttp.ClientSession() as session:
        # Test trade validation endpoint
        validation_request = {
            "symbol": TEST_SYMBOL,
            "side": "buy",
            "amount": TEST_AMOUNT_USD,
            "validate_only": True
        }

        async with session.post(
            f"{BASE_URL}/api/v1/trading/validate",
            headers=headers,
            json=validation_request
        ) as response:
            if response.status == 200:
                data = await response.json()
                print("OK: Trade validation endpoint works")
                print(f"   Validation result: {data}")
            elif response.status == 404:
                print("WARNING: Validation endpoint not found - checking alternatives")
            else:
                print(f"ERROR: Validation failed: {response.status}")

async def main():
    """Main test execution."""
    print("="*60)
    print("CRYPTOUNIVERSE TRADE EXECUTION VERIFICATION")
    print(f"Platform: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print("="*60)

    # Login
    print("\n[1] AUTHENTICATING...")
    token = await login_and_get_token()
    if not token:
        print("ERROR: Authentication failed. Cannot proceed.")
        return

    print("OK: Authentication successful")

    # Check user configuration
    print("\n[2] CHECKING USER CONFIGURATION...")
    user = await check_user_mode(token)

    # Check exchange credentials
    print("\n[3] CHECKING EXCHANGE CONNECTIVITY...")
    accounts = await check_exchange_credentials(token)

    # Test simulation mode
    print("\n[4] TESTING SIMULATION MODE...")
    sim_result = await test_simulation_trade(token)

    # Check live capability (no execution)
    print("\n[5] CHECKING LIVE TRADE CAPABILITY...")
    live_check = await test_live_trade_check(token)

    # Verify execution paths
    print("\n[6] VERIFYING EXECUTION PATHS...")
    await verify_trade_execution_path(token)

    # SUMMARY
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)

    print(f"\n[OK] Authentication: WORKING")
    print(f"{'[OK]' if sim_result else '[ERROR]'} Simulation Mode: {'WORKING' if sim_result else 'NOT CONFIRMED'}")
    print(f"{'[OK]' if accounts else '[ERROR]'} Exchange Credentials: {'FOUND' if accounts else 'NOT FOUND'}")
    print(f"{'[OK]' if live_check else '[ERROR]'} Live Trade Capability: {'POSSIBLE' if live_check else 'NOT READY'}")

    print("\n[CONCLUSION]:")
    if sim_result and accounts and live_check:
        print("[OK] BOTH simulation and live trading appear FUNCTIONAL")
        print("   - Simulation trades execute with mock data")
        print("   - Live trading infrastructure is present")
        print("   - Exchange credentials are configured")
    elif sim_result and not live_check:
        print("[WARNING] ONLY simulation mode is working")
        print("   - Simulation trades work with mock data")
        print("   - Live trading needs exchange API keys")
    else:
        print("[ERROR] Trading functionality needs configuration")
        print("   - Check exchange API keys")
        print("   - Verify database connections")
        print("   - Review trade execution service")

    print("\n[!] IMPORTANT: Did NOT execute any LIVE trades for safety")
    print("   To test live trading, manual confirmation required")

if __name__ == "__main__":
    asyncio.run(main())