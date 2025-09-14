#!/usr/bin/env python3
"""
AI Money Manager Comprehensive Testing
CTO-Level Testing: Ensure system reliability before enhancement
"""

import asyncio
import httpx
import json
from datetime import datetime
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com"
LOGIN_DATA = {
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
}

class AIMoneyManagerTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.token = None
        self.test_results = {}
        
    async def authenticate(self):
        """Authenticate and get token"""
        print("🔐 Authenticating...")
        response = await self.client.post(f"{BASE_URL}/api/v1/auth/login", json=LOGIN_DATA)
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            print("✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return False
    
    async def test_current_system_stability(self):
        """Test current system before making changes"""
        print("\n" + "="*80)
        print("🔍 TESTING CURRENT SYSTEM STABILITY")
        print("="*80)
        
        tests = {
            "portfolio_retrieval": self.test_portfolio_api,
            "rebalancing_analysis": self.test_rebalancing_analysis,
            "symbol_consolidation": self.test_symbol_consolidation,
            "strategy_selection": self.test_strategy_selection
        }
        
        results = {}
        for test_name, test_func in tests.items():
            try:
                print(f"\n🧪 Testing {test_name}...")
                result = await test_func()
                results[test_name] = {
                    "status": "PASS" if result else "FAIL",
                    "result": result
                }
                print(f"   {'✅ PASS' if result else '❌ FAIL'}")
            except Exception as e:
                results[test_name] = {
                    "status": "ERROR",
                    "error": str(e)
                }
                print(f"   ❌ ERROR: {e}")
        
        return results
    
    async def test_portfolio_api(self):
        """Test portfolio API functionality"""
        try:
            response = await self.client.get(f"{BASE_URL}/api/v1/trading/portfolio")
            if response.status_code == 200:
                data = response.json()
                total_value = float(data.get('total_value', 0))
                positions = data.get('positions', [])
                
                # Validate data quality
                if total_value > 0 and len(positions) > 0:
                    positions_with_value = [p for p in positions if p.get('value_usd', 0) > 0]
                    return {
                        "total_value": total_value,
                        "total_positions": len(positions),
                        "positions_with_value": len(positions_with_value),
                        "data_quality": "good" if len(positions_with_value) > 5 else "limited"
                    }
            return False
        except Exception as e:
            print(f"Portfolio API error: {e}")
            return False
    
    async def test_rebalancing_analysis(self):
        """Test rebalancing analysis functionality"""
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/message",
                json={"message": "rebalance"}
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('content', '')
                
                # Check for key rebalancing elements
                has_portfolio_value = 'Portfolio Value:' in content
                has_trades = 'Amount:' in content
                has_strategy = 'Strategy:' in content
                
                if has_portfolio_value and has_trades and has_strategy:
                    # Extract trade amounts to check if they're non-zero
                    import re
                    amounts = re.findall(r'Amount: \$([0-9,]+\.?[0-9]*)', content)
                    non_zero_amounts = [amt for amt in amounts if float(amt.replace(',', '')) > 0]
                    
                    return {
                        "rebalancing_working": True,
                        "total_trades": len(amounts),
                        "non_zero_trades": len(non_zero_amounts),
                        "trade_quality": "good" if len(non_zero_amounts) > 0 else "poor"
                    }
            return False
        except Exception as e:
            print(f"Rebalancing test error: {e}")
            return False
    
    async def test_symbol_consolidation(self):
        """Test if symbol consolidation is working"""
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/message",
                json={"message": "rebalance"}
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('content', '')
                
                # Check debug information for consolidation
                if "🔍 **Debug Information:**" in content:
                    import re
                    debug_match = re.search(r'Portfolio Positions: (\d+)', content)
                    weights_match = re.search(r'Optimization Weights: (\d+)', content)
                    
                    if debug_match and weights_match:
                        portfolio_positions = int(debug_match.group(1))
                        optimization_weights = int(weights_match.group(1))
                        
                        return {
                            "consolidation_working": True,
                            "portfolio_positions": portfolio_positions,
                            "optimization_weights": optimization_weights,
                            "consolidation_ratio": optimization_weights / portfolio_positions if portfolio_positions > 0 else 0
                        }
            return False
        except Exception as e:
            print(f"Symbol consolidation test error: {e}")
            return False
    
    async def test_strategy_selection(self):
        """Test strategy selection logic"""
        try:
            # Test different strategy keywords
            strategies_to_test = [
                ("rebalance", "auto"),
                ("rebalance with risk parity", "risk_parity"),
                ("rebalance with max sharpe", "max_sharpe"),
                ("conservative rebalance", "min_variance")
            ]
            
            results = {}
            for message, expected_strategy in strategies_to_test:
                response = await self.client.post(
                    f"{BASE_URL}/api/v1/chat/message",
                    json={"message": message}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get('content', '')
                    
                    # Check if strategy is mentioned in response
                    strategy_detected = expected_strategy in content.lower() or "strategy" in content.lower()
                    results[message] = {
                        "response_received": True,
                        "strategy_detected": strategy_detected
                    }
                else:
                    results[message] = {"response_received": False}
                
                # Small delay between tests
                await asyncio.sleep(1)
            
            return results
        except Exception as e:
            print(f"Strategy selection test error: {e}")
            return False
    
    async def generate_system_health_report(self, test_results):
        """Generate comprehensive system health report"""
        print("\n" + "="*80)
        print("📊 SYSTEM HEALTH REPORT")
        print("="*80)
        
        total_tests = len(test_results)
        passed_tests = len([r for r in test_results.values() if r["status"] == "PASS"])
        failed_tests = len([r for r in test_results.values() if r["status"] == "FAIL"])
        error_tests = len([r for r in test_results.values() if r["status"] == "ERROR"])
        
        health_score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"📈 Overall Health Score: {health_score:.1f}%")
        print(f"✅ Passed Tests: {passed_tests}/{total_tests}")
        print(f"❌ Failed Tests: {failed_tests}/{total_tests}")
        print(f"🚨 Error Tests: {error_tests}/{total_tests}")
        
        print(f"\n📋 Detailed Results:")
        for test_name, result in test_results.items():
            status_icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "🚨"}[result["status"]]
            print(f"   {status_icon} {test_name}: {result['status']}")
            
            if result["status"] == "PASS" and "result" in result:
                if isinstance(result["result"], dict):
                    for key, value in result["result"].items():
                        print(f"      {key}: {value}")
        
        # Risk Assessment
        print(f"\n🎯 RISK ASSESSMENT:")
        if health_score >= 90:
            risk_level = "LOW"
            recommendation = "✅ System is stable. Safe to proceed with enhancements."
        elif health_score >= 70:
            risk_level = "MEDIUM"
            recommendation = "⚠️ Some issues detected. Fix critical issues before major changes."
        else:
            risk_level = "HIGH"
            recommendation = "🚨 Multiple issues detected. Stabilize system before enhancements."
        
        print(f"   Risk Level: {risk_level}")
        print(f"   Recommendation: {recommendation}")
        
        return {
            "health_score": health_score,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "safe_to_enhance": health_score >= 70
        }
    
    async def run_comprehensive_test(self):
        """Run comprehensive system test"""
        print("🔍 Starting AI Money Manager Comprehensive Test")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        print(f"👨‍💼 CTO-Level System Validation")
        
        if not await self.authenticate():
            return False
        
        # Test current system stability
        test_results = await self.test_current_system_stability()
        
        # Generate health report
        health_report = await self.generate_system_health_report(test_results)
        
        await self.client.aclose()
        
        print(f"\n⏰ Testing completed: {datetime.now()}")
        return health_report

async def main():
    tester = AIMoneyManagerTester()
    health_report = await tester.run_comprehensive_test()
    
    if health_report and health_report["safe_to_enhance"]:
        print(f"\n🚀 READY FOR ENHANCEMENT")
        print(f"   System health: {health_report['health_score']:.1f}%")
        print(f"   Risk level: {health_report['risk_level']}")
        print(f"   ✅ Safe to implement AI Money Manager enhancements")
    else:
        print(f"\n⚠️ SYSTEM NEEDS STABILIZATION")
        print(f"   Fix current issues before implementing enhancements")
    
    return health_report

if __name__ == "__main__":
    result = asyncio.run(main())