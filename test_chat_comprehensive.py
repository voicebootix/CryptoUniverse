#!/usr/bin/env python3
"""
Comprehensive Chat Endpoint Testing

Tests all chat endpoints and WebSocket functionality.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

class ChatTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.session_id = None
        
    def login(self):
        """Login and get access token."""
        print("🔐 Logging in...")
        
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            print(f"✅ Login successful! Token: {self.token[:20]}...")
            return True
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    
    def test_chat_status(self):
        """Test chat status endpoint."""
        print("\n📊 Testing Chat Status...")
        
        response = self.session.get(f"{BASE_URL}/chat/status")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Chat Status Response:")
            print(json.dumps(data, indent=2))
            return data.get("success", False)
        else:
            print(f"❌ Chat Status failed: {response.status_code} - {response.text}")
            return False
    
    def test_create_session(self):
        """Test creating a new chat session."""
        print("\n🆕 Testing Create New Session...")
        
        response = self.session.post(f"{BASE_URL}/chat/session/new")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.session_id = data["session_id"]
                print(f"✅ Session created: {self.session_id}")
                return True
            else:
                print(f"❌ Session creation failed: {data}")
                return False
        else:
            print(f"❌ Session creation failed: {response.status_code} - {response.text}")
            return False
    
    def test_send_message(self, message):
        """Test sending a chat message."""
        print(f"\n💬 Testing Send Message: '{message}'")
        
        if not self.session_id:
            print("❌ No session ID available")
            return False
        
        message_data = {
            "message": message,
            "session_id": self.session_id
        }
        
        response = self.session.post(f"{BASE_URL}/chat/message", json=message_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Message Response:")
            print(f"   Content: {data.get('content', 'No content')}")
            print(f"   Intent: {data.get('intent', 'Unknown')}")
            print(f"   Confidence: {data.get('confidence', 0)}%")
            print(f"   Success: {data.get('success', False)}")
            return data.get("success", False)
        else:
            print(f"❌ Send message failed: {response.status_code} - {response.text}")
            return False
    
    def test_get_history(self):
        """Test getting chat history."""
        print("\n📜 Testing Get Chat History...")
        
        if not self.session_id:
            print("❌ No session ID available")
            return False
        
        response = self.session.get(f"{BASE_URL}/chat/history/{self.session_id}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ History retrieved: {data.get('total_messages', 0)} messages")
            
            # Show last few messages
            messages = data.get('messages', [])
            for msg in messages[-3:]:  # Last 3 messages
                msg_type = msg.get('message_type', 'unknown')
                content = msg.get('content', '')[:100] + '...' if len(msg.get('content', '')) > 100 else msg.get('content', '')
                print(f"   {msg_type}: {content}")
            
            return True
        else:
            print(f"❌ Get history failed: {response.status_code} - {response.text}")
            return False
    
    def test_get_sessions(self):
        """Test getting user sessions."""
        print("\n📋 Testing Get User Sessions...")
        
        response = self.session.get(f"{BASE_URL}/chat/sessions")
        
        if response.status_code == 200:
            data = response.json()
            sessions = data.get('sessions', [])
            print(f"✅ Sessions retrieved: {len(sessions)} active sessions")
            for session in sessions:
                print(f"   Session: {session}")
            return True
        else:
            print(f"❌ Get sessions failed: {response.status_code} - {response.text}")
            return False
    
    def test_quick_portfolio_analysis(self):
        """Test quick portfolio analysis."""
        print("\n📈 Testing Quick Portfolio Analysis...")
        
        response = self.session.post(f"{BASE_URL}/chat/portfolio/quick-analysis")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Portfolio Analysis Response:")
            print(f"   Success: {data.get('success', False)}")
            analysis = data.get('analysis', '')
            if analysis:
                print(f"   Analysis: {analysis[:200]}...")
            return data.get("success", False)
        else:
            print(f"❌ Portfolio analysis failed: {response.status_code} - {response.text}")
            return False
    
    def test_discover_opportunities(self):
        """Test opportunity discovery."""
        print("\n🔍 Testing Discover Opportunities...")
        
        response = self.session.post(f"{BASE_URL}/chat/market/opportunities?risk_tolerance=balanced")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Opportunities Response:")
            print(f"   Success: {data.get('success', False)}")
            opportunities = data.get('opportunities', '')
            if opportunities:
                print(f"   Opportunities: {opportunities[:200]}...")
            return data.get("success", False)
        else:
            print(f"❌ Discover opportunities failed: {response.status_code} - {response.text}")
            return False
    
    def run_all_tests(self):
        """Run all chat tests."""
        print("🚀 Starting Comprehensive Chat Tests")
        print("=" * 50)
        
        results = {}
        
        # Login first
        if not self.login():
            print("❌ Cannot proceed without login")
            return results
        
        # Test all endpoints
        results["chat_status"] = self.test_chat_status()
        results["create_session"] = self.test_create_session()
        
        # Test messaging (multiple messages)
        test_messages = [
            "Hello! How are you?",
            "What is Bitcoin's current price?",
            "Can you analyze my portfolio?",
            "What are the best trading opportunities today?"
        ]
        
        message_results = []
        for msg in test_messages:
            message_results.append(self.test_send_message(msg))
            time.sleep(1)  # Small delay between messages
        
        results["send_messages"] = all(message_results)
        
        results["get_history"] = self.test_get_history()
        results["get_sessions"] = self.test_get_sessions()
        results["portfolio_analysis"] = self.test_quick_portfolio_analysis()
        results["discover_opportunities"] = self.test_discover_opportunities()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:25} {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed!")
        elif passed_tests > total_tests / 2:
            print("⚠️ Most tests passed - some issues to investigate")
        else:
            print("❌ Many tests failed - significant issues detected")
        
        return results

if __name__ == "__main__":
    tester = ChatTester()
    results = tester.run_all_tests()