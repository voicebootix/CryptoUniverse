import asyncio
from playwright.async_api import async_playwright
import ssl
import requests
import json
from urllib.parse import urlparse
import socket
import os

class SecurityTestError(Exception):
    """Custom exception for security test failures"""
    pass

# Environment variables with defaults
BASE_URL = os.environ.get("BASE_URL", "https://cryptouniverse.onrender.com")
CU_TEST_EMAIL = os.environ.get("CU_TEST_EMAIL")
CU_TEST_PASSWORD = os.environ.get("CU_TEST_PASSWORD")

# Sensitive cookie patterns
SENSITIVE_COOKIE_PATTERNS = [
    "session",
    "auth",
    "token",
    "jwt",
    "remember",
    "secure"
]

def is_sensitive_cookie(cookie_name: str) -> bool:
    """Check if cookie name matches sensitive patterns"""
    return any(pattern in cookie_name.lower() for pattern in SENSITIVE_COOKIE_PATTERNS)

async def verify_ssl_certificate(domain):
    """Verify SSL certificate validity and properties"""
    try:
        print("\n🔒 Verifying SSL Certificate...")
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                
                if not cert:
                    raise SecurityTestError("No SSL certificate found")
                
                print("✅ SSL Certificate verified")
                print(f"Issuer: {dict(x[0] for x in cert['issuer'])}")
                print(f"Valid until: {cert['notAfter']}")
                return True
    except Exception as e:
        raise SecurityTestError(f"SSL verification failed: {str(e)}")

async def check_security_headers(url):
    """Check for required security headers"""
    print("\n🛡️ Checking Security Headers...")
    required_headers = {
        'Strict-Transport-Security',
        'X-Content-Type-Options',
        'X-Frame-Options',
        'X-XSS-Protection',
        'Content-Security-Policy'
    }
    
    response = requests.get(url)
    headers = response.headers
    
    missing_headers = required_headers - set(headers.keys())
    if missing_headers:
        print("⚠️ Missing security headers:", missing_headers)
    else:
        print("✅ All required security headers present")
    
    return headers

async def test_dashboard_security():
    """Test dashboard security and encryption compliance"""
    
    # Verify test credentials are available
    if not CU_TEST_EMAIL or not CU_TEST_PASSWORD:
        raise SecurityTestError(
            "Test credentials not found. Please set CU_TEST_EMAIL and CU_TEST_PASSWORD environment variables."
        )
    
    try:
        # Step 1: Verify HTTPS and SSL
        domain = urlparse(BASE_URL).netloc
        await verify_ssl_certificate(domain)
        
        # Step 2: Check Security Headers
        headers = await check_security_headers(BASE_URL)
        
        # Step 3: Test Dashboard Security
        print("\n🔐 Testing Dashboard Security...")
        async with async_playwright() as p:
            # Launch browser with security flags (removed certificate error ignore)
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            
            # Create context with security settings
            context = await browser.new_context(
                bypass_csp=False,
                ignore_https_errors=False,
                java_script_enabled=True
            )
            
            # Create new page
            page = await context.new_page()
            
            # Step 4: Login securely
            print("\n🔑 Testing Secure Login...")
            await page.goto(f"{BASE_URL}/login")
            
            # Fill login form with environment variables
            await page.fill("input[type='email']", CU_TEST_EMAIL)
            await page.fill("input[type='password']", CU_TEST_PASSWORD)
            await page.click("button[type='submit']")
            
            # Wait for dashboard
            await page.wait_for_load_state("networkidle")
            
            # Step 5: Verify secure connection
            print("\n🔍 Verifying Secure Connection...")
            security_details = await page.evaluate("""() => {
                return {
                    protocol: window.location.protocol,
                    encrypted: document.location.protocol === 'https:',
                    cookies: document.cookie
                }
            }""")
            
            assert security_details["protocol"] == "https:", "Not using HTTPS"
            assert security_details["encrypted"], "Connection not encrypted"
            
            # Step 6: Check sensitive data handling
            print("\n🔐 Checking Sensitive Data Handling...")
            
            # Verify no sensitive data in HTML source
            page_content = await page.content()
            sensitive_patterns = ["password", "secret", "token", "key"]
            for pattern in sensitive_patterns:
                assert pattern not in page_content.lower(), f"Found sensitive data in page source: {pattern}"
            
            # Step 7: Test session security
            print("\n🔒 Testing Session Security...")
            
            # Check secure cookie attributes for sensitive cookies only
            cookies = await context.cookies()
            sensitive_cookies = [c for c in cookies if is_sensitive_cookie(c["name"])]
            
            for cookie in sensitive_cookies:
                assert cookie.get("secure", False), f"Cookie '{cookie['name']}' not marked as secure"
                assert cookie.get("httpOnly", False), f"Cookie '{cookie['name']}' not marked as httpOnly"
            
            print(f"✅ {len(sensitive_cookies)} sensitive cookies verified as secure")
            
            # Cleanup
            await context.close()
            await browser.close()
            
            print("\n✅ All security checks passed successfully!")
            
    except SecurityTestError as e:
        print(f"\n❌ Security Test Failed: {str(e)}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_dashboard_security())