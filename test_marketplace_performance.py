import requests
import time
import json

BASE_URL = "https://cryptouniverse.onrender.com"
EMAIL = "admin@cryptouniverse.com"
PASSWORD = "AdminPass123!"

def login():
    """Login and get auth token"""
    url = f"{BASE_URL}/api/v1/auth/login"
    payload = {"email": EMAIL, "password": PASSWORD}
    
    print(f"\n[LOGIN] Logging in as {EMAIL}...")
    start = time.time()
    response = requests.post(url, json=payload, timeout=30)
    elapsed = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user_id = data.get("user_id")
        print(f"[OK] Login successful ({elapsed:.2f}s)")
        print(f"   User ID: {user_id}")
        return token
    else:
        print(f"[ERROR] Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def test_endpoint(name, url, headers, timeout=120):
    """Test an endpoint and measure performance"""
    print(f"\n{'='*60}")
    print(f"[TEST] Testing: {name}")
    print(f"   URL: {url}")
    print(f"{'='*60}")
    
    start = time.time()
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        elapsed = time.time() - start
        
        print(f"\n[TIME] Response Time: {elapsed:.2f} seconds")
        print(f"[STATUS] Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Extract key metrics
                if isinstance(data, dict):
                    if "strategies" in data:
                        strategies = data["strategies"]
                        print(f"[DATA] Strategies Count: {len(strategies)}")
                        if strategies:
                            print(f"   First strategy: {strategies[0].get('name', 'N/A')}")
                    elif isinstance(data, list):
                        print(f"[DATA] Items Count: {len(data)}")
                        if data:
                            print(f"   First item keys: {list(data[0].keys())[:5]}")
                    
                    # Show other keys
                    other_keys = [k for k in data.keys() if k != "strategies"]
                    if other_keys:
                        print(f"[FIELDS] Other fields: {', '.join(other_keys)}")
                
                print(f"[OK] Success!")
                return True, elapsed
            except json.JSONDecodeError:
                print(f"[WARN] Response is not JSON")
                print(f"   First 500 chars: {response.text[:500]}")
                return False, elapsed
        else:
            print(f"[ERROR] Error Response:")
            print(f"   {response.text[:500]}")
            return False, elapsed
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        print(f"[TIME] Response Time: {elapsed:.2f} seconds (TIMEOUT)")
        print(f"[ERROR] Request timed out after {timeout}s")
        return False, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"[TIME] Response Time: {elapsed:.2f} seconds")
        print(f"[ERROR] Error: {str(e)}")
        return False, elapsed

def main():
    print("="*60)
    print("CRYPTOUNIVERSE MARKETPLACE PERFORMANCE TEST")
    print("="*60)
    
    # Login
    token = login()
    if not token:
        print("\n[ERROR] Cannot proceed without authentication")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test endpoints
    results = []
    
    # 1. Strategy Marketplace
    marketplace_url = f"{BASE_URL}/api/v1/strategies/marketplace"
    success, elapsed = test_endpoint(
        "Strategy Marketplace",
        marketplace_url,
        headers,
        timeout=120
    )
    results.append(("Strategy Marketplace", success, elapsed))
    
    # 2. User Strategies List
    strategies_url = f"{BASE_URL}/api/v1/strategies/list"
    success, elapsed = test_endpoint(
        "User Strategies List",
        strategies_url,
        headers,
        timeout=60
    )
    results.append(("User Strategies List", success, elapsed))
    
    # Summary
    print(f"\n{'='*60}")
    print("[SUMMARY] PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    for name, success, elapsed in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {name}: {elapsed:.2f}s")
    
    # Identify slow endpoints
    slow_threshold = 5.0
    slow_endpoints = [r for r in results if r[2] > slow_threshold]
    if slow_endpoints:
        print(f"\n[WARN] SLOW ENDPOINTS (> {slow_threshold}s):")
        for name, success, elapsed in slow_endpoints:
            print(f"   - {name}: {elapsed:.2f}s")

if __name__ == "__main__":
    main()

