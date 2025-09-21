import os
import requests
import time

def grant_admin_strategies():
    BASE_URL = "https://cryptouniverse.onrender.com/api/v1"

    print("Step 1: Login...")
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        raise ValueError("ADMIN_EMAIL and ADMIN_PASSWORD environment variables are required")

    login_data = {"email": admin_email, "password": admin_password}

    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=30)

        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")
            return

        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        print("Login successful!")

        print("Step 2: Grant admin full strategy access...")
        grant_payload = {
            "strategy_type": "all",
            "grant_reason": "fix_missing_strategies"
        }

        grant_response = requests.post(
            f"{BASE_URL}/admin-strategy-access/grant-full-access",
            json=grant_payload,
            headers=headers,
            timeout=60  # Longer timeout for this critical operation
        )

        print(f"Grant request status: {grant_response.status_code}")

        if grant_response.status_code == 200:
            data = grant_response.json()
            print(f"SUCCESS!")
            print(f"Strategies granted: {data.get('total_strategies', 0)}")
            print(f"Grant type: {data.get('grant_type', 'unknown')}")
            print(f"Message: {data.get('message', 'No message')}")

            # Wait a bit for the grant to propagate
            print("Waiting 5 seconds for changes to propagate...")
            time.sleep(5)

            # Try to verify by checking portfolio
            print("Step 3: Verifying portfolio...")
            portfolio_response = requests.get(
                f"{BASE_URL}/strategies/my-portfolio",
                headers=headers,
                timeout=45
            )

            if portfolio_response.status_code == 200:
                portfolio_data = portfolio_response.json()
                strategies = portfolio_data.get("active_strategies", [])
                print(f"VERIFICATION: Found {len(strategies)} active strategies")

                if len(strategies) > 0:
                    print("SUCCESS! Strategies are now available!")
                    print("Sample strategies:")
                    for i, strategy in enumerate(strategies[:3]):
                        print(f"  {i+1}. {strategy.get('name', 'Unnamed')}")
                else:
                    print("Still no strategies visible - may need backend restart or cache clear")
            else:
                print(f"Portfolio verification failed: {portfolio_response.status_code}")

        else:
            print(f"Grant failed: {grant_response.text[:300]}")

    except requests.exceptions.Timeout:
        print("Request timed out - Render backend is slow but grant may have succeeded")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    grant_admin_strategies()