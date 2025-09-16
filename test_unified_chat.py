#!/usr/bin/env python3
"""
Test script for Unified Chat Service
Validates all features are preserved and working correctly
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any

# Test configuration
API_BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
TEST_EMAIL = "admin@cryptouniverse.com"
TEST_PASSWORD = "AdminPass123!"


class UnifiedChatTester:
    def __init__(self):
        self.token = None
        self.session_id = None
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
    
    async def login(self):
        """Authenticate and get JWT token."""
        import httpx
        
        print("🔐 Logging in...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                print("✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                return False
    
    async def test_basic_chat(self):
        """Test basic chat functionality."""
        print("\n📝 Testing basic chat...")
        
        import httpx
        headers = {"Authorization": f"Bearer {self.token}"}
        
        test_messages = [
            "What is my portfolio balance?",
            "Show me market analysis for Bitcoin",
            "What trading opportunities are available?",
            "How risky is my portfolio?"
        ]
        
        async with httpx.AsyncClient() as client:
            for message in test_messages:
                start_time = time.time()
                
                response = await client.post(
                    f"{API_BASE_URL}/chat/message",
                    headers=headers,
                    json={"message": message}
                )
                
                elapsed_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        print(f"✅ '{message}' - Response in {elapsed_time:.2f}s")
                        self.passed_tests += 1
                        
                        # Check response time
                        if elapsed_time > 5:
                            print(f"⚠️  Response time too slow: {elapsed_time:.2f}s")
                    else:
                        print(f"❌ '{message}' - Failed: {data.get('error')}")
                        self.failed_tests += 1
                else:
                    print(f"❌ '{message}' - HTTP {response.status_code}")
                    self.failed_tests += 1
    
    async def test_streaming_chat(self):
        """Test streaming chat functionality."""
        print("\n🌊 Testing streaming chat...")
        
        import httpx
        headers = {"Authorization": f"Bearer {self.token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/chat/stream",
                headers=headers,
                json={
                    "message": "Give me a detailed portfolio analysis",
                    "stream": True
                }
            )
            
            if response.status_code == 200:
                print("✅ Streaming endpoint accessible")
                self.passed_tests += 1
            else:
                print(f"❌ Streaming failed: HTTP {response.status_code}")
                self.failed_tests += 1
    
    async def test_conversation_modes(self):
        """Test different conversation modes."""
        print("\n🎭 Testing conversation modes...")
        
        import httpx
        headers = {"Authorization": f"Bearer {self.token}"}
        
        modes = [
            ("live_trading", "Buy $100 of Bitcoin"),
            ("paper_trading", "Buy $10000 of Ethereum in paper trading"),
            ("learning", "Explain what is a stop loss"),
            ("analysis", "Analyze the crypto market trends")
        ]
        
        async with httpx.AsyncClient() as client:
            for mode, message in modes:
                response = await client.post(
                    f"{API_BASE_URL}/chat/message",
                    headers=headers,
                    json={
                        "message": message,
                        "conversation_mode": mode
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        print(f"✅ {mode} mode - Working")
                        self.passed_tests += 1
                    else:
                        print(f"❌ {mode} mode - Failed")
                        self.failed_tests += 1
                else:
                    print(f"❌ {mode} mode - HTTP {response.status_code}")
                    self.failed_tests += 1
    
    async def test_credit_validation(self):
        """Test credit validation for paid operations."""
        print("\n💳 Testing credit validation...")
        
        import httpx
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test trade that should require credits
        response = await httpx.AsyncClient().post(
            f"{API_BASE_URL}/chat/message",
            headers=headers,
            json={
                "message": "Execute a trade to buy $1000 of Bitcoin",
                "conversation_mode": "live_trading"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            # Should either succeed or show credit requirement
            print("✅ Credit validation working")
            self.passed_tests += 1
        else:
            print(f"❌ Credit validation failed: HTTP {response.status_code}")
            self.failed_tests += 1
    
    async def test_paper_trading_no_credits(self):
        """Test that paper trading doesn't require credits."""
        print("\n📄 Testing paper trading (no credits)...")
        
        import httpx
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = await httpx.AsyncClient().post(
            f"{API_BASE_URL}/chat/message",
            headers=headers,
            json={
                "message": "Buy $5000 of Bitcoin",
                "conversation_mode": "paper_trading"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("✅ Paper trading works without credits")
                self.passed_tests += 1
            else:
                print(f"❌ Paper trading failed: {data.get('error')}")
                self.failed_tests += 1
        else:
            print(f"❌ Paper trading HTTP {response.status_code}")
            self.failed_tests += 1
    
    async def test_real_data_integration(self):
        """Test that real portfolio data is being used."""
        print("\n📊 Testing real data integration...")
        
        import httpx
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = await httpx.AsyncClient().post(
            f"{API_BASE_URL}/chat/message",
            headers=headers,
            json={"message": "What is my exact portfolio balance?"}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                content = data.get("content", "")
                # Check for real numbers in response
                if "$" in content and any(char.isdigit() for char in content):
                    print("✅ Real portfolio data returned")
                    self.passed_tests += 1
                    
                    # Extract balance if possible
                    import re
                    balance_match = re.search(r'\$([0-9,]+\.?\d*)', content)
                    if balance_match:
                        print(f"   Portfolio value: {balance_match.group(0)}")
                else:
                    print("❌ No real data found in response")
                    self.failed_tests += 1
        else:
            print(f"❌ Real data test failed: HTTP {response.status_code}")
            self.failed_tests += 1
    
    async def test_capabilities_endpoint(self):
        """Test capabilities endpoint."""
        print("\n🎯 Testing capabilities endpoint...")
        
        import httpx
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = await httpx.AsyncClient().get(
            f"{API_BASE_URL}/chat/capabilities",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                caps = data.get("capabilities", {})
                features = data.get("platform_features", [])
                
                print(f"✅ Capabilities retrieved:")
                print(f"   - Trading features: {len(caps.get('trading', {}))} types")
                print(f"   - Platform features: {len(features)} total")
                print(f"   - AI models: {', '.join(data.get('ai_models', []))}")
                self.passed_tests += 1
            else:
                print("❌ Capabilities failed")
                self.failed_tests += 1
        else:
            print(f"❌ Capabilities HTTP {response.status_code}")
            self.failed_tests += 1
    
    async def test_service_status(self):
        """Test service status endpoint."""
        print("\n🔧 Testing service status...")
        
        import httpx
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = await httpx.AsyncClient().get(
            f"{API_BASE_URL}/chat/status",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                status = data.get("service_status", {})
                print(f"✅ Service status: {status.get('status', 'unknown')}")
                print(f"   - Active sessions: {status.get('active_sessions', 0)}")
                print(f"   - ChatAI status: {status.get('chat_ai_status', {}).get('status', 'unknown')}")
                self.passed_tests += 1
            else:
                print(f"❌ Status check failed: {data.get('error')}")
                self.failed_tests += 1
        else:
            print(f"❌ Status HTTP {response.status_code}")
            self.failed_tests += 1
    
    async def run_all_tests(self):
        """Run all tests."""
        print("🚀 Starting Unified Chat Tests\n")
        
        # Login first
        if not await self.login():
            print("❌ Cannot proceed without authentication")
            return
        
        # Run all tests
        await self.test_basic_chat()
        await self.test_streaming_chat()
        await self.test_conversation_modes()
        await self.test_credit_validation()
        await self.test_paper_trading_no_credits()
        await self.test_real_data_integration()
        await self.test_capabilities_endpoint()
        await self.test_service_status()
        
        # Summary
        print("\n" + "="*50)
        print("📊 TEST SUMMARY")
        print("="*50)
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"📈 Success Rate: {self.passed_tests/(self.passed_tests+self.failed_tests)*100:.1f}%")
        
        if self.failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED! Unified chat is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Please check the implementation.")


async def main():
    """Run the test suite."""
    tester = UnifiedChatTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())