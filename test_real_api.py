#!/usr/bin/env python3
"""
Test real API endpoints with authentication
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_login():
    """Test login and get token"""
    try:
        # Test login endpoint
        login_data = {
            "email": "admin@cryptouniverse.com",
            "password": "AdminPass123!"
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=login_data,
            timeout=10
        )

        print(f"Login Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"✅ Login successful! Token: {token[:50]}...")
            return token
        else:
            print(f"❌ Login failed: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_endpoints(token):
    """Test various endpoints with token"""
    if not token:
        print("❌ No token available")
        return

    headers = {"Authorization": f"Bearer {token}"}

    endpoints = [
        "/api/v1/trading/portfolio",
        "/api/v1/credits/balance",
        "/api/v1/exchanges/list",
        "/api/v1/market/data",
        "/api/v1/trading/status"
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                headers=headers,
                timeout=10
            )

            print(f"\n{endpoint}: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}")

                # Show specific data for portfolio
                if "portfolio" in endpoint and isinstance(data, dict):
                    total_value = data.get("total_value", 0)
                    positions = data.get("positions", [])
                    print(f"  📊 Total Value: ${total_value}")
                    print(f"  📊 Positions: {len(positions)}")

                # Show specific data for credits
                elif "credits" in endpoint and isinstance(data, dict):
                    balance = data.get("balance", 0)
                    print(f"  💰 Credits Balance: {balance}")

            else:
                print(f"  ❌ Error: {response.text[:100]}...")

        except Exception as e:
            print(f"  ❌ Exception: {e}")

def test_market_data():
    """Test public market data endpoints"""
    print("\n🔍 Testing Public Market Data:")

    # These might not need authentication
    public_endpoints = [
        "/",
        "/api/v1/market/symbols",
        "/health"
    ]

    for endpoint in public_endpoints:
        try:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                timeout=5
            )

            print(f"{endpoint}: {response.status_code}")
            if response.status_code == 200 and endpoint != "/":
                data = response.json()
                print(f"  ✅ Keys: {list(data.keys()) if isinstance(data, dict) else str(type(data))}")

        except Exception as e:
            print(f"  ❌ {endpoint}: {e}")

if __name__ == "__main__":
    print("🚀 Testing CryptoUniverse Real API...")

    # Test public endpoints first
    test_market_data()

    # Test authentication
    print("\n🔐 Testing Authentication...")
    token = test_login()

    # Test protected endpoints
    print("\n📊 Testing Protected Endpoints...")
    test_endpoints(token)

    print("\n✅ API Test Complete!")