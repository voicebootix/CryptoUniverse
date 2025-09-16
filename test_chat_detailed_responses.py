#!/usr/bin/env python3
"""
Detailed Chat Response Analysis
Tests chat endpoints and shows full response content and metadata
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# Live deployment URL
BASE_URL = "https://cryptouniverse.onrender.com"

class DetailedChatTester:
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
                print(f"✅ Login successful")
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
            
    def test_detailed_message(self, message: str, test_name: str):
        """Send a chat message and show detailed response"""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "message": message,
                "session_id": self.session_id
            }
            
            print(f"\n{'='*80}")
            print(f"🔄 TESTING: {test_name}")
            print(f"📤 MESSAGE: {message}")
            print(f"{'='*80}")
            
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
                
                print(f"✅ SUCCESS ({response_time:.2f}s)")
                print(f"\n📥 FULL RESPONSE:")
                print(f"   Intent: {data.get('intent', 'N/A')}")
                print(f"   Confidence: {data.get('confidence', 0):.2f}")
                print(f"   Requires Approval: {data.get('requires_approval', False)}")
                print(f"   Message ID: {data.get('message_id', 'N/A')}")
                
                # Show metadata in detail
                metadata = data.get('metadata', {})
                if metadata:
                    print(f"\n📊 METADATA:")
                    for key, value in metadata.items():
                        if isinstance(value, dict):
                            print(f"   {key}:")
                            for sub_key, sub_value in value.items():
                                print(f"     {sub_key}: {sub_value}")
                        elif isinstance(value, list):
                            print(f"   {key}: [{len(value)} items]")
                            for i, item in enumerate(value[:3]):  # Show first 3 items
                                print(f"     [{i}]: {item}")
                            if len(value) > 3:
                                print(f"     ... and {len(value) - 3} more")
                        else:
                            print(f"   {key}: {value}")
                
                # Show AI analysis if available
                ai_analysis = data.get('ai_analysis')
                if ai_analysis:
                    print(f"\n🤖 AI ANALYSIS:")
                    print(f"   {ai_analysis}")
                
                # Show response content (truncated)
                content = data.get('content', '')
                print(f"\n💬 RESPONSE CONTENT:")
                if len(content) > 500:
                    print(f"   {content[:500]}...")
                    print(f"   [Content truncated - Total length: {len(content)} chars]")
                else:
                    print(f"   {content}")
                
                return True
            else:
                print(f"❌ FAILED ({response_time:.2f}s): {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False
            
    def test_quick_endpoints(self):
        """Test the quick analysis endpoints"""
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        print(f"\n{'='*80}")
        print(f"🔄 TESTING: Quick Portfolio Analysis Endpoint")
        print(f"{'='*80}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/portfolio/quick-analysis",
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS")
                print(f"   Analysis: {data.get('analysis', '')[:200]}...")
                print(f"   Confidence: {data.get('confidence', 0):.2f}")
                
                metadata = data.get('metadata', {})
                if metadata:
                    print(f"   Metadata keys: {list(metadata.keys())}")
            else:
                print(f"❌ FAILED: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            
        print(f"\n{'='*80}")
        print(f"🔄 TESTING: Market Opportunities Endpoint")
        print(f"{'='*80}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/market/opportunities",
                headers=headers,
                json={"risk_tolerance": "balanced"},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS")
                print(f"   Opportunities: {data.get('opportunities', '')[:200]}...")
                print(f"   Confidence: {data.get('confidence', 0):.2f}")
                
                metadata = data.get('metadata', {})
                if metadata:
                    print(f"   Metadata keys: {list(metadata.keys())}")
            else:
                print(f"❌ FAILED: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            
    def run_detailed_tests(self):
        """Run detailed chat tests"""
        print("🚀 Starting Detailed Chat Response Analysis")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started at: {datetime.now()}")
        
        # Login
        if not self.login():
            print("❌ Cannot proceed without login")
            return
            
        # Create session
        if not self.create_chat_session():
            print("❌ Cannot proceed without chat session")
            return
            
        # Test specific high-value scenarios
        test_cases = [
            {
                "message": "What's my current portfolio balance and performance?",
                "name": "Portfolio Balance & Performance"
            },
            {
                "message": "Show me the best rebalancing opportunities right now",
                "name": "Rebalancing Opportunities"
            },
            {
                "message": "Find me profitable trading opportunities with detailed analysis",
                "name": "Trading Opportunities Discovery"
            }
        ]
        
        # Run detailed message tests
        for test_case in test_cases:
            success = self.test_detailed_message(
                test_case["message"], 
                test_case["name"]
            )
            
            if success:
                # Small delay between tests
                time.sleep(3)
            else:
                print("⚠️ Skipping remaining tests due to failure")
                break
                
        # Test quick endpoints
        self.test_quick_endpoints()
        
        print(f"\n{'='*80}")
        print("📊 DETAILED ANALYSIS COMPLETE")
        print(f"⏰ Completed at: {datetime.now()}")
        print(f"{'='*80}")

def main():
    """Main test execution"""
    tester = DetailedChatTester()
    tester.run_detailed_tests()

if __name__ == "__main__":
    main()