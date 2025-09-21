#!/usr/bin/env python3
"""
Provision Admin User Strategies - Simple Version

Manually provision strategies for the admin user.
"""

import os
import requests
import json

# Configuration from environment
BASE_URL = os.getenv("BASE_URL", "https://cryptouniverse.onrender.com/api/v1")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not ADMIN_EMAIL or not ADMIN_PASSWORD:
    raise ValueError("ADMIN_EMAIL and ADMIN_PASSWORD environment variables are required")

def provision_strategies():
    """Provision strategies for admin user."""

    print("PROVISIONING ADMIN STRATEGIES")
    print("=" * 60)

    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}

    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        print(response.text)
        return False

    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("Authenticated successfully")

    # Test current portfolio status first
    print("\nChecking current portfolio status...")
    portfolio_response = session.get(f"{BASE_URL}/strategies/my-portfolio")
    print(f"Portfolio status: {portfolio_response.status_code}")
    if portfolio_response.status_code == 200:
        portfolio_data = portfolio_response.json()
        print(f"Current strategies: {len(portfolio_data.get('active_strategies', []))}")

    # Try the admin grant endpoint
    print("\nTrying admin grant endpoint...")
    grant_payload = {
        "strategy_type": "all",
        "grant_reason": "admin_testing"
    }

    grant_response = session.post(f"{BASE_URL}/admin-strategy-access/grant-full-access", json=grant_payload)
    print(f"Grant response: {grant_response.status_code}")

    if grant_response.status_code == 200:
        grant_data = grant_response.json()
        print(f"Success: {grant_data.get('success')}")
        print(f"Strategies granted: {grant_data.get('total_strategies')}")
    else:
        print(f"Grant failed: {grant_response.text}")

    # Check portfolio again
    print("\nChecking portfolio after grant...")
    portfolio_response2 = session.get(f"{BASE_URL}/strategies/my-portfolio")
    print(f"Portfolio status: {portfolio_response2.status_code}")
    if portfolio_response2.status_code == 200:
        portfolio_data2 = portfolio_response2.json()
        print(f"Current strategies after grant: {len(portfolio_data2.get('active_strategies', []))}")
        if portfolio_data2.get('active_strategies'):
            print("First few strategies:")
            for i, strategy in enumerate(portfolio_data2['active_strategies'][:3]):
                print(f"  {i+1}. {strategy.get('name', 'Unnamed')}")

    return True

if __name__ == "__main__":
    provision_strategies()