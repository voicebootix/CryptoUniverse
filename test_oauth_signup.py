import asyncio
from playwright.async_api import async_playwright
import requests
import json
from urllib.parse import urlparse, parse_qs
import os

class OAuthTestError(Exception):
    """Custom exception for OAuth test failures"""
    pass

async def verify_oauth_config():
    """Verify OAuth configuration settings"""
    print("\n🔍 Verifying OAuth Configuration...")
    
    base_url = "https://cryptouniverse.onrender.com"
    oauth_config_url = f"{base_url}/api/v1/auth/oauth/config"
    
    try:
        response = requests.get(oauth_config_url)
        config = response.json()
        
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
        
    except requests.exceptions.RequestException as e:
        raise OAuthTestError(f"Failed to fetch OAuth config: {str(e)}")
    except json.JSONDecodeError:
        raise OAuthTestError("Invalid OAuth configuration format")

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
            await page.goto("https://cryptouniverse.onrender.com/signup")
            await page.wait_for_load_state("networkidle")
            
            # Step 3: Verify Google Sign-up Button
            print("\n🔍 Checking Google Sign-up Button...")
            google_button = await page.query_selector("'Sign up with Google'")
            if not google_button:
                raise OAuthTestError("Google sign-up button not found")
            
            # Step 4: Click Google Sign-up Button
            print("\n🖱️ Clicking Google Sign-up Button...")
            async with page.expect_navigation() as navigation_info:
                await google_button.click()
            
            # Step 5: Verify Redirect
            response = await navigation_info.value
            redirect_url = response.url
            
            print("\n🔍 Verifying OAuth Redirect...")
            parsed_url = urlparse(redirect_url)
            query_params = parse_qs(parsed_url.query)
            
            # Verify required OAuth parameters
            required_params = ["client_id", "redirect_uri", "scope", "response_type"]
            for param in required_params:
                if param not in query_params:
                    raise OAuthTestError(f"Missing OAuth parameter: {param}")
            
            # Step 6: Verify Redirect URI
            redirect_uri = query_params["redirect_uri"][0]
            if not redirect_uri.startswith("https://"):
                raise OAuthTestError("Insecure redirect URI detected")
            
            # Step 7: Verify OAuth Scopes
            scopes = query_params["scope"][0].split(" ")
            required_scopes = ["email", "profile"]
            for scope in required_scopes:
                if scope not in scopes:
                    raise OAuthTestError(f"Missing required scope: {scope}")
            
            print("\n✅ OAuth redirect parameters verified")
            
            # Step 8: Verify Error Handling
            print("\n🔍 Testing Error Handling...")
            
            # Test with invalid state parameter
            error_url = f"{oauth_config['redirect_uri']}?error=access_denied&state=invalid"
            await page.goto(error_url)
            
            # Verify error message is displayed
            error_message = await page.query_selector("text=Authentication failed")
            if not error_message:
                raise OAuthTestError("Error handling not implemented properly")
            
            print("✅ Error handling verified")
            
            # Cleanup
            await context.close()
            await browser.close()
            
            print("\n✅ OAuth sign-up flow test completed successfully!")
            
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
