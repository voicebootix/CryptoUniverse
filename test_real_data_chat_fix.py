#!/usr/bin/env python3
"""
FOCUSED TEST: Real Data vs Mock Data in Chat
Tests if merge 77396f2 fixed the core issue where chat returned mock data instead of real market intelligence.

Tests specifically:
1. Opportunity Discovery - Should return REAL market opportunities
2. Rebalancing - Should return REAL rebalancing suggestions  
3. Portfolio Optimization - Should return REAL optimization recommendations
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

class RealDataChatTester:
    def __init__(self):
        self.token = None
        self.session_id = None
        self.results = {}
        
    def make_request(self, url: str, data: Dict = None, method: str = "GET") -> Dict[str, Any]:
        """Make HTTP request using urllib"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (compatible; ChatTester/1.0)'
            }
            
            if self.token:
                headers['Authorization'] = f'Bearer {self.token}'
            
            if data and method in ["POST", "PUT"]:
                data_bytes = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
            else:
                req = urllib.request.Request(url, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=45) as response:
                return {
                    "status_code": response.getcode(),
                    "data": json.loads(response.read().decode('utf-8'))
                }
                
        except urllib.error.HTTPError as e:
            return {
                "status_code": e.code,
                "error": e.read().decode('utf-8') if e.fp else str(e)
            }
        except Exception as e:
            return {
                "status_code": 0,
                "error": str(e)
            }
    
    def authenticate(self) -> bool:
        """Login and get auth token"""
        print("🔐 Authenticating...")
        
        try:
            login_data = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            
            response = self.make_request(f"{BASE_URL}/auth/login", login_data, "POST")
            
            if response.get("status_code") == 200:
                data = response.get("data", {})
                self.token = data.get("access_token")
                if self.token:
                    print(f"✅ Authenticated successfully")
                    return True
            
            print(f"❌ Authentication failed: {response.get('status_code', 'Unknown')}")
            print(f"   Error: {response.get('error', 'No error details')}")
            return False
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def create_session(self) -> bool:
        """Create chat session"""
        try:
            response = self.make_request(f"{BASE_URL}/chat/session/new", {}, "POST")
            if response.get("status_code") == 200:
                data = response.get("data", {})
                self.session_id = data.get("session_id")
                print(f"✅ Chat session created: {self.session_id}")
                return True
            print(f"❌ Session creation failed: {response.get('status_code', 'Unknown')}")
            return False
        except Exception as e:
            print(f"❌ Session creation failed: {e}")
            return False
    
    def analyze_response_for_real_data(self, response_text: str, test_type: str) -> Dict[str, Any]:
        """Analyze if response contains real data vs mock/template data"""
        
        # Indicators of MOCK/TEMPLATE data
        mock_indicators = [
            "example", "sample", "placeholder", "mock", "template", 
            "demo", "test", "fictional", "hypothetical", "$X", "$Y",
            "[Amount]", "[Symbol]", "[Price]", "TBD", "N/A", "Coming Soon",
            "Lorem", "ipsum", "dolor", "consectetur", "adipiscing"
        ]
        
        # Indicators of REAL data
        real_data_indicators = [
            "$", "BTC", "ETH", "USD", "USDT", "EUR", "GBP",
            "%", "0.", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.",
            "price", "volume", "market cap", "24h", "change",
            "binance", "coinbase", "kraken", "kucoin",
            "buy", "sell", "trade", "portfolio", "balance"
        ]
        
        response_lower = response_text.lower()
        
        mock_count = sum(1 for indicator in mock_indicators if indicator.lower() in response_lower)
        real_count = sum(1 for indicator in real_data_indicators if indicator.lower() in response_lower)
        
        # Look for specific patterns that indicate real vs mock
        has_real_prices = any(f"${i}" in response_text for i in range(10000)) or \
                         any(f"{i}." in response_text for i in range(1000))
        
        has_mock_patterns = any(pattern in response_lower for pattern in [
            "example portfolio", "sample strategy", "placeholder data",
            "mock response", "template answer", "coming soon"
        ])
        
        analysis = {
            "likely_real_data": real_count > mock_count and not has_mock_patterns,
            "mock_indicators": mock_count,
            "real_indicators": real_count,
            "has_real_prices": has_real_prices,
            "has_mock_patterns": has_mock_patterns,
            "response_length": len(response_text),
            "contains_specific_numbers": bool(has_real_prices)
        }
        
        return analysis
    
    def test_opportunity_discovery(self) -> Dict[str, Any]:
        """Test: Find new trading opportunities - should return REAL opportunities"""
        
        print("\n🎯 Testing OPPORTUNITY DISCOVERY...")
        
        test_message = "Find me the best cryptocurrency trading opportunities right now. I want real market opportunities with current prices and potential returns."
        
        try:
            start_time = time.time()
            
            payload = {
                "message": test_message,
                "session_id": self.session_id
            }
            
            response = self.make_request(f"{BASE_URL}/chat/message", payload, "POST")
            response_time = time.time() - start_time
            
            if response.get("status_code") == 200:
                data = response.get("data", {})
                response_text = data.get("response", "")
                
                analysis = self.analyze_response_for_real_data(response_text, "opportunities")
                
                print(f"📊 Response Analysis:")
                print(f"   - Length: {analysis['response_length']} characters")
                print(f"   - Real data indicators: {analysis['real_indicators']}")
                print(f"   - Mock data indicators: {analysis['mock_indicators']}")
                print(f"   - Has real prices: {analysis['has_real_prices']}")
                print(f"   - Likely real data: {analysis['likely_real_data']}")
                
                if analysis['likely_real_data']:
                    print("✅ SUCCESS: Response contains REAL opportunity data")
                else:
                    print("❌ FAILED: Response appears to contain mock/template data")
                
                return {
                    "success": response.get("status_code") == 200,
                    "real_data_detected": analysis['likely_real_data'],
                    "response_time": response_time,
                    "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text,
                    "analysis": analysis
                }
            else:
                print(f"❌ Request failed: {response.get('status_code', 'Unknown')}")
                return {"success": False, "error": f"HTTP {response.get('status_code', 'Unknown')}"}
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"success": False, "error": str(e)}
    
    def test_rebalancing(self) -> Dict[str, Any]:
        """Test: Portfolio rebalancing - should return REAL rebalancing advice"""
        
        print("\n⚖️ Testing PORTFOLIO REBALANCING...")
        
        test_message = "I need to rebalance my crypto portfolio. Please analyze my current holdings and suggest specific rebalancing actions with real market data."
        
        try:
            start_time = time.time()
            
            payload = {
                "message": test_message,
                "session_id": self.session_id
            }
            
            response = self.make_request(f"{BASE_URL}/chat/message", payload, "POST")
            response_time = time.time() - start_time
            
            if response.get("status_code") == 200:
                data = response.get("data", {})
                response_text = data.get("response", "")
                
                analysis = self.analyze_response_for_real_data(response_text, "rebalancing")
                
                print(f"📊 Response Analysis:")
                print(f"   - Length: {analysis['response_length']} characters")
                print(f"   - Real data indicators: {analysis['real_indicators']}")
                print(f"   - Mock data indicators: {analysis['mock_indicators']}")
                print(f"   - Has real prices: {analysis['has_real_prices']}")
                print(f"   - Likely real data: {analysis['likely_real_data']}")
                
                if analysis['likely_real_data']:
                    print("✅ SUCCESS: Response contains REAL rebalancing data")
                else:
                    print("❌ FAILED: Response appears to contain mock/template data")
                
                return {
                    "success": response.get("status_code") == 200,
                    "real_data_detected": analysis['likely_real_data'],
                    "response_time": response_time,
                    "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text,
                    "analysis": analysis
                }
            else:
                print(f"❌ Request failed: {response.get('status_code', 'Unknown')}")
                return {"success": False, "error": f"HTTP {response.get('status_code', 'Unknown')}"}
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"success": False, "error": str(e)}
    
    def test_portfolio_optimization(self) -> Dict[str, Any]:
        """Test: Portfolio optimization - should return REAL optimization suggestions"""
        
        print("\n🚀 Testing PORTFOLIO OPTIMIZATION...")
        
        test_message = "Optimize my cryptocurrency portfolio for maximum returns. I want specific recommendations with real market analysis and current data."
        
        try:
            start_time = time.time()
            
            payload = {
                "message": test_message,
                "session_id": self.session_id
            }
            
            response = self.make_request(f"{BASE_URL}/chat/message", payload, "POST")
            response_time = time.time() - start_time
            
            if response.get("status_code") == 200:
                data = response.get("data", {})
                response_text = data.get("response", "")
                
                analysis = self.analyze_response_for_real_data(response_text, "optimization")
                
                print(f"📊 Response Analysis:")
                print(f"   - Length: {analysis['response_length']} characters")
                print(f"   - Real data indicators: {analysis['real_indicators']}")
                print(f"   - Mock data indicators: {analysis['mock_indicators']}")
                print(f"   - Has real prices: {analysis['has_real_prices']}")
                print(f"   - Likely real data: {analysis['likely_real_data']}")
                
                if analysis['likely_real_data']:
                    print("✅ SUCCESS: Response contains REAL optimization data")
                else:
                    print("❌ FAILED: Response appears to contain mock/template data")
                
                return {
                    "success": response.get("status_code") == 200,
                    "real_data_detected": analysis['likely_real_data'],
                    "response_time": response_time,
                    "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text,
                    "analysis": analysis
                }
            else:
                print(f"❌ Request failed: {response.get('status_code', 'Unknown')}")
                return {"success": False, "error": f"HTTP {response.get('status_code', 'Unknown')}"}
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"success": False, "error": str(e)}
    
    def run_full_test(self):
        """Run the complete real data test suite"""
        
        print("=" * 60)
        print("🎯 TESTING: Real Data vs Mock Data in Chat System")
        print("   Verifying if merge 77396f2 fixed the mock data issue")
        print("=" * 60)
        
        # Authenticate
        if not self.authenticate():
            print("❌ Authentication failed - cannot proceed")
            return
        
        # Create session
        if not self.create_session():
            print("❌ Session creation failed - cannot proceed")
            return
        
        # Run the three critical tests
        self.results["opportunity_discovery"] = self.test_opportunity_discovery()
        time.sleep(2)  # Brief pause between tests
        
        self.results["rebalancing"] = self.test_rebalancing()
        time.sleep(2)
        
        self.results["portfolio_optimization"] = self.test_portfolio_optimization()
        
        # Generate final report
        self.generate_final_report()
    
    def generate_final_report(self):
        """Generate comprehensive test report"""
        
        print("\n" + "=" * 60)
        print("📊 FINAL TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for result in self.results.values() if result.get("success", False))
        real_data_tests = sum(1 for result in self.results.values() if result.get("real_data_detected", False))
        
        print(f"📈 Overall Statistics:")
        print(f"   - Total Tests: {total_tests}")
        print(f"   - Successful Requests: {successful_tests}/{total_tests} ({(successful_tests/total_tests)*100:.1f}%)")
        print(f"   - Real Data Detected: {real_data_tests}/{total_tests} ({(real_data_tests/total_tests)*100:.1f}%)")
        
        print(f"\n🎯 Core Issue Resolution:")
        if real_data_tests == total_tests:
            print("✅ MERGE SUCCESS: All tests show real data instead of mock data")
            print("   The chat system is now providing actual market intelligence!")
        elif real_data_tests > 0:
            print("⚠️  PARTIAL SUCCESS: Some tests show real data, others still show mock data")
            print("   The merge partially fixed the issue but needs more work")
        else:
            print("❌ MERGE FAILED: All tests still show mock/template data")
            print("   The core issue was not resolved by merge 77396f2")
        
        print(f"\n📋 Detailed Results:")
        for test_name, result in self.results.items():
            status = "✅" if result.get("real_data_detected", False) else "❌"
            print(f"   {status} {test_name.replace('_', ' ').title()}")
            if result.get("response_preview"):
                print(f"      Preview: {result['response_preview']}")
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"real_data_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "test_timestamp": datetime.now().isoformat(),
                "merge_tested": "77396f2",
                "base_url": BASE_URL,
                "summary": {
                    "total_tests": total_tests,
                    "successful_requests": successful_tests,
                    "real_data_detected": real_data_tests,
                    "success_rate": (real_data_tests/total_tests)*100 if total_tests > 0 else 0
                },
                "detailed_results": self.results
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")
        print("=" * 60)

if __name__ == "__main__":
    tester = RealDataChatTester()
    tester.run_full_test()