"""
End-to-end tests for password reset functionality.
"""

import time
import pytest
from playwright.async_api import async_playwright, Page, expect
from typing import Generator
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

# Constants
FRONTEND_URL = settings.FRONTEND_URL
DEFAULT_TIMEOUT = 10000  # 10 seconds
RETRY_ATTEMPTS = 3

@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
async def wait_for_element(page: Page, selector: str, timeout: int = DEFAULT_TIMEOUT):
    """Wait for element with retry logic and return the element handle."""
    try:
        element = await page.wait_for_selector(selector, timeout=timeout)
        if not element:
            raise Exception(f"Element {selector} not found")
        return element
    except Exception as e:
        print(f"Failed to find element {selector}: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_password_reset_flow():
    """
    Test the complete password reset flow.
    
    Steps:
    1. Navigate to login page
    2. Click forgot password
    3. Enter email
    4. Submit form
    5. Verify success message
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1920,1080",
                "--disable-dev-shm-usage",  # Prevent crashes in containers
                "--no-sandbox",  # Required for Docker
                "--single-process"  # Better stability
            ]
        )
        
        async with browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        ) as context:
            page = await context.new_page()
            page.set_default_timeout(DEFAULT_TIMEOUT)
            
            try:
                # Navigate to frontend
                await page.goto(FRONTEND_URL, wait_until="networkidle")
                await page.wait_for_load_state("domcontentloaded")
                
                # Click "Forgot Password" link
                forgot_password = page.get_by_test_id("forgot-password-link")
                await expect(forgot_password).to_be_visible()
                await forgot_password.click()
                
                # Fill email
                email_input = page.get_by_test_id("email-input")
                await expect(email_input).to_be_visible()
                await email_input.fill("admin@cryptouniverse.com")
                
                # Submit form
                submit_button = page.get_by_test_id("submit-button")
                await expect(submit_button).to_be_visible()
                await submit_button.click()
                
                # Verify success message
                success_message = page.get_by_test_id("success-message")
                await expect(success_message).to_be_visible()
                await expect(success_message).to_have_text(
                    "Password reset link has been sent to your email"
                )
                
            except Exception as e:
                # Take screenshot on failure
                await page.screenshot(path=f"password_reset_error_{int(time.time())}.png")
                raise

@pytest.mark.asyncio
async def test_password_reset_validation():
    """
    Test password reset form validation.
    
    Tests:
    1. Empty email validation
    2. Invalid email format
    3. Non-existent email shows success (no enumeration)
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        
        async with browser.new_context() as context:
            page = await context.new_page()
            page.set_default_timeout(DEFAULT_TIMEOUT)
            
            try:
                # Navigate to frontend
                await page.goto(FRONTEND_URL, wait_until="networkidle")
                
                # Click forgot password
                forgot_password = page.get_by_test_id("forgot-password-link")
                await expect(forgot_password).to_be_visible()
                await forgot_password.click()
                
                # Test empty email
                submit_button = page.get_by_test_id("submit-button")
                await expect(submit_button).to_be_visible()
                await submit_button.click()
                
                # Check validation error
                email_error = page.get_by_test_id("email-error")
                await expect(email_error).to_be_visible()
                await expect(email_error).to_have_text("Email is required")
                
                # Test invalid email format
                email_input = page.get_by_test_id("email-input")
                await expect(email_input).to_be_visible()
                await email_input.fill("invalid-email")
                await submit_button.click()
                
                # Check format error
                await expect(email_error).to_be_visible()
                await expect(email_error).to_have_text("Please enter a valid email address")
                
                # Test non-existent email - should show success
                await email_input.fill("nonexistent@cryptouniverse.com")
                await submit_button.click()
                
                # Verify success message (no account enumeration)
                success_message = page.get_by_test_id("success-message")
                await expect(success_message).to_be_visible()
                
                # Ensure no error is shown
                global_error = page.get_by_test_id("global-error")
                await expect(global_error).not_to_be_visible()
                
            except Exception as e:
                # Take screenshot on failure
                await page.screenshot(path=f"password_reset_validation_error_{int(time.time())}.png")
                raise
