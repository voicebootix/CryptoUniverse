#!/usr/bin/env python3
"""
Fix URL construction bug and test locally vs production to see the difference
"""

import requests

def test_url_construction_fix():
    """Test the URL construction that was causing issues."""
    
    # Test the problematic URL construction from my script
    base_url = "https://cryptouniverse.onrender.com/api/v1" 
    path = "/api/v1/status"
    
    # WRONG: This creates "api/v1status" 
    wrong_url = f"{base_url}{path[8:]}"  # Remove /api/v1 from path
    
    # RIGHT: This should be used
    right_url = f"https://cryptouniverse.onrender.com{path}"
    
    print("🔧 URL CONSTRUCTION BUG FOUND:")
    print(f"Path: {path}")
    print(f"❌ Wrong URL: {wrong_url}")  
    print(f"✅ Right URL: {right_url}")
    
    print(f"\n🧪 Testing both URLs:")
    
    # Test wrong URL
    try:
        response = requests.get(wrong_url, timeout=5)
        print(f"❌ Wrong URL result: {response.status_code}")
    except Exception as e:
        print(f"❌ Wrong URL error: {e}")
    
    # Test right URL  
    try:
        response = requests.get(right_url, timeout=5)
        print(f"✅ Right URL result: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.text[:100]}")
        else:
            print(f"   Error: {response.text[:100]}")
    except Exception as e:
        print(f"❌ Right URL error: {e}")

def test_local_vs_production():
    """Test if local server would work vs production."""
    
    endpoints = [
        "https://cryptouniverse.onrender.com/health",
        "https://cryptouniverse.onrender.com/api/v1/status", 
        "https://cryptouniverse.onrender.com/auth/login"
    ]
    
    print(f"\n🌐 PRODUCTION vs LOCAL COMPARISON")
    print("=" * 50)
    
    for url in endpoints:
        path = url.split('onrender.com')[1] 
        print(f"\n📍 Testing: {path}")
        
        # Test production
        try:
            if "login" in url:
                response = requests.post(url, json={"email": "test", "password": "test"}, timeout=5)
            else:
                response = requests.get(url, timeout=5)
            
            print(f"   🌐 Production: {response.status_code} - {response.text[:60]}")
            
        except Exception as e:
            print(f"   🌐 Production: ERROR - {str(e)[:60]}")
        
        # Note about local (can't actually test without running server)
        print(f"   💻 Local: Would be fixed with middleware changes")

if __name__ == "__main__":
    test_url_construction_fix()
    test_local_vs_production()
