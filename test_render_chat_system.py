#!/usr/bin/env python3
"""
RENDER CHAT SYSTEM TESTING
Tests chat endpoints on cryptouniverse.onrender.com to verify recent fixes
"""

import requests
import json
import time
import asyncio
import websockets
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
WS_URL = "wss://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
import os

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "AdminPass123!")

class RenderChatTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 45  # Longer timeout for Render
        self.token = None
        self.session_id = None
        self.test_results = {
            "authentication": {},
            "chat_endpoints": {},
            "chat_functionality": {},
            "ai_responses": {},
            "trading_integration": {},
            "performance": {}
        }
        
    def log_test(self, category: str, test_name: str, success: bool, details: Dict[str, Any] = None):
        """Log test results with enhanced formatting"""
        if category not in self.test_results:
            self.test_results[category] = {}
        
        self.test_results[category][test_name] = {
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        status = "✅" if success else "❌"
        print(f"{status} {category.upper()}: {test_name}")
        if details:
            if success:
                # Show key success metrics
                if "response_time" in details:
                    print(f"   ⏱️  Response Time: {details['response_time']:.2f}s")
                if "message" in details:
                    print(f"   💬 Response: {details['message'][:100]}...")
            else:
                print(f"   ❌ Error: {details.get('error', 'Unknown error')}")
                if "status_code" in details:
                    print(f"   🔍 Status: {details['status_code']}")
    
    def authenticate(self):
        """Test authentication with admin credentials"""
        print("\n🔐 Testing Authentication...")
        
        login_data = {
            "username": ADMIN_EMAIL,  # Using form data format
            "password": ADMIN_PASSWORD
        }
        
        try:
            start_time = time.time()
            response = self.session.post(
                f"{BASE_URL}/auth/login", 
                data=login_data,  # Using form data
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                    self.log_test("authentication", "admin_login", True, {
                        "response_time": response_time,
                        "token_length": len(self.token),
                        "user_email": data.get("user", {}).get("email", "unknown")
                    })
                    return True
                else:
                    self.log_test("authentication", "admin_login", False, {
                        "response_time": response_time,
                        "error": "No access token in response",
                        "response_data": data
                    })
            else:
                self.log_test("authentication", "admin_login", False, {
                    "response_time": response_time,
                    "status_code": response.status_code,
                    "error": response.text[:200]
                })
        except Exception as e:
            self.log_test("authentication", "admin_login", False, {"error": str(e)})
            
        return False
    
    def test_chat_endpoints(self):
        """Test all chat REST endpoints"""
        print("\n📡 Testing Chat Endpoints...")
        
        endpoints_to_test = [
            ("chat_status", "GET", "/chat/status", None),
            ("create_session", "POST", "/chat/session/new", {}),
            ("get_sessions", "GET", "/chat/sessions", None),
            ("quick_portfolio_analysis", "POST", "/chat/portfolio/quick-analysis", {}),
            ("market_opportunities", "POST", "/chat/market/opportunities", {"risk_tolerance": "balanced"}),
        ]
        
        for test_name, method, endpoint, payload in endpoints_to_test:
            try:
                start_time = time.time()
                
                if method == "GET":
                    response = self.session.get(f"{BASE_URL}{endpoint}")
                else:
                    response = self.session.post(f"{BASE_URL}{endpoint}", json=payload)
                
                response_time = time.time() - start_time
                success = response.status_code == 200
                
                if success:
                    data = response.json()
                    self.log_test("chat_endpoints", test_name, True, {
                        "response_time": response_time,
                        "status_code": response.status_code,
                        "data_keys": list(data.keys()) if isinstance(data, dict) else "non-dict response"
                    })
                    
                    # Store session ID if created
                    if test_name == "create_session" and data.get("session_id"):
                        self.session_id = data["session_id"]
                        
                else:
                    self.log_test("chat_endpoints", test_name, False, {
                        "response_time": response_time,
                        "status_code": response.status_code,
                        "error": response.text[:200]
                    })
                    
            except Exception as e:
                self.log_test("chat_endpoints", test_name, False, {"error": str(e)})
    
    def test_chat_messaging(self):
        """Test chat message functionality"""
        print("\n💬 Testing Chat Messaging...")
        
        test_messages = [
            ("basic_greeting", "Hello, how are you?"),
            ("portfolio_question", "What is my current portfolio balance?"),
            ("market_analysis", "Can you analyze Bitcoin's current market conditions?"),
            ("trading_inquiry", "What trading opportunities do you recommend?"),
            ("strategy_question", "What trading strategies are available?")
        ]
        
        for test_name, message in test_messages:
            try:
                start_time = time.time()
                
                payload = {
                    "message": message,
                    "session_id": self.session_id
                }
                
                response = self.session.post(f"{BASE_URL}/chat/message", json=payload)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    ai_response = data.get("response", "")
                    
                    # Analyze response quality
                    quality_indicators = {
                        "has_response": bool(ai_response),
                        "response_length": len(ai_response),
                        "contains_data": "data" in ai_response.lower() or "analysis" in ai_response.lower(),
                        "is_helpful": len(ai_response) > 50 and not "error" in ai_response.lower()
                    }
                    
                    self.log_test("chat_functionality", test_name, True, {
                        "response_time": response_time,
                        "message": ai_response[:150],
                        "quality_score": sum(quality_indicators.values()),
                        "quality_indicators": quality_indicators
                    })
                else:
                    self.log_test("chat_functionality", test_name, False, {
                        "response_time": response_time,
                        "status_code": response.status_code,
                        "error": response.text[:200]
                    })
                    
            except Exception as e:
                self.log_test("chat_functionality", test_name, False, {"error": str(e)})
    
    def test_admin_features(self):
        """Test admin-specific chat features"""
        print("\n👑 Testing Admin Features...")
        
        admin_tests = [
            ("admin_strategy_list", "POST", "/admin/testing/strategy/list-all", {}),
            ("admin_strategy_test", "POST", "/admin/testing/strategy/execute", {
                "function": "portfolio_optimization",
                "symbol": "BTC/USDT",
                "parameters": {}
            })
        ]
        
        for test_name, method, endpoint, payload in admin_tests:
            try:
                start_time = time.time()
                response = self.session.post(f"{BASE_URL}{endpoint}", json=payload)
                response_time = time.time() - start_time
                
                success = response.status_code == 200
                
                if success:
                    data = response.json()
                    self.log_test("admin_features", test_name, True, {
                        "response_time": response_time,
                        "admin_access": data.get("admin_access", False),
                        "function_count": data.get("total_functions", 0) if "list" in test_name else None
                    })
                else:
                    self.log_test("admin_features", test_name, False, {
                        "response_time": response_time,
                        "status_code": response.status_code,
                        "error": response.text[:200]
                    })
                    
            except Exception as e:
                self.log_test("admin_features", test_name, False, {"error": str(e)})
    
    def run_comprehensive_test(self):
        """Run all tests and generate report"""
        print("🚀 STARTING RENDER CHAT SYSTEM TEST")
        print("=" * 60)
        print(f"🌐 Target: {BASE_URL}")
        print(f"👤 Admin User: {ADMIN_EMAIL}")
        print(f"🕐 Test Started: {datetime.now().isoformat()}")
        print("=" * 60)
        
        # Run test sequence
        if self.authenticate():
            self.test_chat_endpoints()
            self.test_chat_messaging()
            self.test_admin_features()
        else:
            print("❌ Authentication failed - skipping other tests")
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate comprehensive test summary"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 60)
        
        total_tests = 0
        successful_tests = 0
        total_response_time = 0
        
        for category, tests in self.test_results.items():
            if not tests:
                continue
                
            print(f"\n📂 {category.upper()}:")
            category_success = 0
            category_total = 0
            
            for test_name, result in tests.items():
                total_tests += 1
                category_total += 1
                
                if result["success"]:
                    successful_tests += 1
                    category_success += 1
                    print(f"  ✅ {test_name}")
                else:
                    print(f"  ❌ {test_name}")
                
                # Track response times
                if "details" in result and "response_time" in result["details"]:
                    total_response_time += result["details"]["response_time"]
            
            success_rate = (category_success / category_total * 100) if category_total > 0 else 0
            print(f"  📊 Category Success Rate: {success_rate:.1f}% ({category_success}/{category_total})")
        
        # Overall metrics
        overall_success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        avg_response_time = (total_response_time / total_tests) if total_tests > 0 else 0
        
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"  📊 Success Rate: {overall_success_rate:.1f}% ({successful_tests}/{total_tests})")
        print(f"  ⏱️  Average Response Time: {avg_response_time:.2f}s")
        print(f"  🕐 Test Completed: {datetime.now().isoformat()}")
        
        # Save detailed results
        report_filename = f"render_chat_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump({
                "test_summary": {
                    "timestamp": datetime.now().isoformat(),
                    "base_url": BASE_URL,
                    "admin_user": ADMIN_EMAIL,
                    "overall_success_rate": overall_success_rate,
                    "total_tests": total_tests,
                    "successful_tests": successful_tests,
                    "average_response_time": avg_response_time
                },
                "detailed_results": self.test_results
            }, f, indent=2)
        
        print(f"\n💾 Detailed report saved: {report_filename}")
        
        # Assessment of fixes
        self.assess_chat_fixes(overall_success_rate, successful_tests, total_tests)
    
    def assess_chat_fixes(self, success_rate: float, successful: int, total: int):
        """Assess if recent fixes resolved chat issues"""
        print(f"\n🔍 ASSESSMENT: Did merge 77396f2 fix the chat issues?")
        print("-" * 50)
        
        if success_rate >= 80:
            print("✅ EXCELLENT: Chat system appears to be working well!")
            print("   - High success rate indicates fixes were effective")
            print("   - Admin features are properly integrated")
        elif success_rate >= 60:
            print("🟡 GOOD: Chat system is mostly working with some issues")
            print("   - Most core functionality is operational")
            print("   - Some endpoints may need attention")
        elif success_rate >= 40:
            print("🟠 NEEDS IMPROVEMENT: Chat system has significant issues")
            print("   - Core functionality partially working")
            print("   - Multiple endpoints failing")
        else:
            print("🔴 CRITICAL: Chat system has major problems")
            print("   - Most functionality is not working")
            print("   - Requires immediate attention")
        
        # Specific recommendations
        print(f"\n📝 RECOMMENDATIONS:")
        if successful < total:
            print(f"   - Investigate {total - successful} failing tests")
            print(f"   - Check server logs for error details")
            print(f"   - Verify environment variables are set correctly")
        
        if success_rate < 100:
            print(f"   - Consider additional testing of failing endpoints")
            print(f"   - Review merge 77396f2 changes for any missed configurations")

if __name__ == "__main__":
    tester = RenderChatTester()
    tester.run_comprehensive_test()