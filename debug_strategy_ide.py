#!/usr/bin/env python3
"""
Debug Strategy IDE Frontend Authentication Issue
"""

import requests
import json
import os
from pathlib import Path

def test_strategy_ide_auth():
    """Test Strategy IDE endpoints with authentication"""

    base_url = "https://cryptouniverse.onrender.com/api/v1"

    print("🔍 Testing Strategy IDE Authentication Flow...")
    print("=" * 60)

    # Test 1: Check if endpoints exist
    print("\n1. Testing endpoint availability:")

    endpoints = [
        "/strategies/templates",
        "/strategies/validate",
        "/strategies/backtest"
    ]

    for endpoint in endpoints:
        try:
            response = requests.post(f"{base_url}{endpoint}",
                                   json={"code": "def test(): pass"},
                                   timeout=10)

            if response.status_code == 401:
                print(f"✅ {endpoint}: EXISTS (requires auth)")
            elif response.status_code == 404:
                print(f"❌ {endpoint}: NOT FOUND")
            else:
                print(f"⚠️  {endpoint}: Status {response.status_code}")

        except Exception as e:
            print(f"❌ {endpoint}: ERROR - {str(e)}")

    # Test 2: Try with a test authentication
    print("\n2. Testing with guest authentication:")

    # Try to create a test account or login
    login_data = {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }

    try:
        # Try login first
        login_response = requests.post(f"{base_url}/auth/login",
                                     json=login_data,
                                     timeout=10)

        if login_response.status_code == 200:
            auth_data = login_response.json()
            token = auth_data.get("access_token")

            print(f"✅ Login successful, token received")

            # Test Strategy IDE endpoints with auth
            headers = {"Authorization": f"Bearer {token}"}

            print("\n3. Testing Strategy IDE with authentication:")

            # Test validation endpoint
            validate_response = requests.post(f"{base_url}/strategies/validate",
                                            json={"code": "def strategy_logic(): return {'signals': []}"},
                                            headers=headers,
                                            timeout=30)

            print(f"Validate endpoint: Status {validate_response.status_code}")
            if validate_response.status_code == 200:
                print("✅ Validation working!")
                print(f"Response: {validate_response.json()}")
            else:
                print(f"❌ Validation failed: {validate_response.text}")

            # Test backtest endpoint
            backtest_response = requests.post(f"{base_url}/strategies/backtest",
                                            json={
                                                "code": "def strategy_logic(): return {'signals': []}",
                                                "symbol": "BTC/USDT",
                                                "start_date": "2024-01-01",
                                                "end_date": "2024-01-30",
                                                "initial_capital": 10000,
                                                "parameters": {}
                                            },
                                            headers=headers,
                                            timeout=60)

            print(f"Backtest endpoint: Status {backtest_response.status_code}")
            if backtest_response.status_code == 200:
                print("✅ Backtest working!")
                print(f"Response: {backtest_response.json()}")
            else:
                print(f"❌ Backtest failed: {backtest_response.text}")

        elif login_response.status_code == 422:
            print("⚠️  Login validation error - trying registration")

            # Try registration
            register_response = requests.post(f"{base_url}/auth/register",
                                            json={
                                                "email": "test@example.com",
                                                "password": "TestPassword123!",
                                                "username": "testuser"
                                            },
                                            timeout=10)

            print(f"Registration status: {register_response.status_code}")
            if register_response.status_code == 201:
                print("✅ Registration successful")
                # Try login again
                login_response = requests.post(f"{base_url}/auth/login",
                                             json=login_data,
                                             timeout=10)
                print(f"Login after registration: {login_response.status_code}")

        else:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")

    except Exception as e:
        print(f"❌ Authentication test error: {str(e)}")

    print("\n" + "=" * 60)
    print("🎯 Strategy IDE Debug Complete!")
    print("=" * 60)

def test_frontend_config():
    """Check frontend API configuration"""
    print("\n4. Analyzing frontend configuration:")

    # Check if the API base URL is correct in the deployed frontend
    frontend_url = "https://cryptouniverse-frontend.onrender.com"

    try:
        # This would ideally check the frontend's API configuration
        # For now, let's verify the frontend can reach the backend
        response = requests.get(f"{frontend_url}/", timeout=10)
        print(f"✅ Frontend accessible: Status {response.status_code}")

        # Check if the frontend is making requests to the correct backend
        print("💡 Frontend should be calling: https://cryptouniverse.onrender.com/api/v1/")
        print("📋 Check browser dev tools Network tab when clicking Console button")

    except Exception as e:
        print(f"❌ Frontend connection error: {str(e)}")

if __name__ == "__main__":
    test_strategy_ide_auth()
    test_frontend_config()