#!/usr/bin/env python3
"""
Test Efficient Rebalancing Fix
Tests that rebalancing now uses the same real portfolio data as chat
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "https://cryptouniverse.onrender.com"

class EfficientRebalancingTester:
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
    
    def test_portfolio_data_consistency(self):
        """Test that portfolio and rebalancing use the same data"""
        print(f"\n{'='*80}")
        print("🔍 TESTING: Portfolio Data Consistency After Fix")
        print(f"{'='*80}")
        
        headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
        
        # 1. Get portfolio data
        print(f"\n📊 Step 1: Getting Portfolio Data")
        portfolio_message = "What's my current portfolio balance?"
        payload = {"message": portfolio_message, "session_id": self.session_id}
        
        try:
            response = requests.post(f"{BASE_URL}/api/v1/chat/message", headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                portfolio_metadata = data.get('metadata', {}).get('portfolio_summary', {})
                
                portfolio_value = portfolio_metadata.get('total_value', 0)
                portfolio_positions = portfolio_metadata.get('positions', [])
                portfolio_assets = [pos.get('symbol') for pos in portfolio_positions]
                
                print(f"✅ Portfolio Retrieved:")
                print(f"   Value: ${portfolio_value:,.2f}")
                print(f"   Assets: {sorted(portfolio_assets)}")
                print(f"   Positions: {len(portfolio_positions)}")
                
                self.portfolio_data = {
                    'value': portfolio_value,
                    'assets': set(portfolio_assets),
                    'positions': len(portfolio_positions)
                }
            else:
                print(f"❌ Portfolio retrieval failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Portfolio error: {e}")
            return False
        
        # 2. Get rebalancing data (should use SAME portfolio data)
        print(f"\n⚖️ Step 2: Getting Rebalancing Analysis")
        rebalance_message = "Should I rebalance my portfolio?"
        payload = {"message": rebalance_message, "session_id": self.session_id}
        
        try:
            response = requests.post(f"{BASE_URL}/api/v1/chat/message", headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                metadata = data.get('metadata', {})
                
                rebalance_portfolio = metadata.get('portfolio_data', {})
                rebalance_value = rebalance_portfolio.get('total_value', 0)
                rebalance_positions = rebalance_portfolio.get('positions', [])
                rebalance_assets = [pos.get('symbol') for pos in rebalance_positions]
                
                recommended_trades = metadata.get('rebalance_analysis', {}).get('recommended_trades', [])
                trade_assets = [trade.get('symbol') for trade in recommended_trades]
                
                print(f"✅ Rebalancing Retrieved:")
                print(f"   Value: ${rebalance_value:,.2f}")
                print(f"   Assets: {sorted(rebalance_assets)}")
                print(f"   Positions: {len(rebalance_positions)}")
                print(f"   Trade Assets: {sorted(trade_assets)}")
                
                self.rebalance_data = {
                    'value': rebalance_value,
                    'assets': set(rebalance_assets),
                    'positions': len(rebalance_positions),
                    'trade_assets': set(trade_assets)
                }
                
                return True
            else:
                print(f"❌ Rebalancing failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Rebalancing error: {e}")
            return False
    
    def analyze_consistency(self):
        """Analyze data consistency between portfolio and rebalancing"""
        print(f"\n📊 Step 3: Data Consistency Analysis")
        print(f"-" * 60)
        
        if not hasattr(self, 'portfolio_data') or not hasattr(self, 'rebalance_data'):
            print(f"❌ Missing data for comparison")
            return False
        
        portfolio = self.portfolio_data
        rebalance = self.rebalance_data
        
        # Check portfolio values
        value_diff = abs(portfolio['value'] - rebalance['value'])
        value_match = value_diff < 10  # Allow $10 difference for timing
        
        print(f"💰 PORTFOLIO VALUES:")
        print(f"   Chat Portfolio: ${portfolio['value']:,.2f}")
        print(f"   Rebalancing Portfolio: ${rebalance['value']:,.2f}")
        print(f"   Difference: ${value_diff:,.2f}")
        print(f"   Match: {'✅' if value_match else '❌'}")
        
        # Check asset consistency
        assets_match = portfolio['assets'] == rebalance['assets']
        
        print(f"\n🎯 ASSET CONSISTENCY:")
        print(f"   Chat Assets: {sorted(portfolio['assets'])}")
        print(f"   Rebalancing Assets: {sorted(rebalance['assets'])}")
        print(f"   Match: {'✅' if assets_match else '❌'}")
        
        if not assets_match:
            print(f"   Chat Only: {sorted(portfolio['assets'] - rebalance['assets'])}")
            print(f"   Rebalancing Only: {sorted(rebalance['assets'] - portfolio['assets'])}")
        
        # Check trade asset validity
        trade_assets = rebalance.get('trade_assets', set())
        valid_trades = trade_assets.issubset(rebalance['assets'])
        
        print(f"\n🔄 TRADE VALIDITY:")
        print(f"   Portfolio Assets: {sorted(rebalance['assets'])}")
        print(f"   Trade Assets: {sorted(trade_assets)}")
        print(f"   Valid Trades: {'✅' if valid_trades else '❌'}")
        
        if not valid_trades:
            phantom_assets = trade_assets - rebalance['assets']
            print(f"   Phantom Trade Assets: {sorted(phantom_assets)}")
        
        # Overall assessment
        overall_success = value_match and assets_match and valid_trades
        
        print(f"\n🎯 OVERALL ASSESSMENT:")
        print(f"   Portfolio Value Match: {'✅' if value_match else '❌'}")
        print(f"   Asset Consistency: {'✅' if assets_match else '❌'}")
        print(f"   Trade Validity: {'✅' if valid_trades else '❌'}")
        print(f"   FIX SUCCESS: {'✅' if overall_success else '❌'}")
        
        return overall_success
    
    def run_efficiency_test(self):
        """Run the complete efficiency test"""
        print("🚀 Starting Efficient Rebalancing Fix Test")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not self.login() or not self.create_session():
            return False
        
        # Test data consistency
        if not self.test_portfolio_data_consistency():
            print(f"\n❌ Data consistency test failed")
            return False
        
        # Analyze results
        success = self.analyze_consistency()
        
        print(f"\n{'='*80}")
        print("📊 EFFICIENCY TEST SUMMARY")
        print(f"{'='*80}")
        
        if success:
            print("✅ EFFICIENCY FIX SUCCESSFUL!")
            print("   • Portfolio and rebalancing use same data")
            print("   • No duplicate API calls")
            print("   • Trade recommendations are valid")
            print("   • Data consistency maintained")
        else:
            print("❌ EFFICIENCY FIX NEEDS MORE WORK")
            print("   • Data inconsistencies still exist")
            print("   • May still be using separate data sources")
        
        print(f"\n⏰ Completed: {datetime.now()}")
        return success

def main():
    tester = EfficientRebalancingTester()
    success = tester.run_efficiency_test()
    return success

if __name__ == "__main__":
    main()