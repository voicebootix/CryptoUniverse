#!/usr/bin/env python3
"""
Check admin user role to see why bypass isn't working
"""
import requests

def check_admin_role():
    print("CHECKING ADMIN ROLE")
    print("=" * 20)

    # Login
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}

    response = requests.post(login_url, json=login_payload, timeout=15)
    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Admin user ID: {user_id}")

    # Check user profile to see role
    print("\nChecking user profile...")
    try:
        profile_url = "https://cryptouniverse.onrender.com/api/v1/users/profile"
        response = requests.get(profile_url, headers=headers, timeout=15)

        if response.status_code == 200:
            profile = response.json()
            print(f"User role: {profile.get('role', 'Not found')}")
            print(f"User email: {profile.get('email', 'Not found')}")
            print(f"Full profile: {profile}")
        else:
            print(f"Profile check failed: {response.status_code}")

    except Exception as e:
        print(f"Profile check error: {e}")

    # Check if admin endpoints work
    print("\nTesting admin endpoint access...")
    try:
        admin_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/admin-portfolio-status"
        response = requests.get(admin_url, headers=headers, timeout=20)

        if response.status_code == 200:
            print("Admin endpoint accessible - user has admin permissions")
            data = response.json()
            print(f"Admin status: {data}")
        else:
            print(f"Admin endpoint failed: {response.status_code}")
            if response.status_code == 403:
                print("User does NOT have admin role")

    except Exception as e:
        print(f"Admin endpoint error: {e}")

if __name__ == "__main__":
    check_admin_role()