import requests

BASE_URL = "https://cryptouniverse.onrender.com"

response = requests.post(f"{BASE_URL}/api/v1/auth/login",
                       json={"email": "admin@cryptouniverse.com",
                            "password": "AdminPass123!"})
token = response.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

print("Testing Portfolio Endpoint...")
response = requests.get(f"{BASE_URL}/api/v1/unified-strategies/portfolio",
                      headers=headers, timeout=30)
if response.status_code == 200:
    data = response.json()
    if "greenlet_spawn" in str(data):
        print("GREENLET ERROR FOUND!")
        print(f"Error: {data.get(\"metadata\", {}).get(\"error\", \"unknown\")}")
    else:
        print("SUCCESS - No greenlet error")
else:
    print(f"HTTP Error: {response.status_code}")
