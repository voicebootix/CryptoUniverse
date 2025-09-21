import requests

# Try different possible backend URLs
possible_urls = [
    "https://cryptouniverse-backend.onrender.com",
    "https://cryptouniverse.onrender.com",
    "https://cryptouniverse-api.onrender.com",
    "https://cryptouniverse-backend.onrender.com/api/v1"
]

print("Checking backend URLs...")

for url in possible_urls:
    try:
        # Try a simple health check or docs endpoint
        for endpoint in ["/", "/docs", "/health", "/api/v1/health"]:
            full_url = url + endpoint
            print(f"\nTrying: {full_url}")

            response = requests.get(full_url, timeout=5)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                print(f"SUCCESS! Backend found at: {url}")
                print(f"Response preview: {response.text[:200]}")
                break
    except Exception as e:
        print(f"Error with {url}: {str(e)[:100]}")

print("\nDone checking URLs.")