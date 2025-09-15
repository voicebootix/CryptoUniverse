#!/usr/bin/env python3
"""
Comprehensive Chat Endpoints Testing
Tests all chat functionality on live deployment
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# Live deployment URL
BASE_URL = "https://cryptouniverse.onrender.com"

class ChatEndpointTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.session_id = None
        
    async def setup_session(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        
    async def cleanup_session(self):
        """Clean up HTTP session"""
        if self.session:
            await self.session.close()
            
    async def login(self) -> bool:
        """Login and get auth token"""
        try:
            login_data = {
                "username": "testuser@example.com",
                "password": "testpass123"
            }
            
            async with self.session.post(
                f"{BASE_URL}/api/v1/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    print(f"✅ Login successful, token: {self.auth_token[:20]}...")
                    return True
                else:
                    text = await response.text()
                    print(f"❌ Login failed: {response.status} - {text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
            
    async def create_chat_session(self) -> bool:
        """Create a new chat session"""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            async with self.session.post(
                f"{BASE_URL}/api/v1/chat/sessions",
                headers=headers,
                json={"title": "Test Session"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.session_id = data.get("id")
                    print(f"✅ Chat session created: {self.session_id}")
                    return True
                else:
                    text = await response.text()
                    print(f"❌ Session creation failed: {response.status} - {text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Session creation error: {e}")
            return False
            
    async def test_chat_message(self, message: str, test_name: str) -> Dict[str, Any]:
        """Send a chat message and analyze response"""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "message": message,
                "session_id": self.session_id
            }
            
            print(f"\n🔄 Testing: {test_name}")
            print(f"📤 Message: {message}")
            
            start_time = time.time()
            
            async with self.session.post(
                f"{BASE_URL}/api/v1/chat/message",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                end_time = time.time()
                response_time = end_time - start_time
                
                if response.status == 200:
                    data = await response.json()
                    
                    result = {
                        "test_name": test_name,
                        "status": "success",
                        "response_time": response_time,
                        "message": data.get("message", ""),
                        "intent": data.get("intent", ""),
                        "metadata": data.get("metadata", {}),
                        "raw_response": data
                    }
                    
                    print(f"✅ Success ({response_time:.2f}s)")
                    print(f"📥 Response: {data.get('message', '')[:200]}...")
                    print(f"🎯 Intent: {data.get('intent', 'N/A')}")
                    
                    return result
                else:
                    text = await response.text()
                    result = {
                        "test_name": test_name,
                        "status": "failed",
                        "response_time": response_time,
                        "error": f"HTTP {response.status}: {text}",
                        "raw_response": text
                    }
                    
                    print(f"❌ Failed ({response_time:.2f}s): {response.status} - {text}")
                    return result
                    
        except Exception as e:
            result = {
                "test_name": test_name,
                "status": "error",
                "error": str(e),
                "raw_response": None
            }
            
            print(f"❌ Error: {e}")
            return result
            
    async def test_websocket_chat(self) -> Dict[str, Any]:
        """Test WebSocket chat functionality"""
        try:
            import websockets
            
            ws_url = f"wss://cryptouniverse.onrender.com/ws/chat/{self.session_id}?token={self.auth_token}"
            
            print(f"\n🔄 Testing WebSocket Chat")
            print(f"🔗 Connecting to: {ws_url}")
            
            async with websockets.connect(ws_url) as websocket:
                # Send a test message
                test_message = {
                    "type": "message",
                    "content": "Hello via WebSocket"
                }
                
                await websocket.send(json.dumps(test_message))
                print(f"📤 Sent: {test_message}")
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=30)
                response_data = json.loads(response)
                
                print(f"📥 Received: {response_data}")
                
                return {
                    "test_name": "websocket_chat",
                    "status": "success",
                    "response": response_data
                }
                
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            return {
                "test_name": "websocket_chat",
                "status": "error",
                "error": str(e)
            }
            
    async def run_comprehensive_tests(self):
        """Run all chat endpoint tests"""
        print("🚀 Starting Comprehensive Chat Endpoint Tests")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started at: {datetime.now()}")
        
        results = []
        
        # Setup
        await self.setup_session()
        
        # Login
        if not await self.login():
            print("❌ Cannot proceed without login")
            return
            
        # Create session
        if not await self.create_chat_session():
            print("❌ Cannot proceed without chat session")
            return
            
        # Test cases
        test_cases = [
            {
                "message": "What's my current portfolio balance?",
                "name": "Portfolio Balance Query"
            },
            {
                "message": "Show me rebalancing opportunities",
                "name": "Rebalancing Opportunities"
            },
            {
                "message": "Find profitable trading opportunities",
                "name": "Trading Opportunities"
            },
            {
                "message": "Analyze BTC market trends",
                "name": "Market Analysis"
            },
            {
                "message": "What are the current market risks?",
                "name": "Risk Analysis"
            },
            {
                "message": "Help me optimize my portfolio",
                "name": "Portfolio Optimization"
            },
            {
                "message": "Show me my trading history",
                "name": "Trading History"
            },
            {
                "message": "What's the best strategy for ETH?",
                "name": "Strategy Recommendation"
            }
        ]
        
        # Run chat message tests
        for test_case in test_cases:
            result = await self.test_chat_message(
                test_case["message"], 
                test_case["name"]
            )
            results.append(result)
            
            # Small delay between tests
            await asyncio.sleep(2)
            
        # Test WebSocket (if websockets is available)
        try:
            ws_result = await self.test_websocket_chat()
            results.append(ws_result)
        except ImportError:
            print("⚠️ WebSocket test skipped (websockets package not available)")
            
        # Cleanup
        await self.cleanup_session()
        
        # Generate report
        await self.generate_report(results)
        
    async def generate_report(self, results: List[Dict[str, Any]]):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("📊 CHAT ENDPOINTS TEST REPORT")
        print("="*80)
        
        successful_tests = [r for r in results if r.get("status") == "success"]
        failed_tests = [r for r in results if r.get("status") != "success"]
        
        print(f"✅ Successful Tests: {len(successful_tests)}/{len(results)}")
        print(f"❌ Failed Tests: {len(failed_tests)}")
        
        if successful_tests:
            avg_response_time = sum(r.get("response_time", 0) for r in successful_tests) / len(successful_tests)
            print(f"⏱️ Average Response Time: {avg_response_time:.2f}s")
            
        print("\n📋 DETAILED RESULTS:")
        print("-" * 80)
        
        for result in results:
            status_icon = "✅" if result.get("status") == "success" else "❌"
            print(f"{status_icon} {result.get('test_name', 'Unknown Test')}")
            
            if result.get("status") == "success":
                print(f"   ⏱️ Response Time: {result.get('response_time', 0):.2f}s")
                print(f"   🎯 Intent: {result.get('intent', 'N/A')}")
                
                # Show metadata if available
                metadata = result.get("metadata", {})
                if metadata:
                    print(f"   📊 Metadata: {json.dumps(metadata, indent=6)}")
                    
            else:
                print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
                
            print()
            
        # Save detailed results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"💾 Detailed results saved to: {filename}")
        print("="*80)

async def main():
    """Main test execution"""
    tester = ChatEndpointTester()
    await tester.run_comprehensive_tests()

if __name__ == "__main__":
    asyncio.run(main())