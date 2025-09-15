#!/usr/bin/env python3
"""
PROPER SYSTEM TESTING
Test current system to understand actual behavior vs expected
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import time
from datetime import datetime
from typing import Dict, List, Any

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

class ProperSystemTester:
    def __init__(self):
        self.token = None
        self.results = {}
        
    def make_request(self, url: str, data: Dict = None, method: str = "GET") -> Dict[str, Any]:
        """Make HTTP request with proper error handling"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (compatible; SystemTester/1.0)'
            }
            
            if self.token:
                headers['Authorization'] = f'Bearer {self.token}'
            
            if data and method in ["POST", "PUT"]:
                data_bytes = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
            else:
                req = urllib.request.Request(url, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=90) as response:
                response_data = response.read().decode('utf-8')
                return {
                    "status_code": response.getcode(),
                    "data": json.loads(response_data) if response_data.strip() else {},
                    "success": True
                }
                
        except urllib.error.HTTPError as e:
            error_data = e.read().decode('utf-8') if e.fp else str(e)
            try:
                error_json = json.loads(error_data)
            except:
                error_json = {"error": error_data}
            
            return {
                "status_code": e.code,
                "error": error_json,
                "success": False
            }
        except Exception as e:
            return {
                "status_code": 0,
                "error": str(e),
                "success": False
            }
    
    def authenticate(self) -> bool:
        """Get authentication token"""
        print("🔐 Authenticating...")
        
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = self.make_request(f"{BASE_URL}/auth/login", login_data, "POST")
        
        if response.get("success") and response.get("status_code") == 200:
            data = response.get("data", {})
            self.token = data.get("access_token")
            if self.token:
                print(f"✅ Authenticated successfully")
                return True
        
        print(f"❌ Authentication failed: {response}")
        return False
    
    def test_opportunities_current(self) -> Dict[str, Any]:
        """Test current opportunity discovery system"""
        print("\n🎯 Testing Current Opportunity System...")
        
        opportunity_queries = [
            "Find me the best cryptocurrency trading opportunities right now",
            "Show me opportunities",
            "What opportunities are available",
            "Find trading opportunities with high profit potential"
        ]
        
        opportunity_results = []
        
        for query in opportunity_queries:
            print(f"   Testing: '{query}'")
            
            response = self.make_request(
                f"{BASE_URL}/chat/message",
                {"message": query},
                "POST"
            )
            
            if response.get("success"):
                data = response.get("data", {})
                
                result = {
                    "query": query,
                    "response_content": data.get("content", "")[:500] + "..." if len(data.get("content", "")) > 500 else data.get("content", ""),
                    "intent": data.get("intent"),
                    "metadata": data.get("metadata", {}),
                    "analysis": self._analyze_opportunity_response(data)
                }
            else:
                result = {
                    "query": query,
                    "error": response.get("error"),
                    "success": False
                }
            
            opportunity_results.append(result)
            time.sleep(3)
        
        return {
            "test": "opportunities_current",
            "results": opportunity_results,
            "summary": self._summarize_opportunity_results(opportunity_results)
        }
    
    def test_rebalancing_strategies(self) -> Dict[str, Any]:
        """Test rebalancing with different strategy requests"""
        print("\n⚖️ Testing Rebalancing Strategies...")
        
        strategy_queries = [
            "rebalance my portfolio",
            "rebalance using risk parity strategy",
            "rebalance using equal weight strategy", 
            "rebalance using max sharpe strategy",
            "rebalance using min variance strategy",
            "rebalance using kelly criterion strategy",
            "rebalance using adaptive strategy",
            "show me all rebalancing strategies with profit potential",
            "what's the best rebalancing strategy for maximum profit"
        ]
        
        strategy_results = []
        
        for query in strategy_queries:
            print(f"   Testing: '{query}'")
            
            response = self.make_request(
                f"{BASE_URL}/chat/message",
                {"message": query},
                "POST"
            )
            
            if response.get("success"):
                data = response.get("data", {})
                
                result = {
                    "query": query,
                    "response_content": data.get("content", "")[:800] + "..." if len(data.get("content", "")) > 800 else data.get("content", ""),
                    "intent": data.get("intent"),
                    "metadata": data.get("metadata", {}),
                    "analysis": self._analyze_rebalancing_response(data)
                }
            else:
                result = {
                    "query": query,
                    "error": response.get("error"),
                    "success": False
                }
            
            strategy_results.append(result)
            time.sleep(4)
        
        return {
            "test": "rebalancing_strategies",
            "results": strategy_results,
            "summary": self._summarize_strategy_results(strategy_results)
        }
    
    def test_portfolio_consistency(self) -> Dict[str, Any]:
        """Test portfolio data consistency"""
        print("\n📊 Testing Portfolio Data Consistency...")
        
        portfolio_results = []
        
        for i in range(3):
            print(f"   Portfolio request {i+1}/3...")
            
            response = self.make_request(
                f"{BASE_URL}/chat/message",
                {"message": "show my portfolio"},
                "POST"
            )
            
            if response.get("success"):
                data = response.get("data", {})
                metadata = data.get("metadata", {})
                
                result = {
                    "request_number": i + 1,
                    "content": data.get("content", ""),
                    "portfolio_metadata": metadata.get("portfolio_summary"),
                    "analysis": self._analyze_portfolio_data(metadata.get("portfolio_summary", {}))
                }
            else:
                result = {
                    "request_number": i + 1,
                    "error": response.get("error"),
                    "success": False
                }
            
            portfolio_results.append(result)
            time.sleep(2)
        
        return {
            "test": "portfolio_consistency", 
            "results": portfolio_results,
            "consistency_analysis": self._analyze_portfolio_consistency(portfolio_results)
        }
    
    def _analyze_opportunity_response(self, response_data: Dict) -> Dict[str, Any]:
        """Analyze opportunity response for key indicators"""
        content = response_data.get("content", "")
        metadata = response_data.get("metadata", {})
        
        analysis = {
            "has_opportunities": "opportunities" in content.lower(),
            "opportunity_count": 0,
            "shows_strategies": False,
            "shows_assets": False,
            "has_profit_potential": "profit" in content.lower() or "return" in content.lower(),
            "mentions_analysis": "analysis" in content.lower() or "consensus" in content.lower(),
            "response_type": "unknown"
        }
        
        # Check metadata for opportunities
        if metadata.get("opportunities"):
            analysis["opportunity_count"] = len(metadata["opportunities"])
        
        # Look for strategy mentions
        strategies = ["risk parity", "equal weight", "max sharpe", "min variance", "kelly", "adaptive"]
        analysis["shows_strategies"] = any(strategy in content.lower() for strategy in strategies)
        
        # Look for asset mentions
        common_assets = ["btc", "eth", "ada", "xrp", "doge", "sol", "aave"]
        analysis["shows_assets"] = any(asset in content.lower() for asset in common_assets)
        
        # Classify response type
        if "no significant trading opportunities" in content.lower():
            analysis["response_type"] = "no_opportunities_found"
        elif "scan complete" in content.lower():
            analysis["response_type"] = "scan_complete_no_results"
        elif analysis["opportunity_count"] > 0:
            analysis["response_type"] = "opportunities_found"
        
        return analysis
    
    def _analyze_rebalancing_response(self, response_data: Dict) -> Dict[str, Any]:
        """Analyze rebalancing response"""
        content = response_data.get("content", "")
        metadata = response_data.get("metadata", {})
        
        analysis = {
            "shows_strategy_comparison": False,
            "shows_profit_potential": False,
            "strategy_count": 0,
            "has_recommendations": "buy" in content.lower() or "sell" in content.lower(),
            "mentions_ai_recommendation": "ai" in content.lower() or "recommend" in content.lower(),
            "shows_risk_reduction": "risk reduction" in content.lower(),
            "shows_expected_improvement": "improvement" in content.lower() or "expected" in content.lower(),
            "response_type": "unknown"
        }
        
        # Check for multiple strategies
        strategies = ["risk parity", "equal weight", "max sharpe", "min variance", "kelly", "adaptive"]
        mentioned_strategies = [s for s in strategies if s in content.lower()]
        analysis["strategy_count"] = len(mentioned_strategies)
        analysis["mentioned_strategies"] = mentioned_strategies
        
        # Classify response type
        if "optimally balanced" in content.lower():
            analysis["response_type"] = "already_balanced"
        elif "rebalancing needed" in content.lower():
            analysis["response_type"] = "rebalancing_recommended"
        elif "portfolio summary" in content.lower():
            analysis["response_type"] = "portfolio_display"
        
        return analysis
    
    def _analyze_portfolio_data(self, portfolio_summary: Dict) -> Dict[str, Any]:
        """Analyze portfolio data structure"""
        if not portfolio_summary:
            return {"error": "no_portfolio_data"}
        
        positions = portfolio_summary.get("positions", [])
        
        return {
            "total_value": portfolio_summary.get("total_value"),
            "position_count": len(positions),
            "symbols": [pos.get("symbol") for pos in positions],
            "exchanges": list(set(pos.get("exchange") for pos in positions if pos.get("exchange"))),
            "has_duplicates": len(positions) != len(set(pos.get("symbol") for pos in positions)),
            "value_range": {
                "max": max((pos.get("value_usd", 0) for pos in positions), default=0),
                "min": min((pos.get("value_usd", 0) for pos in positions), default=0)
            }
        }
    
    def _summarize_opportunity_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Summarize opportunity test results"""
        successful = [r for r in results if r.get("analysis")]
        
        if not successful:
            return {"error": "no_successful_tests"}
        
        return {
            "total_tests": len(results),
            "successful_tests": len(successful),
            "opportunities_found": sum(r["analysis"]["opportunity_count"] for r in successful),
            "shows_strategies": sum(1 for r in successful if r["analysis"]["shows_strategies"]),
            "shows_assets": sum(1 for r in successful if r["analysis"]["shows_assets"]),
            "response_types": [r["analysis"]["response_type"] for r in successful]
        }
    
    def _summarize_strategy_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Summarize strategy test results"""
        successful = [r for r in results if r.get("analysis")]
        
        if not successful:
            return {"error": "no_successful_tests"}
        
        return {
            "total_tests": len(results),
            "successful_tests": len(successful),
            "shows_multiple_strategies": sum(1 for r in successful if r["analysis"]["strategy_count"] > 1),
            "shows_profit_potential": sum(1 for r in successful if r["analysis"]["shows_profit_potential"]),
            "has_recommendations": sum(1 for r in successful if r["analysis"]["has_recommendations"]),
            "response_types": [r["analysis"]["response_type"] for r in successful]
        }
    
    def _analyze_portfolio_consistency(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze portfolio consistency"""
        successful = [r for r in results if r.get("analysis") and not r["analysis"].get("error")]
        
        if len(successful) < 2:
            return {"error": "insufficient_data"}
        
        # Check consistency metrics
        position_counts = [r["analysis"]["position_count"] for r in successful]
        total_values = [r["analysis"]["total_value"] for r in successful if r["analysis"]["total_value"]]
        
        return {
            "consistent_position_count": len(set(position_counts)) == 1,
            "position_count_range": (min(position_counts), max(position_counts)),
            "total_value_variance": max(total_values) - min(total_values) if total_values else 0,
            "symbols_consistent": all(
                set(successful[0]["analysis"]["symbols"]) == set(r["analysis"]["symbols"])
                for r in successful[1:]
            )
        }
    
    def run_comprehensive_test(self):
        """Run comprehensive system test"""
        print("=" * 80)
        print("🔬 COMPREHENSIVE CURRENT SYSTEM TEST")
        print("=" * 80)
        
        if not self.authenticate():
            return
        
        # Test 1: Current Opportunities
        self.results["opportunities"] = self.test_opportunities_current()
        
        # Test 2: Rebalancing Strategies  
        self.results["rebalancing"] = self.test_rebalancing_strategies()
        
        # Test 3: Portfolio Consistency
        self.results["portfolio_consistency"] = self.test_portfolio_consistency()
        
        # Generate comprehensive report
        self.generate_comprehensive_report()
    
    def generate_comprehensive_report(self):
        """Generate detailed analysis report"""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE SYSTEM ANALYSIS")
        print("=" * 80)
        
        # Opportunities Analysis
        opp_test = self.results.get("opportunities", {})
        if opp_test:
            opp_summary = opp_test.get("summary", {})
            print(f"\n🎯 OPPORTUNITY DISCOVERY:")
            print(f"   - Tests Run: {opp_summary.get('successful_tests', 0)}/{opp_summary.get('total_tests', 0)}")
            print(f"   - Opportunities Found: {opp_summary.get('opportunities_found', 0)}")
            print(f"   - Shows Strategies: {opp_summary.get('shows_strategies', 0)} tests")
            print(f"   - Shows Assets: {opp_summary.get('shows_assets', 0)} tests")
            print(f"   - Response Types: {opp_summary.get('response_types', [])}")
        
        # Rebalancing Analysis
        reb_test = self.results.get("rebalancing", {})
        if reb_test:
            reb_summary = reb_test.get("summary", {})
            print(f"\n⚖️ REBALANCING STRATEGIES:")
            print(f"   - Tests Run: {reb_summary.get('successful_tests', 0)}/{reb_summary.get('total_tests', 0)}")
            print(f"   - Shows Multiple Strategies: {reb_summary.get('shows_multiple_strategies', 0)} tests")
            print(f"   - Shows Profit Potential: {reb_summary.get('shows_profit_potential', 0)} tests")
            print(f"   - Has Recommendations: {reb_summary.get('has_recommendations', 0)} tests")
            print(f"   - Response Types: {reb_summary.get('response_types', [])}")
        
        # Portfolio Analysis
        port_test = self.results.get("portfolio_consistency", {})
        if port_test:
            consistency = port_test.get("consistency_analysis", {})
            print(f"\n📊 PORTFOLIO CONSISTENCY:")
            print(f"   - Position Count Consistent: {consistency.get('consistent_position_count', False)}")
            print(f"   - Position Count Range: {consistency.get('position_count_range', 'N/A')}")
            print(f"   - Value Variance: ${consistency.get('total_value_variance', 0):.2f}")
            print(f"   - Symbols Consistent: {consistency.get('symbols_consistent', False)}")
        
        # Key Issues Identified
        print(f"\n🚨 KEY ISSUES IDENTIFIED:")
        
        issues = []
        
        # Check opportunity issues
        if opp_test and opp_test.get("summary", {}).get("opportunities_found", 0) == 0:
            issues.append("No opportunities found in any test")
        
        if opp_test and opp_test.get("summary", {}).get("shows_strategies", 0) == 0:
            issues.append("Strategies not shown in opportunity discovery")
        
        # Check rebalancing issues
        if reb_test and reb_test.get("summary", {}).get("shows_multiple_strategies", 0) == 0:
            issues.append("Multiple strategies not displayed in manual rebalancing")
        
        if reb_test and reb_test.get("summary", {}).get("shows_profit_potential", 0) == 0:
            issues.append("Profit potential not shown for strategies")
        
        # Check consistency issues
        if port_test and not port_test.get("consistency_analysis", {}).get("consistent_position_count", True):
            issues.append("Portfolio position count inconsistent across requests")
        
        if issues:
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("   - No major issues detected")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_system_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "test_timestamp": datetime.now().isoformat(),
                "system_tested": BASE_URL,
                "test_results": self.results,
                "issues_identified": issues
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")
        print("=" * 80)

if __name__ == "__main__":
    tester = ProperSystemTester()
    tester.run_comprehensive_test()