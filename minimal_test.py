#!/usr/bin/env python3
import requests

def minimal_test():
    print("MINIMAL CONNECTIVITY TEST")
    print("=" * 25)

    # Test 1: Health check
    try:
        print("1. Health check...")
        response = requests.get("https://cryptouniverse.onrender.com/health", timeout=30)
        print(f"   Health: {response.status_code}")
    except Exception as e:
        print(f"   Health error: {e}")

    # Test 2: Login only
    try:
        print("2. Login test...")
        login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
        payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
        response = requests.post(login_url, json=payload, timeout=30)
        print(f"   Login: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   Token: {data.get('access_token')[:20]}...")
            return data.get('access_token')
    except Exception as e:
        print(f"   Login error: {e}")

    return None

if __name__ == "__main__":
    token = minimal_test()
    if token:
        print("\n[SUCCESS] Basic connectivity works")
    else:
        print("\n[FAILED] Connection issues persist")