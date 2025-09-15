#!/usr/bin/env python3
"""
Investigation: Portfolio Performance Issues
Systematic analysis of why portfolio fetching is slow and timing out
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "https://cryptouniverse.onrender.com"

class PortfolioPerformanceInvestigator:
    def __init__(self):
        self.auth_token = None
        self.session_id = None
        
    def login(self) -> bool:
        """Login with admin credentials"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"email": "admin@cryptouniverse.com", "password": "AdminPass123!"},
                timeout=30
            )
            
            if response.status_code == 200:
                self.auth_token = response.json().get("access_token")
                print(f"✅ Authenticated successfully")
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def investigate_portfolio_timing(self):
        """Investigate portfolio query timing patterns"""
        print(f"\n{'='*80}")
        print("🔍 INVESTIGATION 1: Portfolio Query Timing Patterns")
        print(f"{'='*80}")
        
        headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
        
        # Test multiple portfolio queries with different timeouts
        test_cases = [
            {"message": "What's my portfolio?", "timeout": 30, "name": "Quick Portfolio"},
            {"message": "Show my current balance", "timeout": 45, "name": "Balance Query"},
            {"message": "Portfolio summary", "timeout": 60, "name": "Summary Query"},
            {"message": "What's my current portfolio balance and performance?", "timeout": 90, "name": "Detailed Portfolio"}
        ]
        
        results = []
        
        for test in test_cases:
            print(f"\n📊 Testing: {test['name']} (timeout: {test['timeout']}s)")
            
            # Create fresh session for each test
            session_response = requests.post(f"{BASE_URL}/api/v1/chat/session/new", headers=headers, json={}, timeout=30)
            if session_response.status_code != 200:
                print(f"   ❌ Session creation failed")
                continue
                
            session_id = session_response.json().get("session_id")
            payload = {"message": test["message"], "session_id": session_id}
            
            try:
                start_time = time.time()
                response = requests.post(
                    f"{BASE_URL}/api/v1/chat/message", 
                    headers=headers, 
                    json=payload, 
                    timeout=test["timeout"]
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    metadata = data.get('metadata', {})
                    portfolio_summary = metadata.get('portfolio_summary', {})
                    
                    result = {
                        "test": test["name"],
                        "success": True,
                        "response_time": response_time,
                        "portfolio_value": portfolio_summary.get('total_value', 0),
                        "positions_count": len(portfolio_summary.get('positions', [])),
                        "timeout_used": test["timeout"]
                    }
                    
                    print(f"   ✅ Success ({response_time:.1f}s)")
                    print(f"      Portfolio: ${result['portfolio_value']:,.2f}")
                    print(f"      Positions: {result['positions_count']}")
                    
                else:
                    result = {
                        "test": test["name"],
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "response_time": response_time,
                        "timeout_used": test["timeout"]
                    }
                    print(f"   ❌ Failed ({response_time:.1f}s): {response.status_code}")
                    
            except requests.exceptions.ReadTimeout:
                result = {
                    "test": test["name"],
                    "success": False,
                    "error": "Read timeout",
                    "response_time": test["timeout"],
                    "timeout_used": test["timeout"]
                }
                print(f"   ❌ Timeout after {test['timeout']}s")
                
            except Exception as e:
                result = {
                    "test": test["name"],
                    "success": False,
                    "error": str(e),
                    "response_time": 0,
                    "timeout_used": test["timeout"]
                }
                print(f"   ❌ Error: {e}")
            
            results.append(result)
            time.sleep(2)  # Small delay between tests
        
        return results
    
    def investigate_rebalancing_timing(self):
        """Investigate rebalancing query timing patterns"""
        print(f"\n{'='*80}")
        print("🔍 INVESTIGATION 2: Rebalancing Query Timing Patterns")
        print(f"{'='*80}")
        
        headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
        
        # Test different rebalancing queries
        test_cases = [
            {"message": "Do I need to rebalance?", "timeout": 30, "name": "Simple Rebalance"},
            {"message": "Should I rebalance?", "timeout": 45, "name": "Basic Rebalance"},
            {"message": "Rebalance my portfolio", "timeout": 60, "name": "Direct Rebalance"},
            {"message": "Show me rebalancing opportunities", "timeout": 90, "name": "Detailed Rebalance"}
        ]
        
        results = []
        
        for test in test_cases:
            print(f"\n⚖️ Testing: {test['name']} (timeout: {test['timeout']}s)")
            
            # Create fresh session
            session_response = requests.post(f"{BASE_URL}/api/v1/chat/session/new", headers=headers, json={}, timeout=30)
            if session_response.status_code != 200:
                print(f"   ❌ Session creation failed")
                continue
                
            session_id = session_response.json().get("session_id")
            payload = {"message": test["message"], "session_id": session_id}
            
            try:
                start_time = time.time()
                response = requests.post(
                    f"{BASE_URL}/api/v1/chat/message", 
                    headers=headers, 
                    json=payload, 
                    timeout=test["timeout"]
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    metadata = data.get('metadata', {})
                    
                    portfolio_data = metadata.get('portfolio_data', {})
                    rebalance_analysis = metadata.get('rebalance_analysis', {})
                    
                    result = {
                        "test": test["name"],
                        "success": True,
                        "response_time": response_time,
                        "portfolio_value": portfolio_data.get('total_value', 0),
                        "positions_count": len(portfolio_data.get('positions', [])),
                        "needs_rebalancing": rebalance_analysis.get('needs_rebalancing'),
                        "trades_count": len(rebalance_analysis.get('recommended_trades', [])),
                        "has_error": bool(rebalance_analysis.get('error')),
                        "timeout_used": test["timeout"]
                    }
                    
                    print(f"   ✅ Success ({response_time:.1f}s)")
                    print(f"      Portfolio: ${result['portfolio_value']:,.2f}")
                    print(f"      Positions: {result['positions_count']}")
                    print(f"      Trades: {result['trades_count']}")
                    if result['has_error']:
                        print(f"      Error: {rebalance_analysis.get('error')}")
                    
                else:
                    result = {
                        "test": test["name"],
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "response_time": response_time,
                        "timeout_used": test["timeout"]
                    }
                    print(f"   ❌ Failed ({response_time:.1f}s): {response.status_code}")
                    
            except requests.exceptions.ReadTimeout:
                result = {
                    "test": test["name"],
                    "success": False,
                    "error": "Read timeout",
                    "response_time": test["timeout"],
                    "timeout_used": test["timeout"]
                }
                print(f"   ❌ Timeout after {test['timeout']}s")
                
            except Exception as e:
                result = {
                    "test": test["name"],
                    "success": False,
                    "error": str(e),
                    "response_time": 0,
                    "timeout_used": test["timeout"]
                }
                print(f"   ❌ Error: {e}")
            
            results.append(result)
            time.sleep(2)
        
        return results
    
    def investigate_performance_bottlenecks(self):
        """Investigate what's causing the performance issues"""
        print(f"\n{'='*80}")
        print("🔍 INVESTIGATION 3: Performance Bottleneck Analysis")
        print(f"{'='*80}")
        
        # Based on the code analysis, identify potential bottlenecks
        bottlenecks = [
            {
                "component": "get_user_portfolio_from_exchanges",
                "location": "app/api/v1/endpoints/exchanges.py",
                "potential_issues": [
                    "Database query performance (ExchangeAccount + ExchangeApiKey joins)",
                    "Exchange API calls (fetch_exchange_balances)",
                    "Multiple exchange processing in sequence",
                    "No caching of exchange balance data"
                ]
            },
            {
                "component": "calculate_daily_pnl",
                "location": "app/services/portfolio_risk_core.py",
                "potential_issues": [
                    "3-second timeout protection may be causing issues",
                    "Historical P&L calculation complexity",
                    "Database queries for historical data"
                ]
            },
            {
                "component": "calculate_portfolio_volatility_risk",
                "location": "app/services/portfolio_risk_core.py", 
                "potential_issues": [
                    "2-second timeout protection",
                    "Volatility calculations for each asset",
                    "Market analysis service calls"
                ]
            },
            {
                "component": "AI Consensus System",
                "location": "Multiple services",
                "potential_issues": [
                    "Multiple AI model calls (GPT-4, Claude, Gemini)",
                    "Network latency to AI services",
                    "AI processing time (15-35 seconds typical)"
                ]
            }
        ]
        
        print("🎯 IDENTIFIED POTENTIAL BOTTLENECKS:")
        for i, bottleneck in enumerate(bottlenecks, 1):
            print(f"\n{i}. {bottleneck['component']}")
            print(f"   Location: {bottleneck['location']}")
            print(f"   Potential Issues:")
            for issue in bottleneck['potential_issues']:
                print(f"     • {issue}")
        
        return bottlenecks
    
    def generate_investigation_report(self, portfolio_results, rebalancing_results, bottlenecks):
        """Generate comprehensive investigation report"""
        print(f"\n{'='*80}")
        print("📊 PORTFOLIO PERFORMANCE INVESTIGATION REPORT")
        print(f"{'='*80}")
        
        # Portfolio timing analysis
        portfolio_successes = [r for r in portfolio_results if r.get("success")]
        portfolio_timeouts = [r for r in portfolio_results if r.get("error") == "Read timeout"]
        
        print(f"📊 PORTFOLIO QUERY ANALYSIS:")
        print(f"   Successful Queries: {len(portfolio_successes)}/{len(portfolio_results)}")
        print(f"   Timeout Queries: {len(portfolio_timeouts)}/{len(portfolio_results)}")
        
        if portfolio_successes:
            avg_time = sum(r["response_time"] for r in portfolio_successes) / len(portfolio_successes)
            print(f"   Average Success Time: {avg_time:.1f}s")
            
        if portfolio_timeouts:
            print(f"   Timeout Thresholds: {[r['timeout_used'] for r in portfolio_timeouts]}s")
        
        # Rebalancing timing analysis
        rebalancing_successes = [r for r in rebalancing_results if r.get("success")]
        rebalancing_timeouts = [r for r in rebalancing_results if r.get("error") == "Read timeout"]
        
        print(f"\n⚖️ REBALANCING QUERY ANALYSIS:")
        print(f"   Successful Queries: {len(rebalancing_successes)}/{len(rebalancing_results)}")
        print(f"   Timeout Queries: {len(rebalancing_timeouts)}/{len(rebalancing_results)}")
        
        if rebalancing_successes:
            avg_time = sum(r["response_time"] for r in rebalancing_successes) / len(rebalancing_successes)
            print(f"   Average Success Time: {avg_time:.1f}s")
            
            # Check data quality
            empty_portfolio_count = sum(1 for r in rebalancing_successes if r.get("portfolio_value", 0) == 0)
            print(f"   Empty Portfolio Results: {empty_portfolio_count}/{len(rebalancing_successes)}")
        
        # Root cause analysis
        print(f"\n🎯 ROOT CAUSE ANALYSIS:")
        
        if len(portfolio_timeouts) > len(portfolio_successes):
            print(f"   ❌ PRIMARY ISSUE: Portfolio queries are timing out frequently")
            print(f"   📍 LOCATION: get_portfolio_summary() method in chat_service_adapters_fixed.py")
            print(f"   🔍 LIKELY CAUSES:")
            print(f"      • Exchange API calls are too slow")
            print(f"      • Database queries are inefficient") 
            print(f"      • P&L calculations are taking too long")
            print(f"      • Risk analysis calculations are slow")
            
        elif len(rebalancing_successes) > 0 and all(r.get("portfolio_value", 0) == 0 for r in rebalancing_successes):
            print(f"   ❌ PRIMARY ISSUE: Rebalancing gets empty portfolio data")
            print(f"   📍 LOCATION: Portfolio data pipeline in rebalancing analysis")
            print(f"   🔍 LIKELY CAUSES:")
            print(f"      • Portfolio conversion is failing")
            print(f"      • Monkey-patch is not working correctly")
            print(f"      • Exception handling is swallowing errors")
            
        else:
            print(f"   ⚠️ MIXED ISSUES: Both timing and data quality problems")
        
        # Performance recommendations
        print(f"\n💡 PERFORMANCE OPTIMIZATION RECOMMENDATIONS:")
        print(f"   1. Add caching layer for portfolio data (60-second TTL)")
        print(f"   2. Optimize database queries with proper indexing")
        print(f"   3. Implement async parallel processing for exchange calls")
        print(f"   4. Add circuit breakers for slow external services")
        print(f"   5. Implement progressive timeouts (fast path vs detailed path)")
        
        return {
            "portfolio_success_rate": len(portfolio_successes) / len(portfolio_results) if portfolio_results else 0,
            "rebalancing_success_rate": len(rebalancing_successes) / len(rebalancing_results) if rebalancing_results else 0,
            "primary_issue": "timeout" if len(portfolio_timeouts) > len(portfolio_successes) else "data_quality",
            "bottlenecks": bottlenecks
        }
    
    def run_investigation(self):
        """Run complete performance investigation"""
        print("🔍 Starting Portfolio Performance Investigation")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not self.login():
            return None
        
        # Run investigations
        portfolio_results = self.investigate_portfolio_timing()
        rebalancing_results = self.investigate_rebalancing_timing()
        bottlenecks = self.investigate_performance_bottlenecks()
        
        # Generate report
        report = self.generate_investigation_report(portfolio_results, rebalancing_results, bottlenecks)
        
        print(f"\n⏰ Investigation completed: {datetime.now()}")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"portfolio_performance_investigation_{timestamp}.json"
        
        investigation_data = {
            "portfolio_results": portfolio_results,
            "rebalancing_results": rebalancing_results,
            "bottlenecks": bottlenecks,
            "report": report,
            "timestamp": timestamp
        }
        
        with open(filename, 'w') as f:
            json.dump(investigation_data, f, indent=2, default=str)
        
        print(f"💾 Detailed investigation saved to: {filename}")
        
        return report

def main():
    investigator = PortfolioPerformanceInvestigator()
    report = investigator.run_investigation()
    return report

if __name__ == "__main__":
    main()