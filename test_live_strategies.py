import requests
import json

def test_live_strategies():
    # Base URL for the live app
    base_url = "https://cryptouniverse-backend.onrender.com"

    # First, let's test the my-portfolio endpoint
    headers = {
        "Authorization": "Bearer your-auth-token-here",  # You'll need to get this from browser
        "Content-Type": "application/json"
    }

    # Test strategies endpoint
    try:
        response = requests.get(f"{base_url}/api/v1/strategies/my-portfolio", headers=headers)
        print("My Portfolio Response:")
        print("Status:", response.status_code)
        print("Response:", response.text)
        print("-" * 50)

        # Test marketplace endpoint
        response2 = requests.get(f"{base_url}/api/v1/strategies/marketplace", headers=headers)
        print("Marketplace Response:")
        print("Status:", response2.status_code)
        print("Response:", response2.text[:1000])  # First 1000 chars

    except Exception as e:
        print(f"Error: {e}")

    # Also test without auth to see what we get
    print("\n" + "="*50)
    print("Testing endpoints without auth:")

    try:
        response = requests.get(f"{base_url}/api/v1/strategies/available")
        print("Available strategies (no auth):")
        print("Status:", response.status_code)
        print("Response:", response.text[:500])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_live_strategies()