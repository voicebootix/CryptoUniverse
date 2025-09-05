import asyncio
from playwright.async_api import async_playwright
import requests
import json
import os
from typing import Dict, Any

class OAuthTestError(Exception):
    """Custom exception for OAuth test failures"""
    pass

# Environment variables with defaults
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
OAUTH_CONFIG_URL = f"{BASE_URL}/api/v1/auth/oauth/config"

async def fetch_oauth_config() -> Dict[str, Any]:
    """Fetch OAuth configuration using asyncio thread pool"""
    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(OAUTH_CONFIG_URL, timeout=5)
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise OAuthTestError(f"Failed to fetch OAuth config: {str(e)}")
    except json.JSONDecodeError as e:
        raise OAuthTestError(f"Invalid OAuth configuration format: {str(e)}")

async def verify_oauth_config():
    """Verify OAuth configuration settings"""
    print("\n🔍 Verifying OAuth Configuration...")
    
    try:
        config = await fetch_oauth_config()
        
        # Verify required OAuth settings
        required_settings = [
            "client_id",
            "redirect_uri",
            "scopes",
            "auth_endpoint"
        ]
        
        for setting in required_settings:
            if setting not in config:
                raise OAuthTestError(f"Missing OAuth config: {setting}")
        
        # Verify redirect URI format
        redirect_uri = config["redirect_uri"]
        if not redirect_uri.startswith("https://"):
            raise OAuthTestError("Redirect URI must use HTTPS")
        
        # Verify required OAuth scopes
        required_scopes = {"email", "profile"}
        configured_scopes = set(config["scopes"].split(" "))
        missing_scopes = required_scopes - configured_scopes
        
        if missing_scopes:
            raise OAuthTestError(f"Missing required OAuth scopes: {missing_scopes}")
        
        print("✅ OAuth configuration verified")
        return config
        
    except OAuthTestError:
        raise
    except Exception as e:
        raise OAuthTestError(f"Unexpected error during OAuth config verification: {str(e)}")

async def test_oauth_signup_flow():
    """Test the complete OAuth sign-up flow"""
    try:
        # Step 1: Verify OAuth Configuration
        oauth_config = await verify_oauth_config()
        
        print("\n🔄 Testing OAuth Sign-up Flow...")
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage', '--no-sandbox']
            )
            
            # Create new context
            context = await browser.new_context()
            page = await context.new_page()
            
            # Step 2: Navigate to signup page
            print("\n🌐 Navigating to signup page...")
            await page.goto(f"{BASE_URL}/signup")
            await page.wait_for_load_state("networkidle")
            
            # Rest of the test implementation...
            # (Previous implementation remains the same)
            
            await context.close()
            await browser.close()
            
    except OAuthTestError as e:
        print(f"\n❌ OAuth Test Failed: {str(e)}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(test_oauth_signup_flow())
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        raise