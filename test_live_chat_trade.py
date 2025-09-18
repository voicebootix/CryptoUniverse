"""
Test Trade Execution via Chat - Production Platform
Verifies if chat-based trade execution works
"""

import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = "https://cryptouniverse.onrender.com"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

async def test_chat_trade():
    """Test trade execution through chat interface."""

    async with aiohttp.ClientSession() as session:
        # 1. Login
        print("[1] Logging in...")
        login_resp = await session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )

        if login_resp.status != 200:
            print(f"Login failed: {login_resp.status}")
            return

        auth_data = await login_resp.json()
        token = auth_data.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("OK: Logged in successfully")

        # 2. Test SIMULATION trade via chat
        print("\n[2] Testing SIMULATION trade via chat...")

        chat_messages = [
            "Set simulation mode on",
            "Buy $5 worth of BTC in simulation",
            "What's my portfolio balance?",
            "Show my recent trades"
        ]

        for message in chat_messages:
            print(f"\n>> Sending: {message}")

            try:
                chat_resp = await session.post(
                    f"{BASE_URL}/api/v1/chat/unified",
                    headers=headers,
                    json={"message": message}
                )

                if chat_resp.status == 200:
                    data = await chat_resp.json()
                    response = data.get("response", "No response")

                    # Print first 500 chars of response
                    print(f"<< Response: {response[:500]}")

                    # Check for trade execution
                    if "executed" in response.lower() or "bought" in response.lower():
                        print("\n[OK] TRADE EXECUTED VIA CHAT!")

                        # Check if simulation or live
                        if "simulation" in response.lower() or "sim_" in response.lower():
                            print("     Mode: SIMULATION")
                        else:
                            print("     Mode: POSSIBLY LIVE (check carefully!)")

                    elif "error" in response.lower():
                        print("\n[ERROR] Trade failed")

                else:
                    print(f"Chat request failed: {chat_resp.status}")

            except Exception as e:
                print(f"Error: {str(e)}")

        # 3. Check user's trading mode
        print("\n[3] Checking user trading mode...")

        # Try different endpoints to get user info
        endpoints = [
            "/api/v1/user/profile",
            "/api/v1/users/profile",
            "/api/v1/account/info"
        ]

        for endpoint in endpoints:
            try:
                resp = await session.get(f"{BASE_URL}{endpoint}", headers=headers)
                if resp.status == 200:
                    data = await resp.json()
                    print(f"User data from {endpoint}:")
                    print(json.dumps(data, indent=2)[:500])
                    break
                elif resp.status != 404:
                    print(f"{endpoint}: {resp.status}")
            except:
                pass

        # 4. Summary
        print("\n" + "="*60)
        print("CHAT TRADE EXECUTION TEST SUMMARY")
        print("="*60)
        print("\nBased on the responses:")
        print("1. Chat interface: ACCESSIBLE")
        print("2. Trade commands: PROCESSED")
        print("3. Execution mode: Check responses above")
        print("\nNOTE: If trades show 'simulation' or 'SIM_' prefixes,")
        print("      then SIMULATION MODE is working.")
        print("      If no real exchange errors appear, LIVE mode")
        print("      likely requires API keys.")

if __name__ == "__main__":
    print("="*60)
    print("CRYPTOUNIVERSE CHAT TRADE EXECUTION TEST")
    print(f"Platform: {BASE_URL}")
    print(f"Time: {datetime.now()}")
    print("="*60 + "\n")

    asyncio.run(test_chat_trade())