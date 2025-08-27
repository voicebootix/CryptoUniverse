#!/usr/bin/env python3
"""
Test what endpoints are available on the backend
"""

import requests

def test_backend_endpoints():
    """Test various endpoints to see what's available."""
    
    backend_url = "https://cryptouniverse.onrender.com"
    
    endpoints_to_test = [
        "/",
        "/api",
        "/api/v1",
        "/api/v1/status",
        "/api/v1/auth/login",
        "/api/v1/auth/register", 
        "/auth/login",
        "/auth/register",
        "/login",
        "/register",
        "/status",
        "/health",
        "/docs",
        "/api/docs"
    ]
    
    print("🔍 Testing Backend Endpoints")
    print("=" * 40)
    print(f"Backend: {backend_url}")
    print()
    
    working_endpoints = []
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{backend_url}{endpoint}", timeout=10)
            status = response.status_code
            
            if status == 200:
                print(f"✅ {endpoint} - {status} - {response.text[:100]}")
                working_endpoints.append(endpoint)
            elif status == 404:
                print(f"❌ {endpoint} - {status} (Not Found)")
            elif status == 405:
                print(f"⚠️  {endpoint} - {status} (Method Not Allowed - might need POST)")
                working_endpoints.append(f"{endpoint} (POST only)")
            else:
                print(f"⚠️  {endpoint} - {status} - {response.text[:50]}")
                
        except Exception as e:
            print(f"❌ {endpoint} - Error: {str(e)[:50]}")
    
    print("\n" + "=" * 40)
    print("📋 WORKING ENDPOINTS:")
    if working_endpoints:
        for endpoint in working_endpoints:
            print(f"   ✅ {endpoint}")
    else:
        print("   ❌ No working endpoints found")
    
    return working_endpoints

if __name__ == "__main__":
    working = test_backend_endpoints()
    
    if not working:
        print("\n🚨 DIAGNOSIS: Backend is running but has no API routes!")
        print("💡 SOLUTION: The backend needs to be redeployed with full API")
        print("🔧 ACTION: Check Render dashboard and redeploy backend service")
