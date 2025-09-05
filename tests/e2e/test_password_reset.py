"""
End-to-end tests for password reset functionality.
"""

import asyncio
import pytest
from playwright.async_api import Page, expect
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
async def wait_for_element(page: Page, selector: str, timeout: int = DEFAULT_TIMEOUT) -> None:
    """Wait for element with retry logic."""
    try:
        await page.wait_for_selector(selector, timeout=timeout)
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
    browser = None
    context = None
    page = None
    
    try:
        # Launch browser with custom viewport and device scale
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--window-size=1920,1080",
                "--disable-dev-shm-usage",  # Prevent crashes in containers
                "--no-sandbox",  # Required for Docker
                "--single-process"  # Better stability
            ]
        )
        
        # Create context with viewport settings
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        
        # Create page and set default timeout
        page = await context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        
        # Navigate to frontend
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        
        # Wait for page to be fully loaded
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_load_state("networkidle")
        
        # Click "Forgot Password" link using data-testid
        forgot_password_button = await wait_for_element(
            page,
            '[data-testid="forgot-password-link"]'
        )
        await forgot_password_button.click()
        
        # Wait for form to appear and enter email
        email_input = await wait_for_element(
            page,
            '[data-testid="email-input"]'
        )
        await email_input.fill("admin@cryptouniverse.com")
        
        # Submit form
        submit_button = await wait_for_element(
            page,
            '[data-testid="submit-button"]'
        )
        await submit_button.click()
        
        # Wait for success message
        success_message = await wait_for_element(
            page,
            '[data-testid="success-message"]'
        )
        
        # Verify success message
        message_text = await success_message.text_content()
        assert "password reset link has been sent" in message_text.lower()
        
    except Exception as e:
        # Take screenshot on failure
        if page:
            await page.screenshot(path="password_reset_error.png")
        raise e
        
    finally:
        # Cleanup
        if context:
            await context.close()
        if browser:
            await browser.close()

@pytest.mark.asyncio
async def test_password_reset_validation():
    """
    Test password reset form validation.
    
    Tests:
    1. Empty email validation
    2. Invalid email format
    3. Non-existent email
    """
    browser = None
    context = None
    page = None
    
    try:
        # Setup browser
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to frontend
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        
        # Click forgot password
        forgot_password_button = await wait_for_element(
            page,
            '[data-testid="forgot-password-link"]'
        )
        await forgot_password_button.click()
        
        # Test empty email
        submit_button = await wait_for_element(
            page,
            '[data-testid="submit-button"]'
        )
        await submit_button.click()
        
        error_message = await wait_for_element(
            page,
            '[data-testid="error-message"]'
        )
        assert "email is required" in (await error_message.text_content()).lower()
        
        # Test invalid email format
        email_input = await wait_for_element(
            page,
            '[data-testid="email-input"]'
        )
        await email_input.fill("invalid-email")
        await submit_button.click()
        
        error_message = await wait_for_element(
            page,
            '[data-testid="error-message"]'
        )
        assert "valid email" in (await error_message.text_content()).lower()
        
        # Test non-existent email
        await email_input.fill("nonexistent@cryptouniverse.com")
        await submit_button.click()
        
        error_message = await wait_for_element(
            page,
            '[data-testid="error-message"]'
        )
        assert "account not found" in (await error_message.text_content()).lower()
        
    finally:
        # Cleanup
        if context:
            await context.close()
        if browser:
            await browser.close()
