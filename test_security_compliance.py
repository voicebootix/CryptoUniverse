import asyncio
from playwright.async_api import async_playwright
import ssl
import requests
import json
from urllib.parse import urlparse
import socket

class SecurityTestError(Exception):
    """Custom exception for security test failures"""
    pass

async def verify_ssl_certificate(domain):
    """Verify SSL certificate validity and properties"""
    try:
        print("\n🔒 Verifying SSL Certificate...")
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                
                # Check certificate properties
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
    
    base_url = "https://cryptouniverse.onrender.com"
    dashboard_url = f"{base_url}/dashboard"
    
    try:
        # Step 1: Verify HTTPS and SSL
        domain = urlparse(base_url).netloc
        await verify_ssl_certificate(domain)
        
        # Step 2: Check Security Headers
        headers = await check_security_headers(base_url)
        
        # Step 3: Test Dashboard Security
        print("\n🔐 Testing Dashboard Security...")
        async with async_playwright() as p:
            # Launch browser with security flags
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--ignore-certificate-errors'
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
            await page.goto(f"{base_url}/login")
            
            # Fill login form
            await page.fill("input[type='email']", "test@cryptouniverse.com")
            await page.fill("input[type='password']", "TestPassword123!")
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
            
            # Check secure cookie attributes
            cookies = await context.cookies()
            for cookie in cookies:
                assert cookie.get("secure", False), "Cookie not marked as secure"
                assert cookie.get("httpOnly", False), "Cookie not marked as httpOnly"
            
            print("✅ Session cookies are secure")
            
            # Step 8: Check CSP compliance
            print("\n🛡️ Checking Content Security Policy...")
            csp_header = headers.get('Content-Security-Policy', '')
            assert csp_header, "No Content Security Policy found"
            print("✅ Content Security Policy is configured")
            
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
