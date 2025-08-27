#!/usr/bin/env python3
"""
Create Admin User via API for CryptoUniverse
"""

import requests
import json

def create_admin_via_api():
    """Create admin user by calling the backend API directly."""
    
    backend_url = "https://cryptouniverse.onrender.com"
    
    print("🚀 Creating Admin User via API")
    print("=" * 40)
    print(f"Backend: {backend_url}")
    
    # Test if backend is responding
    try:
        response = requests.get(f"{backend_url}/", timeout=10)
        print(f"✅ Backend Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Backend not responding: {e}")
        return
    
    # Admin user data
    admin_data = {
        "email": "admin@cryptouniverse.com",
        "password": "AdminPass123!",
        "full_name": "System Administrator",
        "role": "admin"
    }
    
    print(f"\n🔐 Creating admin user: {admin_data['email']}")
    
    # Try to register admin user
    try:
        response = requests.post(
            f"{backend_url}/api/v1/auth/register",
            json=admin_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📡 Registration Response: {response.status_code}")
        
        if response.status_code == 200 or response.status_code == 201:
            print("✅ Admin user created successfully!")
            result = response.json()
            print(f"   User ID: {result.get('id', 'N/A')}")
            print(f"   Email: {result.get('email', 'N/A')}")
            print(f"   Role: {result.get('role', 'N/A')}")
            print(f"   Status: {result.get('status', 'N/A')}")
            
        elif response.status_code == 409:
            print("⚠️ User already exists - trying to login...")
            
            # Try to login with existing user
            login_data = {
                "email": admin_data["email"],
                "password": admin_data["password"]
            }
            
            login_response = requests.post(
                f"{backend_url}/api/v1/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"🔑 Login Response: {login_response.status_code}")
            
            if login_response.status_code == 200:
                print("✅ Login successful! User already exists and is working.")
                result = login_response.json()
                print(f"   Access Token: {result.get('access_token', 'N/A')[:50]}...")
                print(f"   Role: {result.get('role', 'N/A')}")
            else:
                print(f"❌ Login failed: {login_response.text}")
                
        else:
            print(f"❌ Registration failed: {response.text}")
            
            # Try alternative admin credentials
            print("\n🔄 Trying alternative credentials...")
            
            alt_admin_data = {
                "email": "admin@example.com",
                "password": "SecurePassword123!",
                "full_name": "System Administrator",
                "role": "admin"
            }
            
            alt_response = requests.post(
                f"{backend_url}/api/v1/auth/register",
                json=alt_admin_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"📡 Alternative Registration: {alt_response.status_code}")
            
            if alt_response.status_code == 200 or alt_response.status_code == 201:
                print("✅ Alternative admin user created!")
                print(f"   Email: {alt_admin_data['email']}")
                print(f"   Password: {alt_admin_data['password']}")
            else:
                print(f"❌ Alternative registration failed: {alt_response.text}")
    
    except Exception as e:
        print(f"❌ API request failed: {e}")

def test_login():
    """Test login with created admin user."""
    
    backend_url = "https://cryptouniverse.onrender.com"
    
    credentials_to_try = [
        {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"},
        {"email": "admin@example.com", "password": "SecurePassword123!"},
        {"email": "admin@cryptouniverse.com", "password": "SecurePassword123!"}
    ]
    
    print("\n🔑 Testing Login Credentials")
    print("=" * 30)
    
    for i, creds in enumerate(credentials_to_try, 1):
        print(f"\n{i}. Testing: {creds['email']}")
        
        try:
            response = requests.post(
                f"{backend_url}/api/v1/auth/login",
                json=creds,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS! Use these credentials:")
                print(f"      Email: {creds['email']}")
                print(f"      Password: {creds['password']}")
                result = response.json()
                print(f"      Role: {result.get('role', 'N/A')}")
                return creds
            else:
                print(f"   ❌ Failed: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n❌ No working credentials found")
    return None

if __name__ == "__main__":
    create_admin_via_api()
    working_creds = test_login()
    
    print("\n" + "=" * 50)
    print("🎉 ADMIN USER SETUP COMPLETE!")
    print("=" * 50)
    
    if working_creds:
        print(f"✅ Login at: https://cryptouniverse-frontend.onrender.com")
        print(f"📧 Email: {working_creds['email']}")
        print(f"🔒 Password: {working_creds['password']}")
    else:
        print("❌ Please check the backend logs for issues")
        print("💡 Try registering manually on the frontend")
