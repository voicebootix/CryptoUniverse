#!/usr/bin/env python3
"""
Simple Synchronous Chat Endpoints Testing
Tests all chat functionality on live deployment using requests
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# Live deployment URL
BASE_URL = "https://cryptouniverse.onrender.com"

class SimpleChatTester:
    def __init__(self):
        self.auth_token = None
        self.session_id = None
        
    def login(self) -> bool:
        """Login and get auth token"""
        try:
            login_data = {
                "email": "admin@cryptouniverse.com",
                "password": "AdminPass123!"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                print(f"✅ Login successful, token: {self.auth_token[:20]}...")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
            
    def create_chat_session(self) -> bool:
        """Create a new chat session"""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/session/new",
                headers=headers,
                json={},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get("session_id")
                print(f"✅ Chat session created: {self.session_id}")
                return True
            else:
                print(f"❌ Session creation failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Session creation error: {e}")
            return False
            
    def test_chat_message(self, message: str, test_name: str) -> Dict[str, Any]:
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
            
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/message",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 200:
                data = response.json()
                
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
                
                # Show key metadata
                metadata = data.get("metadata", {})
                if metadata:
                    if "portfolio_balance" in metadata:
                        print(f"💰 Portfolio Balance: ${metadata['portfolio_balance']}")
                    if "opportunities_found" in metadata:
                        print(f"🎯 Opportunities Found: {metadata['opportunities_found']}")
                    if "analysis_type" in metadata:
                        print(f"📊 Analysis Type: {metadata['analysis_type']}")
                
                return result
            else:
                result = {
                    "test_name": test_name,
                    "status": "failed",
                    "response_time": response_time,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "raw_response": response.text
                }
                
                print(f"❌ Failed ({response_time:.2f}s): {response.status_code} - {response.text}")
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
            
    def test_chat_sessions_list(self) -> Dict[str, Any]:
        """Test listing chat sessions"""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            print(f"\n🔄 Testing: List Chat Sessions")
            
            response = requests.get(
                f"{BASE_URL}/api/v1/chat/sessions",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                sessions_count = len(data) if isinstance(data, list) else 0
                
                print(f"✅ Success - Found {sessions_count} sessions")
                
                return {
                    "test_name": "list_sessions",
                    "status": "success",
                    "sessions_count": sessions_count,
                    "raw_response": data
                }
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                return {
                    "test_name": "list_sessions",
                    "status": "failed",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                "test_name": "list_sessions",
                "status": "error",
                "error": str(e)
            }
            
    def test_session_messages(self) -> Dict[str, Any]:
        """Test getting session messages"""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            print(f"\n🔄 Testing: Get Session Messages")
            
            response = requests.get(
                f"{BASE_URL}/api/v1/chat/history/{self.session_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                messages_count = len(data) if isinstance(data, list) else 0
                
                print(f"✅ Success - Found {messages_count} messages")
                
                return {
                    "test_name": "session_messages",
                    "status": "success",
                    "messages_count": messages_count,
                    "raw_response": data
                }
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                return {
                    "test_name": "session_messages",
                    "status": "failed",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                "test_name": "session_messages",
                "status": "error",
                "error": str(e)
            }
            
    def run_comprehensive_tests(self):
        """Run all chat endpoint tests"""
        print("🚀 Starting Comprehensive Chat Endpoint Tests")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started at: {datetime.now()}")
        
        results = []
        
        # Login
        if not self.login():
            print("❌ Cannot proceed without login")
            return
            
        # Create session
        if not self.create_chat_session():
            print("❌ Cannot proceed without chat session")
            return
            
        # Test session listing
        list_result = self.test_chat_sessions_list()
        results.append(list_result)
        
        # Test cases for chat messages
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
            result = self.test_chat_message(
                test_case["message"], 
                test_case["name"]
            )
            results.append(result)
            
            # Small delay between tests
            time.sleep(2)
            
        # Test getting session messages
        messages_result = self.test_session_messages()
        results.append(messages_result)
        
        # Generate report
        self.generate_report(results)
        
    def generate_report(self, results: List[Dict[str, Any]]):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("📊 CHAT ENDPOINTS TEST REPORT")
        print("="*80)
        
        successful_tests = [r for r in results if r.get("status") == "success"]
        failed_tests = [r for r in results if r.get("status") != "success"]
        
        print(f"✅ Successful Tests: {len(successful_tests)}/{len(results)}")
        print(f"❌ Failed Tests: {len(failed_tests)}")
        
        if successful_tests:
            chat_tests = [r for r in successful_tests if "response_time" in r]
            if chat_tests:
                avg_response_time = sum(r.get("response_time", 0) for r in chat_tests) / len(chat_tests)
                print(f"⏱️ Average Response Time: {avg_response_time:.2f}s")
            
        print("\n📋 DETAILED RESULTS:")
        print("-" * 80)
        
        for result in results:
            status_icon = "✅" if result.get("status") == "success" else "❌"
            print(f"{status_icon} {result.get('test_name', 'Unknown Test')}")
            
            if result.get("status") == "success":
                if "response_time" in result:
                    print(f"   ⏱️ Response Time: {result.get('response_time', 0):.2f}s")
                if "intent" in result:
                    print(f"   🎯 Intent: {result.get('intent', 'N/A')}")
                if "sessions_count" in result:
                    print(f"   📊 Sessions Count: {result.get('sessions_count', 0)}")
                if "messages_count" in result:
                    print(f"   💬 Messages Count: {result.get('messages_count', 0)}")
                    
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

def main():
    """Main test execution"""
    tester = SimpleChatTester()
    tester.run_comprehensive_tests()

if __name__ == "__main__":
    main()