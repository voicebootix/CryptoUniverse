#!/usr/bin/env python3
"""
COMPREHENSIVE REBALANCING FLOW ANALYSIS
Testing the complete pipeline from chat input to rebalancing response
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

class ComprehensiveRebalancingAnalyzer:
    def __init__(self):
        self.token = None
        self.session_id = None
        self.test_results = {}
        
    def make_request(self, url: str, data: Dict = None, method: str = "GET") -> Dict[str, Any]:
        """Make HTTP request using urllib"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (compatible; RebalancingAnalyzer/1.0)'
            }
            
            if self.token:
                headers['Authorization'] = f'Bearer {self.token}'
            
            if data and method in ["POST", "PUT"]:
                data_bytes = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
            else:
                req = urllib.request.Request(url, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=60) as response:
                response_data = response.read().decode('utf-8')
                return {
                    "status_code": response.getcode(),
                    "data": json.loads(response_data) if response_data.strip() else {}
                }
                
        except urllib.error.HTTPError as e:
            error_data = e.read().decode('utf-8') if e.fp else str(e)
            try:
                error_json = json.loads(error_data)
            except:
                error_json = {"error": error_data}
            
            return {
                "status_code": e.code,
                "error": error_json
            }
        except Exception as e:
            return {
                "status_code": 0,
                "error": str(e)
            }
    
    def authenticate(self) -> bool:
        """Authenticate and get token"""
        print("🔐 Authenticating...")
        
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
        return False
    
    def test_portfolio_consistency(self) -> Dict[str, Any]:
        """Test portfolio data consistency across multiple calls"""
        print("\n📊 Testing Portfolio Data Consistency...")
        
        portfolios = []
        
        # Make 5 rapid portfolio requests
        for i in range(5):
            print(f"   Portfolio request {i+1}/5...")
            
            response = self.make_request(
                f"{BASE_URL}/chat/message", 
                {"message": "Show my portfolio"}, 
                "POST"
            )
            
            if response.get("status_code") == 200:
                data = response.get("data", {})
                content = data.get("content", "")
                metadata = data.get("metadata", {})
                
                # Extract portfolio data from response
                portfolio_info = {
                    "request_number": i + 1,
                    "content_length": len(content),
                    "has_metadata": bool(metadata),
                    "portfolio_summary": metadata.get("portfolio_summary"),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Parse positions from metadata if available
                if metadata.get("portfolio_summary"):
                    summary = metadata["portfolio_summary"]
                    portfolio_info.update({
                        "total_value": summary.get("total_value"),
                        "position_count": len(summary.get("positions", [])),
                        "positions": [
                            {
                                "symbol": pos.get("symbol"),
                                "value_usd": pos.get("value_usd"),
                                "exchange": pos.get("exchange")
                            }
                            for pos in summary.get("positions", [])
                        ]
                    })
                
                portfolios.append(portfolio_info)
            else:
                portfolios.append({
                    "request_number": i + 1,
                    "error": response.get("error"),
                    "status_code": response.get("status_code")
                })
            
            time.sleep(2)  # Wait 2 seconds between requests
        
        return {
            "test": "portfolio_consistency",
            "portfolios": portfolios,
            "analysis": self._analyze_portfolio_consistency(portfolios)
        }
    
    def _analyze_portfolio_consistency(self, portfolios: List[Dict]) -> Dict[str, Any]:
        """Analyze portfolio consistency"""
        
        # Extract successful portfolio data
        successful_portfolios = [p for p in portfolios if not p.get("error")]
        
        if len(successful_portfolios) < 2:
            return {"error": "Not enough successful portfolio requests to analyze"}
        
        # Check consistency
        total_values = [p.get("total_value") for p in successful_portfolios if p.get("total_value")]
        position_counts = [p.get("position_count") for p in successful_portfolios if p.get("position_count")]
        
        analysis = {
            "successful_requests": len(successful_portfolios),
            "total_requests": len(portfolios),
            "total_value_range": {
                "min": min(total_values) if total_values else None,
                "max": max(total_values) if total_values else None,
                "variance": max(total_values) - min(total_values) if total_values else None
            },
            "position_count_range": {
                "min": min(position_counts) if position_counts else None,
                "max": max(position_counts) if position_counts else None,
                "variance": max(position_counts) - min(position_counts) if position_counts else None
            }
        }
        
        # Check if position counts are consistent
        analysis["position_count_consistent"] = len(set(position_counts)) <= 1 if position_counts else False
        analysis["total_value_consistent"] = analysis["total_value_range"]["variance"] < 100 if total_values else False
        
        return analysis
    
    def test_rebalancing_flow(self) -> Dict[str, Any]:
        """Test the complete rebalancing flow"""
        print("\n⚖️ Testing Rebalancing Flow...")
        
        rebalancing_tests = []
        
        # Test different rebalancing requests
        test_messages = [
            "rebalance my portfolio",
            "I need to rebalance with adaptive strategy", 
            "optimize my portfolio for maximum returns",
            "portfolio optimization",
            "balance my holdings"
        ]
        
        for i, message in enumerate(test_messages):
            print(f"   Testing: '{message}'")
            
            response = self.make_request(
                f"{BASE_URL}/chat/message",
                {"message": message},
                "POST"
            )
            
            if response.get("status_code") == 200:
                data = response.get("data", {})
                
                rebalancing_test = {
                    "test_number": i + 1,
                    "message": message,
                    "success": True,
                    "content": data.get("content", ""),
                    "intent": data.get("intent"),
                    "metadata": data.get("metadata", {}),
                    "response_time": 0,  # Would need to measure this
                    "analysis": self._analyze_rebalancing_response(data)
                }
            else:
                rebalancing_test = {
                    "test_number": i + 1,
                    "message": message,
                    "success": False,
                    "error": response.get("error"),
                    "status_code": response.get("status_code")
                }
            
            rebalancing_tests.append(rebalancing_test)
            time.sleep(3)  # Wait between rebalancing requests
        
        return {
            "test": "rebalancing_flow",
            "tests": rebalancing_tests,
            "summary": self._analyze_rebalancing_flow_summary(rebalancing_tests)
        }
    
    def _analyze_rebalancing_response(self, response_data: Dict) -> Dict[str, Any]:
        """Analyze a single rebalancing response"""
        
        content = response_data.get("content", "")
        metadata = response_data.get("metadata", {})
        
        analysis = {
            "has_content": bool(content),
            "content_length": len(content),
            "intent_classification": response_data.get("intent"),
            "has_metadata": bool(metadata),
            "response_type": "unknown"
        }
        
        # Analyze content patterns
        content_lower = content.lower()
        
        if "rebalancing needed" in content_lower:
            analysis["response_type"] = "rebalancing_recommended"
            
            # Look for trade recommendations
            if "buy" in content_lower or "sell" in content_lower:
                analysis["has_trade_recommendations"] = True
                # Count recommendations
                buy_count = content_lower.count("buy")
                sell_count = content_lower.count("sell")
                analysis["trade_recommendation_count"] = buy_count + sell_count
            else:
                analysis["has_trade_recommendations"] = False
                
        elif "optimally balanced" in content_lower or "no rebalancing needed" in content_lower:
            analysis["response_type"] = "already_balanced"
            
        elif "portfolio summary" in content_lower:
            analysis["response_type"] = "portfolio_summary"
            
        elif "scan complete" in content_lower:
            analysis["response_type"] = "opportunity_scan"
            
        # Check for impossible recommendations (like the REEF example)
        if metadata.get("portfolio_summary"):
            analysis["portfolio_analysis"] = self._analyze_portfolio_metadata(metadata["portfolio_summary"])
            
        return analysis
    
    def _analyze_portfolio_metadata(self, portfolio_summary: Dict) -> Dict[str, Any]:
        """Analyze portfolio metadata for inconsistencies"""
        
        positions = portfolio_summary.get("positions", [])
        total_value = portfolio_summary.get("total_value", 0)
        
        analysis = {
            "position_count": len(positions),
            "total_value": total_value,
            "symbols": [pos.get("symbol") for pos in positions],
            "exchanges": list(set(pos.get("exchange") for pos in positions if pos.get("exchange"))),
            "position_values": {
                pos.get("symbol"): pos.get("value_usd") 
                for pos in positions 
                if pos.get("symbol") and pos.get("value_usd")
            }
        }
        
        # Check for duplicates
        symbols = analysis["symbols"]
        analysis["duplicate_symbols"] = [symbol for symbol in set(symbols) if symbols.count(symbol) > 1]
        analysis["has_duplicates"] = len(analysis["duplicate_symbols"]) > 0
        
        # Check for tiny positions
        tiny_positions = [
            {"symbol": pos.get("symbol"), "value": pos.get("value_usd")}
            for pos in positions 
            if pos.get("value_usd", 0) < 10
        ]
        
        analysis["tiny_positions"] = tiny_positions
        analysis["includes_tiny_positions"] = len(tiny_positions) > 0
        
        return analysis
    
    def _analyze_rebalancing_flow_summary(self, rebalancing_tests: List[Dict]) -> Dict[str, Any]:
        """Analyze overall rebalancing flow performance"""
        
        successful_tests = [t for t in rebalancing_tests if t.get("success")]
        
        if not successful_tests:
            return {"error": "No successful rebalancing tests"}
        
        # Analyze response types
        response_types = [t["analysis"]["response_type"] for t in successful_tests if t.get("analysis")]
        
        summary = {
            "total_tests": len(rebalancing_tests),
            "successful_tests": len(successful_tests),
            "success_rate": len(successful_tests) / len(rebalancing_tests),
            "response_types": {
                response_type: response_types.count(response_type)
                for response_type in set(response_types)
            }
        }
        
        # Check for inconsistent responses to similar queries
        rebalancing_responses = [t for t in successful_tests if t["analysis"]["response_type"] in ["rebalancing_recommended", "already_balanced"]]
        
        if len(rebalancing_responses) > 1:
            response_types_set = set(t["analysis"]["response_type"] for t in rebalancing_responses)
            summary["consistent_rebalancing_responses"] = len(response_types_set) == 1
        
        return summary
    
    def run_comprehensive_analysis(self):
        """Run complete analysis"""
        
        print("=" * 80)
        print("🔬 COMPREHENSIVE REBALANCING FLOW ANALYSIS")
        print("=" * 80)
        
        if not self.authenticate():
            print("❌ Authentication failed - cannot proceed")
            return
        
        # Test 1: Portfolio Consistency
        self.test_results["portfolio_consistency"] = self.test_portfolio_consistency()
        
        # Test 2: Rebalancing Flow
        self.test_results["rebalancing_flow"] = self.test_rebalancing_flow()
        
        # Generate Report
        self.generate_analysis_report()
    
    def generate_analysis_report(self):
        """Generate comprehensive analysis report"""
        
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE ANALYSIS REPORT")
        print("=" * 80)
        
        # Portfolio Consistency Analysis
        portfolio_test = self.test_results.get("portfolio_consistency", {})
        
        if portfolio_test:
            analysis = portfolio_test.get("analysis", {})
            
            print(f"\n🔍 PORTFOLIO CONSISTENCY:")
            print(f"   - Successful Requests: {analysis.get('successful_requests', 0)}/{analysis.get('total_requests', 0)}")
            
            if analysis.get("total_value_range"):
                value_range = analysis["total_value_range"]
                print(f"   - Portfolio Value Range: ${value_range.get('min', 0):.2f} - ${value_range.get('max', 0):.2f}")
                print(f"   - Value Variance: ${value_range.get('variance', 0):.2f}")
                print(f"   - Value Consistent: {analysis.get('total_value_consistent', False)}")
            
            if analysis.get("position_count_range"):
                count_range = analysis["position_count_range"]
                print(f"   - Position Count Range: {count_range.get('min', 0)} - {count_range.get('max', 0)}")
                print(f"   - Count Variance: {count_range.get('variance', 0)}")
                print(f"   - Count Consistent: {analysis.get('position_count_consistent', False)}")
        
        # Rebalancing Flow Analysis
        rebalancing_test = self.test_results.get("rebalancing_flow", {})
        
        if rebalancing_test:
            summary = rebalancing_test.get("summary", {})
            
            print(f"\n⚖️ REBALANCING FLOW:")
            print(f"   - Success Rate: {summary.get('success_rate', 0):.2%}")
            print(f"   - Response Types: {summary.get('response_types', {})}")
            
            if "consistent_rebalancing_responses" in summary:
                print(f"   - Consistent Responses: {summary['consistent_rebalancing_responses']}")
        
        # Identify Issues
        print(f"\n🚨 IDENTIFIED ISSUES:")
        
        issues = []
        
        if portfolio_test:
            portfolio_analysis = portfolio_test.get("analysis", {})
            
            if not portfolio_analysis.get("position_count_consistent"):
                issues.append("Portfolio position count varies between requests")
            
            if not portfolio_analysis.get("total_value_consistent"):
                variance = portfolio_analysis.get("total_value_range", {}).get("variance", 0)
                if variance > 100:
                    issues.append(f"Portfolio value variance too high: ${variance:.2f}")
        
        if rebalancing_test:
            rebalancing_summary = rebalancing_test.get("summary", {})
            
            if not rebalancing_summary.get("consistent_rebalancing_responses", True):
                issues.append("Inconsistent rebalancing responses for similar queries")
                
            success_rate = rebalancing_summary.get("success_rate", 1)
            if success_rate < 0.8:
                issues.append(f"Low rebalancing success rate: {success_rate:.2%}")
        
        if issues:
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("   - No major issues detected")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_rebalancing_analysis_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "test_timestamp": datetime.now().isoformat(),
                "base_url": BASE_URL,
                "test_results": self.test_results,
                "issues_identified": issues
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")
        print("=" * 80)

if __name__ == "__main__":
    analyzer = ComprehensiveRebalancingAnalyzer()
    analyzer.run_comprehensive_analysis()