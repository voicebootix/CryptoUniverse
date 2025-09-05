import asyncio
from playwright.async_api import async_playwright
import json
import time
from typing import Dict, Any

class RememberMeTestError(Exception):
    """Custom exception for Remember Me test failures"""
    pass

async def verify_cookie_security(cookies: list) -> None:
    """Verify security settings of cookies"""
    print("\n🔍 Verifying Cookie Security...")
    
    required_flags = {
        "remember_me_token": {
            "secure": True,
            "httpOnly": True,
            "sameSite": "Lax"
        }
    }
    
    for cookie in cookies:
        if cookie["name"] in required_flags:
            for flag, value in required_flags[cookie["name"]].items():
                if cookie.get(flag) != value:
                    raise RememberMeTestError(
                        f"Cookie '{cookie['name']}' missing required security flag: {flag}"
                    )
    
    print("✅ Cookie security verified")

async def verify_session_storage(page) -> None:
    """Verify session storage configuration"""
    print("\n🔍 Checking Session Storage...")
    
    storage = await page.evaluate("""() => {
        const data = {};
        for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            data[key] = sessionStorage.getItem(key);
        }
        return data;
    }""")
    
    required_keys = ["user_email", "remember_me_enabled"]
    for key in required_keys:
        if key not in storage:
            raise RememberMeTestError(f"Missing required session storage key: {key}")
    
    print("✅ Session storage verified")

async def test_remember_me_functionality():
    """Test the Remember Me login feature"""
    
    test_credentials = {
        "email": "test@cryptouniverse.com",
        "password": "TestPassword123!"
    }
    
    try:
        print("\n🔄 Starting Remember Me Feature Test...")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage', '--no-sandbox']
            )
            
            # Create new context
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            
            # Create new page
            page = await context.new_page()
            
            # Step 1: Initial Login with Remember Me
            print("\n1️⃣ Testing Initial Login with Remember Me...")
            
            await page.goto("https://cryptouniverse.onrender.com/login")
            await page.wait_for_load_state("networkidle")
            
            # Fill login form
            await page.fill("input[type='email']", test_credentials["email"])
            await page.fill("input[type='password']", test_credentials["password"])
            
            # Check Remember Me
            remember_me = await page.query_selector("input[type='checkbox'][name='remember_me']")
            if not remember_me:
                raise RememberMeTestError("Remember Me checkbox not found")
            
            await remember_me.check()
            
            # Submit form
            await page.click("button[type='submit']")
            await page.wait_for_load_state("networkidle")
            
            # Verify successful login
            if not await page.query_selector("text=Dashboard"):
                raise RememberMeTestError("Login failed - Dashboard not found")
            
            # Step 2: Verify Cookies and Storage
            print("\n2️⃣ Verifying Cookies and Storage...")
            
            cookies = await context.cookies()
            await verify_cookie_security(cookies)
            await verify_session_storage(page)
            
            # Step 3: Logout and Verify
            print("\n3️⃣ Testing Logout Process...")
            
            await page.click("text=Logout")
            await page.wait_for_load_state("networkidle")
            
            if await page.query_selector("text=Dashboard"):
                raise RememberMeTestError("Logout failed - Dashboard still accessible")
            
            # Step 4: Reload Login Page
            print("\n4️⃣ Testing Remember Me After Reload...")
            
            await page.reload()
            await page.wait_for_load_state("networkidle")
            
            # Verify email is pre-filled
            email_value = await page.input_value("input[type='email']")
            if email_value != test_credentials["email"]:
                raise RememberMeTestError("Email not remembered after reload")
            
            # Verify password field is empty (for security)
            password_value = await page.input_value("input[type='password']")
            if password_value:
                raise RememberMeTestError("Password should not be remembered")
            
            # Step 5: Test Auto-Login
            print("\n5️⃣ Testing Auto-Login Functionality...")
            
            # Fill password and login
            await page.fill("input[type='password']", test_credentials["password"])
            await page.click("button[type='submit']")
            await page.wait_for_load_state("networkidle")
            
            # Verify successful login
            if not await page.query_selector("text=Dashboard"):
                raise RememberMeTestError("Auto-login failed - Dashboard not found")
            
            # Step 6: Clear Remember Me
            print("\n6️⃣ Testing Remember Me Clearing...")
            
            await page.click("text=Logout")
            await page.wait_for_load_state("networkidle")
            
            # Clear cookies and reload
            await context.clear_cookies()
            await page.reload()
            await page.wait_for_load_state("networkidle")
            
            # Verify email is not pre-filled
            email_value = await page.input_value("input[type='email']")
            if email_value:
                raise RememberMeTestError("Email remembered after clearing cookies")
            
            # Cleanup
            await context.close()
            await browser.close()
            
            print("\n✅ Remember Me functionality test completed successfully!")
            
    except RememberMeTestError as e:
        print(f"\n❌ Remember Me Test Failed: {str(e)}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(test_remember_me_functionality())
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        raise
