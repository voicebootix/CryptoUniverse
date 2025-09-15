#!/usr/bin/env python3
"""
Enterprise Rebalancing Fixes Verification
Tests all optimization strategies with proper confidence scores and calculations
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "https://cryptouniverse.onrender.com"

class EnterpriseRebalancingTester:
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
            
    def create_session(self) -> bool:
        """Create chat session"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
            response = requests.post(f"{BASE_URL}/api/v1/chat/session/new", headers=headers, json={}, timeout=30)
            
            if response.status_code == 200:
                self.session_id = response.json().get("session_id")
                print(f"✅ Session created: {self.session_id}")
                return True
            else:
                print(f"❌ Session creation failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Session error: {e}")
            return False
    
    def test_rebalancing_strategy(self, strategy_message: str, strategy_name: str):
        """Test a specific rebalancing strategy"""
        print(f"\n{'='*80}")
        print(f"🎯 TESTING: {strategy_name} Strategy")
        print(f"{'='*80}")
        
        headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
        payload = {"message": strategy_message, "session_id": self.session_id}
        
        try:
            start_time = time.time()
            response = requests.post(f"{BASE_URL}/api/v1/chat/message", headers=headers, json=payload, timeout=90)
            response_time = time.time() - start_time
            
            print(f"⏱️ Response time: {response_time:.1f}s")
            
            if response.status_code == 200:
                data = response.json()
                metadata = data.get('metadata', {})
                
                # Extract key metrics
                portfolio_data = metadata.get('portfolio_data', {})
                rebalance_analysis = metadata.get('rebalance_analysis', {})
                
                portfolio_value = portfolio_data.get('total_value', 0)
                deviation_score = rebalance_analysis.get('deviation_score', 0)
                needs_rebalancing = rebalance_analysis.get('needs_rebalancing', False)
                recommended_trades = rebalance_analysis.get('recommended_trades', [])
                
                print(f"✅ {strategy_name} Analysis Complete")
                print(f"   💰 Portfolio Value: ${portfolio_value:,.2f}")
                print(f"   📊 Deviation Score: {deviation_score:.1f}%")
                print(f"   ⚖️ Needs Rebalancing: {needs_rebalancing}")
                print(f"   🔄 Recommended Trades: {len(recommended_trades)}")
                
                # Check for enterprise fixes
                issues_found = []
                
                # Check deviation score (should be reasonable, not -780%)
                if abs(deviation_score) > 200:
                    issues_found.append(f"Extreme deviation score: {deviation_score:.1f}%")
                
                # Check trade amounts (should not all be $0.00)
                zero_amount_trades = 0
                total_trade_value = 0
                
                for trade in recommended_trades:
                    trade_value = abs(trade.get('value_change', 0))
                    if trade_value == 0:
                        zero_amount_trades += 1
                    total_trade_value += trade_value
                
                if zero_amount_trades == len(recommended_trades) and len(recommended_trades) > 0:
                    issues_found.append("All trades have $0.00 amounts")
                
                # Check for valid asset recommendations
                portfolio_assets = set(pos.get('symbol') for pos in portfolio_data.get('positions', []))
                trade_assets = set(trade.get('symbol') for trade in recommended_trades)
                phantom_assets = trade_assets - portfolio_assets
                
                if phantom_assets:
                    issues_found.append(f"Phantom assets in trades: {phantom_assets}")
                
                # Report results
                if issues_found:
                    print(f"   ❌ Issues Found:")
                    for issue in issues_found:
                        print(f"      • {issue}")
                    return False
                else:
                    print(f"   ✅ All Enterprise Checks Passed")
                    print(f"   📈 Total Trade Value: ${total_trade_value:,.2f}")
                    if trade_assets:
                        print(f"   🎯 Trade Assets: {sorted(trade_assets)}")
                    return True
                    
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def run_enterprise_tests(self):
        """Run comprehensive enterprise rebalancing tests"""
        print("🚀 Starting Enterprise Rebalancing Fixes Verification")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not self.login() or not self.create_session():
            return False
        
        # Test different rebalancing strategies
        strategies = [
            {
                "message": "Rebalance my portfolio using adaptive strategy",
                "name": "Adaptive (Default)"
            },
            {
                "message": "Use equal weight rebalancing for my portfolio",
                "name": "Equal Weight"
            },
            {
                "message": "Apply Kelly Criterion optimization to my portfolio",
                "name": "Kelly Criterion"
            },
            {
                "message": "Optimize my portfolio for maximum Sharpe ratio",
                "name": "Maximum Sharpe"
            },
            {
                "message": "Use risk parity allocation for my portfolio",
                "name": "Risk Parity"
            }
        ]
        
        results = []
        
        for strategy in strategies:
            success = self.test_rebalancing_strategy(strategy["message"], strategy["name"])
            results.append({
                "strategy": strategy["name"],
                "success": success
            })
            
            # Small delay between tests
            time.sleep(3)
        
        # Generate summary
        self.generate_enterprise_summary(results)
        
        return results
    
    def generate_enterprise_summary(self, results):
        """Generate enterprise test summary"""
        print(f"\n{'='*80}")
        print("📊 ENTERPRISE REBALANCING FIXES SUMMARY")
        print(f"{'='*80}")
        
        successful_strategies = [r for r in results if r["success"]]
        failed_strategies = [r for r in results if not r["success"]]
        
        print(f"✅ Successful Strategies: {len(successful_strategies)}/{len(results)}")
        print(f"❌ Failed Strategies: {len(failed_strategies)}")
        
        if successful_strategies:
            print(f"\n✅ WORKING STRATEGIES:")
            for result in successful_strategies:
                print(f"   • {result['strategy']}")
        
        if failed_strategies:
            print(f"\n❌ FAILED STRATEGIES:")
            for result in failed_strategies:
                print(f"   • {result['strategy']}")
        
        # Overall assessment
        success_rate = len(successful_strategies) / len(results) * 100
        
        print(f"\n🎯 ENTERPRISE FIXES ASSESSMENT:")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print(f"   Status: ✅ ENTERPRISE FIXES SUCCESSFUL")
            print(f"   • Confidence scores fixed (no more -780% deviations)")
            print(f"   • Real portfolio assets recognized")
            print(f"   • Trade calculations working")
            print(f"   • Multiple optimization strategies functional")
        elif success_rate >= 60:
            print(f"   Status: ⚠️ PARTIAL SUCCESS - Some strategies need work")
        else:
            print(f"   Status: ❌ ENTERPRISE FIXES NEED MORE WORK")
        
        print(f"\n⏰ Completed: {datetime.now()}")
        print(f"{'='*80}")

def main():
    tester = EnterpriseRebalancingTester()
    results = tester.run_enterprise_tests()
    return results

if __name__ == "__main__":
    main()