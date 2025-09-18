#!/usr/bin/env python3
"""
Enterprise Trade Execution Verification Script

Secure verification script for testing trade execution in live environments.
All credentials loaded from environment variables with proper safety gates.
"""

import asyncio
import os
import sys
import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any
import time

# Load configuration from environment with validation
BASE_URL = os.getenv('CRYPTOUNIVERSE_BASE_URL')
ADMIN_EMAIL = os.getenv('CRYPTOUNIVERSE_ADMIN_EMAIL')
ADMIN_PASSWORD = os.getenv('CRYPTOUNIVERSE_ADMIN_PASSWORD')

# Safety gate - must be explicitly enabled
RUN_LIVE_VERIFICATION = os.getenv('RUN_LIVE_VERIFICATION', '').lower() == 'true'

# Test configuration
MAX_TEST_AMOUNT = float(os.getenv('MAX_TEST_AMOUNT', '10.0'))  # Maximum test trade amount
SIMULATION_MODE = os.getenv('FORCE_SIMULATION_MODE', 'true').lower() == 'true'


def validate_environment():
    """Validate all required environment variables are present."""
    missing_vars = []

    if not BASE_URL:
        missing_vars.append('CRYPTOUNIVERSE_BASE_URL')
    if not ADMIN_EMAIL:
        missing_vars.append('CRYPTOUNIVERSE_ADMIN_EMAIL')
    if not ADMIN_PASSWORD:
        missing_vars.append('CRYPTOUNIVERSE_ADMIN_PASSWORD')

    if missing_vars:
        print(f"❌ ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("\n📋 Required environment variables:")
        print("   CRYPTOUNIVERSE_BASE_URL - API base URL (e.g., https://api.cryptouniverse.com/api/v1)")
        print("   CRYPTOUNIVERSE_ADMIN_EMAIL - Admin email for authentication")
        print("   CRYPTOUNIVERSE_ADMIN_PASSWORD - Admin password")
        print("   RUN_LIVE_VERIFICATION - Must be 'true' to run live tests")
        print("   FORCE_SIMULATION_MODE - Set to 'false' only for live trading tests")
        print("\n⚠️  NEVER commit credentials to the repository!")
        return False

    # Validate BASE_URL format
    if not (BASE_URL.startswith('http://') or BASE_URL.startswith('https://')):
        print("❌ ERROR: BASE_URL must start with http:// or https://")
        return False

    return True


async def login_and_get_token() -> Optional[str]:
    """Authenticate and get access token."""
    try:
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }

        print(f"🔐 Authenticating with {BASE_URL}/auth/login")
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json=login_data,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            user_info = data.get('user', {})

            print(f"✅ Authentication successful")
            print(f"   User: {user_info.get('email', 'N/A')}")
            print(f"   Role: {user_info.get('role', 'N/A')}")

            return token
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {BASE_URL}")
        print("   Check if the server is running and URL is correct")
        return None
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None


async def verify_trade_execution_service(token: str) -> Dict[str, Any]:
    """Verify trade execution service functionality."""
    headers = {"Authorization": f"Bearer {token}"}
    results = {}

    print("\n[2] VERIFYING TRADE EXECUTION SERVICE...")

    # Test 1: Service Health Check
    print("\n📊 Testing service health...")
    try:
        response = requests.get(f"{BASE_URL}/health", headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Service health check passed")
            results['health_check'] = True
        else:
            print(f"⚠️  Health check returned {response.status_code}")
            results['health_check'] = False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        results['health_check'] = False

    # Test 2: User Portfolio Access
    print("\n💼 Testing portfolio access...")
    try:
        response = requests.get(f"{BASE_URL}/strategies/my-portfolio", headers=headers, timeout=15)
        if response.status_code == 200:
            portfolio = response.json()
            print(f"✅ Portfolio access successful")
            print(f"   Active strategies: {len(portfolio.get('active_strategies', []))}")
            results['portfolio_access'] = True
        else:
            print(f"❌ Portfolio access failed: {response.status_code}")
            results['portfolio_access'] = False
    except Exception as e:
        print(f"❌ Portfolio access error: {e}")
        results['portfolio_access'] = False

    # Test 3: Market Data Access
    print("\n📈 Testing market data access...")
    try:
        response = requests.get(f"{BASE_URL}/market/status", headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Market data access successful")
            results['market_data'] = True
        else:
            print(f"⚠️  Market data returned {response.status_code}")
            results['market_data'] = False
    except Exception as e:
        print(f"❌ Market data error: {e}")
        results['market_data'] = False

    # Test 4: Simulation Trade (Safe Test)
    print(f"\n🧪 Testing simulation trade execution...")
    try:
        test_trade = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 0.001,  # Small test amount
            "order_type": "market",
            "simulation_mode": True  # Always use simulation for verification
        }

        response = requests.post(
            f"{BASE_URL}/trades/execute",
            json=test_trade,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            trade_result = response.json()
            print("✅ Simulation trade execution successful")
            print(f"   Order ID: {trade_result.get('order_id', 'N/A')}")
            print(f"   Status: {trade_result.get('status', 'N/A')}")
            results['simulation_trade'] = True
        else:
            print(f"❌ Simulation trade failed: {response.status_code}")
            print(f"   Response: {response.text}")
            results['simulation_trade'] = False

    except Exception as e:
        print(f"❌ Simulation trade error: {e}")
        results['simulation_trade'] = False

    return results


async def verify_risk_management(token: str) -> Dict[str, Any]:
    """Verify risk management systems."""
    headers = {"Authorization": f"Bearer {token}"}
    results = {}

    print("\n[3] VERIFYING RISK MANAGEMENT...")

    # Test position size limits
    print("\n🛡️  Testing position size limits...")
    try:
        large_trade = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 100,  # Intentionally large amount
            "order_type": "market",
            "simulation_mode": True
        }

        response = requests.post(
            f"{BASE_URL}/trades/validate",
            json=large_trade,
            headers=headers,
            timeout=15
        )

        if response.status_code == 400:
            print("✅ Position size limits working correctly")
            results['position_limits'] = True
        elif response.status_code == 200:
            validation = response.json()
            if not validation.get('valid', True):
                print("✅ Risk validation rejected large trade")
                results['position_limits'] = True
            else:
                print("⚠️  Large trade was approved - check risk settings")
                results['position_limits'] = False
        else:
            print(f"❌ Risk validation failed: {response.status_code}")
            results['position_limits'] = False

    except Exception as e:
        print(f"❌ Position limit test error: {e}")
        results['position_limits'] = False

    return results


async def main():
    """Main verification execution with comprehensive safety checks."""
    print("="*80)
    print("🚨 CRYPTOUNIVERSE ENTERPRISE TRADE EXECUTION VERIFICATION")
    print(f"📍 Environment: {BASE_URL}")
    print(f"🕐 Time: {datetime.now().isoformat()}")
    print("="*80)

    # Safety gate #1: Explicit execution approval
    if not RUN_LIVE_VERIFICATION:
        print("⚠️  VERIFICATION DISABLED")
        print("   Set RUN_LIVE_VERIFICATION=true to enable verification")
        print("   This safety measure prevents accidental execution")
        return

    # Safety gate #2: Environment validation
    print("\n[0] VALIDATING ENVIRONMENT...")
    if not validate_environment():
        print("❌ Environment validation failed. Cannot proceed.")
        return

    # Safety gate #3: Credential validation
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("❌ ERROR: Missing credentials in environment variables")
        print("   Set CRYPTOUNIVERSE_ADMIN_EMAIL and CRYPTOUNIVERSE_ADMIN_PASSWORD")
        return

    # Safety gate #4: Confirm simulation mode
    if not SIMULATION_MODE:
        print("⚠️  WARNING: Live trading mode enabled!")
        print("   Set FORCE_SIMULATION_MODE=true for safer verification")

        # Additional confirmation for live mode
        confirmation = input("Type 'I_UNDERSTAND_LIVE_TRADING' to continue: ")
        if confirmation != "I_UNDERSTAND_LIVE_TRADING":
            print("❌ Live trading not confirmed. Exiting for safety.")
            return

    print("✅ All safety checks passed")

    # Authentication
    print("\n[1] AUTHENTICATING...")
    token = await login_and_get_token()
    if not token:
        print("❌ Authentication failed. Cannot proceed with verification.")
        return

    # Core verification tests
    trade_results = await verify_trade_execution_service(token)
    risk_results = await verify_risk_management(token)

    # Results summary
    print("\n" + "="*80)
    print("📊 VERIFICATION SUMMARY")
    print("="*80)

    all_tests = {**trade_results, **risk_results}
    passed = sum(1 for result in all_tests.values() if result)
    total = len(all_tests)

    print(f"📈 Overall Score: {passed}/{total} tests passed")

    for test_name, result in all_tests.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")

    if passed == total:
        print("\n🎉 ALL VERIFICATION TESTS PASSED!")
        print("   Trade execution system is functioning correctly")
    else:
        print(f"\n⚠️  {total - passed} TESTS FAILED")
        print("   Review failed tests and address issues before production use")

    # Security reminder
    print("\n🔒 SECURITY REMINDER:")
    print("   • All credentials loaded from environment variables")
    print("   • No secrets stored in code or logs")
    print("   • Verification performed in safe simulation mode")
    print("   • Multiple safety gates prevent accidental execution")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Verification interrupted by user")
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        sys.exit(1)