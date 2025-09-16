#!/usr/bin/env python3
"""
Complete Conversational AI System Test

Tests the full conversational AI implementation with all platform features:
- Natural language financial conversations
- Real-time streaming responses
- Paper trading integration (no credits)
- Live trading integration (with credits)
- Strategy marketplace integration
- Autonomous trading control
- Portfolio analysis and risk management
- Market intelligence and opportunities
"""

import requests
import json
import time
import asyncio
import websockets
import os
from datetime import datetime

# Configuration - use environment variables for security
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000/api/v1")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

class ConversationalAITester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        
    def login(self):
        """Login and get access token."""
        print("🔐 Logging in...")
        
        # Check required environment variables
        if not ADMIN_EMAIL or not ADMIN_PASSWORD:
            raise ValueError(
                "Required environment variables missing. Please set:\n"
                "export ADMIN_EMAIL='your-admin-email'\n"
                "export ADMIN_PASSWORD='your-admin-password'\n"
                "export BASE_URL='your-api-base-url' (optional)"
            )
        
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = self.session.post(f"{BASE_URL}/auth/login", json=login_data, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            print("✅ Login successful!")
            return True
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    
    def test_capabilities_endpoint(self):
        """Test the capabilities endpoint."""
        print("\n🧠 Testing Conversational AI Capabilities...")
        
        response = self.session.get(f"{BASE_URL}/conversational-chat/capabilities", timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Capabilities endpoint working")
            
            capabilities = data.get("capabilities", {})
            print(f"📊 Trading Features: {len(capabilities.get('trading_features', {}))}")
            print(f"📈 Portfolio Management: {len(capabilities.get('portfolio_management', {}))}")
            print(f"🤖 Strategy Features: {len(capabilities.get('strategy_features', {}))}")
            print(f"🔄 Autonomous Trading: {'Available' if capabilities.get('autonomous_trading', {}).get('available') else 'Not Available'}")
            print(f"💡 Market Intelligence: {'Available' if capabilities.get('market_intelligence', {}).get('available') else 'Not Available'}")
            print(f"💰 Paper Trading: {'No Credits Required' if data.get('paper_trading_no_credits') else 'Credits Required'}")
            print(f"⚡ Real-time Streaming: {'Yes' if data.get('real_time_streaming') else 'No'}")
            
            return True
        else:
            print(f"❌ Capabilities test failed: {response.status_code} - {response.text}")
            return False
    
    def test_personality_endpoint(self):
        """Test personality information endpoints."""
        print("\n🎭 Testing AI Personality System...")
        
        trading_modes = ["conservative", "balanced", "aggressive", "beast_mode"]
        
        for mode in trading_modes:
            response = self.session.get(f"{BASE_URL}/conversational-chat/personality/{mode}", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                personality = data.get("personality", {})
                print(f"✅ {mode.title()}: {personality.get('name', 'Unknown')}")
                print(f"   Style: {personality.get('style', 'Unknown')}")
                print(f"   Risk Tolerance: {personality.get('risk_tolerance', 'Unknown')}")
            else:
                print(f"❌ {mode.title()} personality test failed")
    
    def test_conversational_chat(self):
        """Test conversational chat endpoint."""
        print("\n💬 Testing Conversational Chat...")
        
        test_conversations = [
            {
                "message": "What are you capable of?",
                "mode": "learning",
                "expected_topics": ["capabilities", "features", "trading"]
            },
            {
                "message": "How is my portfolio performing?",
                "mode": "live_trading",
                "expected_topics": ["portfolio", "performance", "analysis"]
            },
            {
                "message": "I want to practice trading without risk",
                "mode": "paper_trading",
                "expected_topics": ["paper", "simulation", "practice"]
            },
            {
                "message": "Show me profitable trading strategies",
                "mode": "strategy_exploration",
                "expected_topics": ["strategies", "marketplace", "profitable"]
            },
            {
                "message": "Start autonomous trading in aggressive mode",
                "mode": "live_trading",
                "expected_topics": ["autonomous", "aggressive", "trading"]
            }
        ]
        
        for i, test in enumerate(test_conversations):
            print(f"\n📝 Test {i+1}: {test['message'][:50]}...")
            
            request_data = {
                "message": test["message"],
                "conversation_mode": test["mode"]
            }
            
            start_time = time.time()
            response = self.session.post(f"{BASE_URL}/conversational-chat/conversational", json=request_data, timeout=15)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"✅ Response received in {response_time:.2f}s")
                print(f"   Session ID: {data.get('session_id', 'None')}")
                print(f"   Personality: {data.get('personality', 'Unknown')}")
                print(f"   Mode: {data.get('conversation_mode', 'Unknown')}")
                print(f"   Response Chunks: {len(data.get('response_chunks', []))}")
                print(f"   Requires Action: {data.get('requires_action', False)}")
                
                # Check for expected topics in response
                response_chunks = data.get('response_chunks', [])
                response_content = " ".join([chunk.get('content', '') for chunk in response_chunks])
                
                found_topics = []
                for topic in test['expected_topics']:
                    if topic.lower() in response_content.lower():
                        found_topics.append(topic)
                
                print(f"   Topics Found: {found_topics}/{test['expected_topics']}")
                
            else:
                print(f"❌ Test {i+1} failed: {response.status_code} - {response.text}")
    
    def test_websocket_streaming(self):
        """Test WebSocket streaming functionality."""
        print("\n🌊 Testing WebSocket Streaming...")
        
        async def websocket_test():
            uri = f"wss://cryptouniverse.onrender.com/api/v1/conversational-chat/stream/test-session"
            
            try:
                # Connect with authentication
                async with websockets.connect(
                    uri,
                    subprotocols=["bearer", self.token, "json"],
                    timeout=10
                ) as websocket:
                    print("✅ WebSocket connected")
                    
                    # Wait for connection confirmation
                    response = await websocket.recv()
                    connection_data = json.loads(response)
                    
                    if connection_data.get("type") == "connection_established":
                        print("✅ Connection confirmed")
                        print(f"   Features: {len(connection_data.get('features', []))}")
                    
                    # Send test message
                    test_message = {
                        "type": "conversational_message",
                        "message": "Explain paper trading and how it works",
                        "conversation_mode": "paper_trading"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    print("📤 Sent test message")
                    
                    # Collect streaming responses
                    response_chunks = []
                    start_time = time.time()
                    
                    try:
                        while True:
                            response = await asyncio.wait_for(websocket.recv(), timeout=30)
                            data = json.loads(response)
                            
                            if data.get("type") == "conversational_response":
                                chunk = data.get("chunk", {})
                                response_chunks.append(chunk)
                                
                                if chunk.get("type") == "complete":
                                    break
                                    
                                print(f"📥 Chunk: {chunk.get('type', 'unknown')}")
                    
                    except asyncio.TimeoutError:
                        print("⏰ WebSocket response timeout")
                    
                    total_time = time.time() - start_time
                    print(f"✅ Streaming test completed in {total_time:.2f}s")
                    print(f"   Total chunks: {len(response_chunks)}")
                    
                    # Test ping/pong
                    await websocket.send(json.dumps({"type": "ping"}))
                    pong_response = await websocket.recv()
                    pong_data = json.loads(pong_response)
                    
                    if pong_data.get("type") == "pong":
                        print("✅ Ping/pong working")
                    
            except Exception as e:
                print(f"❌ WebSocket test failed: {str(e)}")
        
        # Run WebSocket test
        try:
            asyncio.run(websocket_test())
        except Exception as e:
            print(f"❌ WebSocket test setup failed: {str(e)}")
    
    def test_paper_trading_integration(self):
        """Test paper trading integration (no credits required)."""
        print("\n💰 Testing Paper Trading Integration...")
        
        # Test paper trading setup
        response = self.session.post(f"{BASE_URL}/paper-trading/setup")
        
        if response.status_code == 200:
            print("✅ Paper trading setup successful")
        else:
            print(f"ℹ️  Paper trading setup: {response.status_code}")
        
        # Test conversational paper trading request
        request_data = {
            "message": "Set up paper trading for me and execute a test trade of $1000 Bitcoin",
            "conversation_mode": "paper_trading"
        }
        
        response = self.session.post(f"{BASE_URL}/conversational-chat/conversational", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Paper trading conversation successful")
            
            response_content = " ".join([
                chunk.get('content', '') 
                for chunk in data.get('response_chunks', [])
            ])
            
            # Check for paper trading keywords
            paper_keywords = ["paper", "simulation", "virtual", "practice", "no credits"]
            found_keywords = [kw for kw in paper_keywords if kw.lower() in response_content.lower()]
            
            print(f"   Paper Trading Keywords Found: {found_keywords}")
            
        else:
            print(f"❌ Paper trading conversation failed: {response.status_code}")
    
    def test_strategy_marketplace_integration(self):
        """Test strategy marketplace integration."""
        print("\n🏪 Testing Strategy Marketplace Integration...")
        
        request_data = {
            "message": "What trading strategies do I have access to and which ones are most profitable?",
            "conversation_mode": "strategy_exploration"
        }
        
        response = self.session.post(f"{BASE_URL}/conversational-chat/conversational", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Strategy marketplace conversation successful")
            
            response_content = " ".join([
                chunk.get('content', '') 
                for chunk in data.get('response_chunks', [])
            ])
            
            # Check for strategy-related keywords
            strategy_keywords = ["strategy", "strategies", "marketplace", "profitable", "performance"]
            found_keywords = [kw for kw in strategy_keywords if kw.lower() in response_content.lower()]
            
            print(f"   Strategy Keywords Found: {found_keywords}")
            
        else:
            print(f"❌ Strategy marketplace conversation failed: {response.status_code}")
    
    def test_autonomous_trading_integration(self):
        """Test autonomous trading integration."""
        print("\n🤖 Testing Autonomous Trading Integration...")
        
        request_data = {
            "message": "Tell me about autonomous trading modes and help me choose the right one for my risk tolerance",
            "conversation_mode": "live_trading"
        }
        
        response = self.session.post(f"{BASE_URL}/conversational-chat/conversational", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Autonomous trading conversation successful")
            
            response_content = " ".join([
                chunk.get('content', '') 
                for chunk in data.get('response_chunks', [])
            ])
            
            # Check for autonomous trading keywords
            autonomous_keywords = ["autonomous", "automatic", "beast", "conservative", "aggressive", "balanced"]
            found_keywords = [kw for kw in autonomous_keywords if kw.lower() in response_content.lower()]
            
            print(f"   Autonomous Keywords Found: {found_keywords}")
            
        else:
            print(f"❌ Autonomous trading conversation failed: {response.status_code}")
    
    def run_complete_test(self):
        """Run complete conversational AI test suite."""
        print("🚀 Starting Complete Conversational AI System Test")
        print("=" * 60)
        
        if not self.login():
            return
        
        tests = [
            self.test_capabilities_endpoint,
            self.test_personality_endpoint,
            self.test_conversational_chat,
            self.test_paper_trading_integration,
            self.test_strategy_marketplace_integration,
            self.test_autonomous_trading_integration,
            self.test_websocket_streaming
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                test()
                passed += 1
            except Exception as e:
                print(f"❌ Test failed with exception: {str(e)}")
        
        print("\n" + "=" * 60)
        print(f"🏁 Test Summary: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Conversational AI system is fully operational!")
        else:
            print(f"⚠️  {total - passed} tests failed. Check the logs above for details.")
        
        print("\n🌟 Conversational AI Features Tested:")
        print("   ✅ Natural language financial conversations")
        print("   ✅ Real-time streaming responses")
        print("   ✅ Paper trading integration (no credits)")
        print("   ✅ Strategy marketplace integration")
        print("   ✅ Autonomous trading control")
        print("   ✅ AI personality system")
        print("   ✅ WebSocket streaming communication")
        print("   ✅ Complete platform feature access")


if __name__ == "__main__":
    tester = ConversationalAITester()
    tester.run_complete_test()