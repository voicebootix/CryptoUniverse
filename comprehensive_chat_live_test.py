#!/usr/bin/env python3
"""
Comprehensive Live Chat System Testing
Tests all chat endpoints and features against cryptouniverse.onrender.com
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
ADMIN_PASSWORD = "AdminPass123!"

class ComprehensiveChatTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 30  # 30 second timeout
        self.token = None
        self.session_id = None
        self.test_results = {
            "authentication": {},
            "endpoints": {},
            "natural_language": {},
            "trading_features": {},
            "portfolio_features": {},
            "opportunity_discovery": {},
            "intent_classification": {},
            "performance": {}
        }
        
    def log_test(self, category: str, test_name: str, success: bool, details: Dict[str, Any] = None):
        """Log test results"""
        if category not in self.test_results:
            self.test_results[category] = {}
        
        self.test_results[category][test_name] = {
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        status = "✅" if success else "❌"
        print(f"{status} {category.upper()}: {test_name}")
        if details and not success:
            print(f"   Error: {details.get('error', 'Unknown error')}")
    
    def test_authentication(self):
        """Test login and authentication"""
        print("\n🔐 Testing Authentication...")
        
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                    self.log_test("authentication", "login", True, {
                        "token_length": len(self.token),
                        "user_data": data.get("user", {})
                    })
                    return True
                else:
                    self.log_test("authentication", "login", False, {"error": "No access token in response"})
            else:
                self.log_test("authentication", "login", False, {
                    "status_code": response.status_code,
                    "error": response.text
                })
        except Exception as e:
            self.log_test("authentication", "login", False, {"error": str(e)})
            
        return False
    
    def test_chat_endpoints(self):
        """Test all chat REST endpoints"""
        print("\n📡 Testing Chat Endpoints...")
        
        # Test 1: Chat Status
        try:
            response = self.session.get(f"{BASE_URL}/chat/status")
            success = response.status_code == 200
            details = response.json() if success else {"status_code": response.status_code, "error": response.text}
            self.log_test("endpoints", "chat_status", success, details)
        except Exception as e:
            self.log_test("endpoints", "chat_status", False, {"error": str(e)})
        
        # Test 2: Create New Session
        try:
            response = self.session.post(f"{BASE_URL}/chat/session/new")
            success = response.status_code == 200
            if success:
                data = response.json()
                self.session_id = data.get("session_id")
                details = {"session_id": self.session_id, "success_flag": data.get("success")}
            else:
                details = {"status_code": response.status_code, "error": response.text}
            self.log_test("endpoints", "create_session", success, details)
        except Exception as e:
            self.log_test("endpoints", "create_session", False, {"error": str(e)})
        
        # Test 3: Get User Sessions
        try:
            response = self.session.get(f"{BASE_URL}/chat/sessions")
            success = response.status_code == 200
            details = response.json() if success else {"status_code": response.status_code, "error": response.text}
            self.log_test("endpoints", "get_sessions", success, details)
        except Exception as e:
            self.log_test("endpoints", "get_sessions", False, {"error": str(e)})
        
        # Test 4: Quick Portfolio Analysis
        try:
            response = self.session.post(f"{BASE_URL}/chat/portfolio/quick-analysis")
            success = response.status_code == 200
            details = response.json() if success else {"status_code": response.status_code, "error": response.text}
            self.log_test("endpoints", "quick_portfolio_analysis", success, details)
        except Exception as e:
            self.log_test("endpoints", "quick_portfolio_analysis", False, {"error": str(e)})
        
        # Test 5: Market Opportunities
        try:
            response = self.session.post(f"{BASE_URL}/chat/market/opportunities", json={"risk_tolerance": "balanced"})
            success = response.status_code == 200
            details = response.json() if success else {"status_code": response.status_code, "error": response.text}
            self.log_test("endpoints", "market_opportunities", success, details)
        except Exception as e:
            self.log_test("endpoints", "market_opportunities", False, {"error": str(e)})
    
    def test_natural_language_processing(self):
        """Test natural language processing and intent classification"""
        print("\n🧠 Testing Natural Language Processing...")
        
        test_messages = [
            {
                "message": "Show me my portfolio performance",
                "expected_intent": "portfolio_analysis",
                "test_name": "portfolio_request"
            },
            {
                "message": "Buy $1000 worth of Bitcoin",
                "expected_intent": "trade_execution", 
                "test_name": "trade_request"
            },
            {
                "message": "What are the best opportunities right now?",
                "expected_intent": "opportunity_discovery",
                "test_name": "opportunity_request"
            },
            {
                "message": "Analyze the current market conditions",
                "expected_intent": "market_analysis",
                "test_name": "market_request"
            },
            {
                "message": "Should I rebalance my portfolio?",
                "expected_intent": "rebalancing",
                "test_name": "rebalancing_request"
            },
            {
                "message": "What's my risk level?",
                "expected_intent": "risk_assessment",
                "test_name": "risk_request"
            },
            {
                "message": "Emergency stop all trading",
                "expected_intent": "emergency_command",
                "test_name": "emergency_request"
            }
        ]
        
        for test_case in test_messages:
            try:
                start_time = time.time()
                
                payload = {
                    "message": test_case["message"],
                    "session_id": self.session_id,
                    "mode": "trading",
                    "context": {}
                }
                
                response = self.session.post(f"{BASE_URL}/chat/message", json=payload)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    intent = data.get("intent", "unknown")
                    confidence = data.get("confidence", 0)
                    content_length = len(data.get("content", ""))
                    
                    # Check if intent matches expected
                    intent_correct = intent == test_case["expected_intent"]
                    
                    details = {
                        "intent_detected": intent,
                        "intent_expected": test_case["expected_intent"],
                        "intent_correct": intent_correct,
                        "confidence": confidence,
                        "response_time": response_time,
                        "content_length": content_length,
                        "metadata": data.get("metadata", {})
                    }
                    
                    success = intent_correct and confidence > 0.5 and content_length > 50
                    
                else:
                    success = False
                    details = {
                        "status_code": response.status_code,
                        "error": response.text,
                        "response_time": response_time
                    }
                
                self.log_test("natural_language", test_case["test_name"], success, details)
                
                # Small delay between requests
                time.sleep(1)
                
            except Exception as e:
                self.log_test("natural_language", test_case["test_name"], False, {"error": str(e)})
    
    def test_trading_features(self):
        """Test trading-related chat features"""
        print("\n💰 Testing Trading Features...")
        
        trading_tests = [
            "What's the current price of Bitcoin?",
            "Should I buy Ethereum right now?",
            "Execute a market buy order for $500 of SOL",
            "Set a stop loss at 5% below current price for my BTC position",
            "Show me my open orders",
            "Cancel all pending orders",
            "What's the best entry point for ADA?"
        ]
        
        for i, message in enumerate(trading_tests):
            try:
                start_time = time.time()
                
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "mode": "trading"
                }
                
                response = self.session.post(f"{BASE_URL}/chat/message", json=payload)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("success", False) and len(data.get("content", "")) > 20
                    details = {
                        "intent": data.get("intent"),
                        "confidence": data.get("confidence"),
                        "response_time": response_time,
                        "requires_approval": data.get("requires_approval", False),
                        "content_preview": data.get("content", "")[:100]
                    }
                else:
                    success = False
                    details = {"status_code": response.status_code, "error": response.text}
                
                self.log_test("trading_features", f"trading_test_{i+1}", success, details)
                time.sleep(1)
                
            except Exception as e:
                self.log_test("trading_features", f"trading_test_{i+1}", False, {"error": str(e)})
    
    def test_portfolio_features(self):
        """Test portfolio analysis and optimization features"""
        print("\n📊 Testing Portfolio Features...")
        
        portfolio_tests = [
            "Show me my complete portfolio breakdown",
            "What's my total portfolio value?",
            "How did my portfolio perform this week?",
            "Which assets are underperforming?",
            "Optimize my portfolio allocation",
            "What's my risk-adjusted return?",
            "Show me my profit and loss for each position"
        ]
        
        for i, message in enumerate(portfolio_tests):
            try:
                start_time = time.time()
                
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "mode": "analysis"
                }
                
                response = self.session.post(f"{BASE_URL}/chat/message", json=payload)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("success", False) and len(data.get("content", "")) > 50
                    details = {
                        "intent": data.get("intent"),
                        "confidence": data.get("confidence"),
                        "response_time": response_time,
                        "has_metadata": bool(data.get("metadata")),
                        "content_length": len(data.get("content", ""))
                    }
                else:
                    success = False
                    details = {"status_code": response.status_code, "error": response.text}
                
                self.log_test("portfolio_features", f"portfolio_test_{i+1}", success, details)
                time.sleep(1)
                
            except Exception as e:
                self.log_test("portfolio_features", f"portfolio_test_{i+1}", False, {"error": str(e)})
    
    def test_opportunity_discovery(self):
        """Test opportunity discovery and scanning features"""
        print("\n🔍 Testing Opportunity Discovery...")
        
        opportunity_tests = [
            "Find me the best investment opportunities",
            "Scan the market for undervalued coins",
            "What DeFi opportunities look promising?",
            "Show me arbitrage opportunities",
            "Find momentum plays in the altcoin market",
            "What Layer 1 tokens should I consider?",
            "Discover opportunities in the gaming sector"
        ]
        
        for i, message in enumerate(opportunity_tests):
            try:
                start_time = time.time()
                
                payload = {
                    "message": message,
                    "session_id": self.session_id,
                    "mode": "analysis"
                }
                
                response = self.session.post(f"{BASE_URL}/chat/message", json=payload)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("success", False) and len(data.get("content", "")) > 100
                    details = {
                        "intent": data.get("intent"),
                        "confidence": data.get("confidence"),
                        "response_time": response_time,
                        "metadata": data.get("metadata", {}),
                        "ai_analysis": bool(data.get("ai_analysis"))
                    }
                else:
                    success = False
                    details = {"status_code": response.status_code, "error": response.text}
                
                self.log_test("opportunity_discovery", f"opportunity_test_{i+1}", success, details)
                time.sleep(1)
                
            except Exception as e:
                self.log_test("opportunity_discovery", f"opportunity_test_{i+1}", False, {"error": str(e)})
    
    def calculate_performance_metrics(self):
        """Calculate overall performance metrics"""
        print("\n📈 Calculating Performance Metrics...")
        
        total_tests = 0
        successful_tests = 0
        total_response_time = 0
        response_count = 0
        
        for category, tests in self.test_results.items():
            for test_name, result in tests.items():
                total_tests += 1
                if result["success"]:
                    successful_tests += 1
                
                if "details" in result and "response_time" in result["details"]:
                    total_response_time += result["details"]["response_time"]
                    response_count += 1
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        avg_response_time = (total_response_time / response_count) if response_count > 0 else 0
        
        self.test_results["performance"] = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": success_rate,
            "average_response_time": avg_response_time,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📊 Overall Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
        print(f"⏱️  Average Response Time: {avg_response_time:.2f} seconds")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n📋 Generating Comprehensive Report...")
        
        report = {
            "test_summary": {
                "timestamp": datetime.now().isoformat(),
                "base_url": BASE_URL,
                "total_categories": len([k for k in self.test_results.keys() if k != "performance"]),
                "performance_metrics": self.test_results.get("performance", {})
            },
            "detailed_results": self.test_results
        }
        
        # Save report to file
        filename = f"chat_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Report saved to: {filename}")
        return report
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Comprehensive Chat System Testing...")
        print(f"🌐 Target: {BASE_URL}")
        print(f"👤 User: {ADMIN_EMAIL}")
        print("=" * 60)
        
        # Test authentication first
        if not self.test_authentication():
            print("❌ Authentication failed - cannot proceed with other tests")
            return self.generate_report()
        
        # Run all test suites
        self.test_chat_endpoints()
        self.test_natural_language_processing()
        self.test_trading_features()
        self.test_portfolio_features()
        self.test_opportunity_discovery()
        
        # Calculate metrics and generate report
        self.calculate_performance_metrics()
        return self.generate_report()

def main():
    tester = ComprehensiveChatTester()
    report = tester.run_all_tests()
    
    print("\n" + "=" * 60)
    print("🎯 TESTING COMPLETE!")
    print("=" * 60)
    
    return report

if __name__ == "__main__":
    main()