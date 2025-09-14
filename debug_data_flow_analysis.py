#!/usr/bin/env python3
"""
Deep Data Flow Analysis
Traces the exact data flow from portfolio retrieval to rebalancing analysis
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "https://cryptouniverse.onrender.com"

class DataFlowAnalyzer:
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
    
    def analyze_portfolio_data_sources(self):
        """Analyze different portfolio data sources"""
        print(f"\n{'='*80}")
        print("🔍 ANALYZING PORTFOLIO DATA SOURCES")
        print(f"{'='*80}")
        
        headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
        
        # 1. Test chat portfolio summary (uses real exchange data)
        print(f"\n📊 1. CHAT PORTFOLIO SUMMARY (Real Exchange Data)")
        print(f"-" * 60)
        
        chat_message = "What's my current portfolio balance?"
        payload = {"message": chat_message, "session_id": self.session_id}
        
        try:
            response = requests.post(f"{BASE_URL}/api/v1/chat/message", headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                metadata = data.get('metadata', {})
                portfolio_summary = metadata.get('portfolio_summary', {})
                
                print(f"✅ Chat Portfolio Data Retrieved:")
                print(f"   Total Value: ${portfolio_summary.get('total_value', 0):,.2f}")
                print(f"   Positions Count: {len(portfolio_summary.get('positions', []))}")
                print(f"   Data Source: {portfolio_summary.get('data_source', 'Unknown')}")
                
                positions = portfolio_summary.get('positions', [])
                print(f"   Assets: {[pos.get('symbol') for pos in positions[:5]]}")
                
                # Save for comparison
                self.chat_portfolio_data = portfolio_summary
            else:
                print(f"❌ Chat portfolio failed: {response.status_code}")
                self.chat_portfolio_data = {}
        except Exception as e:
            print(f"❌ Chat portfolio error: {e}")
            self.chat_portfolio_data = {}
    
    def analyze_rebalancing_data_source(self):
        """Analyze what data the rebalancing system uses"""
        print(f"\n📊 2. REBALANCING SYSTEM DATA SOURCE")
        print(f"-" * 60)
        
        headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
        
        rebalance_message = "Show me rebalancing opportunities with detailed analysis"
        payload = {"message": rebalance_message, "session_id": self.session_id}
        
        try:
            response = requests.post(f"{BASE_URL}/api/v1/chat/message", headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                metadata = data.get('metadata', {})
                
                # Analyze rebalancing data
                rebalance_analysis = metadata.get('rebalance_analysis', {})
                portfolio_data = metadata.get('portfolio_data', {})
                
                print(f"✅ Rebalancing Data Retrieved:")
                print(f"   Portfolio Value: ${portfolio_data.get('total_value', 0):,.2f}")
                print(f"   Positions Count: {len(portfolio_data.get('positions', []))}")
                print(f"   Data Source: {portfolio_data.get('data_source', 'Unknown')}")
                
                positions = portfolio_data.get('positions', [])
                print(f"   Assets: {[pos.get('symbol') for pos in positions[:5]]}")
                
                # Analyze recommended trades
                recommended_trades = rebalance_analysis.get('recommended_trades', [])
                print(f"   Recommended Trades Count: {len(recommended_trades)}")
                if recommended_trades:
                    print(f"   Trade Assets: {[trade.get('symbol') for trade in recommended_trades[:5]]}")
                
                # Save for comparison
                self.rebalance_portfolio_data = portfolio_data
                self.recommended_trades = recommended_trades
            else:
                print(f"❌ Rebalancing analysis failed: {response.status_code}")
                self.rebalance_portfolio_data = {}
                self.recommended_trades = []
        except Exception as e:
            print(f"❌ Rebalancing analysis error: {e}")
            self.rebalance_portfolio_data = {}
            self.recommended_trades = []
    
    def compare_data_sources(self):
        """Compare the different data sources"""
        print(f"\n📊 3. DATA SOURCE COMPARISON")
        print(f"-" * 60)
        
        chat_assets = set()
        rebalance_assets = set()
        trade_assets = set()
        
        # Extract assets from chat portfolio
        if hasattr(self, 'chat_portfolio_data'):
            for pos in self.chat_portfolio_data.get('positions', []):
                chat_assets.add(pos.get('symbol'))
        
        # Extract assets from rebalancing portfolio
        if hasattr(self, 'rebalance_portfolio_data'):
            for pos in self.rebalance_portfolio_data.get('positions', []):
                rebalance_assets.add(pos.get('symbol'))
        
        # Extract assets from recommended trades
        if hasattr(self, 'recommended_trades'):
            for trade in self.recommended_trades:
                trade_assets.add(trade.get('symbol'))
        
        print(f"📈 CHAT PORTFOLIO ASSETS: {sorted(chat_assets)}")
        print(f"⚖️ REBALANCING PORTFOLIO ASSETS: {sorted(rebalance_assets)}")
        print(f"🔄 RECOMMENDED TRADE ASSETS: {sorted(trade_assets)}")
        
        # Check for mismatches
        print(f"\n🔍 MISMATCH ANALYSIS:")
        
        if chat_assets == rebalance_assets:
            print(f"✅ Portfolio data sources MATCH")
        else:
            print(f"❌ Portfolio data sources MISMATCH")
            print(f"   Chat only: {chat_assets - rebalance_assets}")
            print(f"   Rebalancing only: {rebalance_assets - chat_assets}")
        
        if rebalance_assets == trade_assets:
            print(f"✅ Rebalancing and trade assets MATCH")
        else:
            print(f"❌ Rebalancing and trade assets MISMATCH")
            print(f"   Portfolio has: {sorted(rebalance_assets)}")
            print(f"   Trades suggest: {sorted(trade_assets)}")
            print(f"   Trade assets not in portfolio: {trade_assets - rebalance_assets}")
    
    def analyze_optimization_engine_input(self):
        """Analyze what the optimization engine receives as input"""
        print(f"\n📊 4. OPTIMIZATION ENGINE INPUT ANALYSIS")
        print(f"-" * 60)
        
        # Compare portfolio values
        chat_value = 0
        rebalance_value = 0
        
        if hasattr(self, 'chat_portfolio_data'):
            chat_value = self.chat_portfolio_data.get('total_value', 0)
        
        if hasattr(self, 'rebalance_portfolio_data'):
            rebalance_value = self.rebalance_portfolio_data.get('total_value', 0)
        
        print(f"💰 PORTFOLIO VALUES:")
        print(f"   Chat System: ${chat_value:,.2f}")
        print(f"   Rebalancing System: ${rebalance_value:,.2f}")
        print(f"   Difference: ${abs(chat_value - rebalance_value):,.2f}")
        
        if abs(chat_value - rebalance_value) > 10:
            print(f"⚠️ SIGNIFICANT VALUE DIFFERENCE - Different data sources!")
        else:
            print(f"✅ Portfolio values are consistent")
    
    def generate_root_cause_analysis(self):
        """Generate root cause analysis"""
        print(f"\n{'='*80}")
        print("🎯 ROOT CAUSE ANALYSIS")
        print(f"{'='*80}")
        
        issues_found = []
        
        # Check for data source mismatches
        if hasattr(self, 'chat_portfolio_data') and hasattr(self, 'rebalance_portfolio_data'):
            chat_assets = set(pos.get('symbol') for pos in self.chat_portfolio_data.get('positions', []))
            rebalance_assets = set(pos.get('symbol') for pos in self.rebalance_portfolio_data.get('positions', []))
            
            if chat_assets != rebalance_assets:
                issues_found.append({
                    "issue": "Portfolio Data Source Mismatch",
                    "severity": "HIGH",
                    "description": "Chat and rebalancing systems use different portfolio data",
                    "chat_assets": sorted(chat_assets),
                    "rebalance_assets": sorted(rebalance_assets),
                    "root_cause": "Different services calling different portfolio methods"
                })
        
        # Check for trade asset mismatches
        if hasattr(self, 'rebalance_portfolio_data') and hasattr(self, 'recommended_trades'):
            portfolio_assets = set(pos.get('symbol') for pos in self.rebalance_portfolio_data.get('positions', []))
            trade_assets = set(trade.get('symbol') for trade in self.recommended_trades)
            
            if trade_assets - portfolio_assets:
                issues_found.append({
                    "issue": "Trade Recommendations for Non-Existent Assets",
                    "severity": "CRITICAL",
                    "description": "Optimization engine recommends trades for assets not in portfolio",
                    "portfolio_assets": sorted(portfolio_assets),
                    "trade_assets": sorted(trade_assets),
                    "phantom_assets": sorted(trade_assets - portfolio_assets),
                    "root_cause": "Optimization engine using simulated/cached data instead of real portfolio"
                })
        
        # Report findings
        if issues_found:
            print(f"❌ {len(issues_found)} CRITICAL ISSUES FOUND:")
            for i, issue in enumerate(issues_found, 1):
                print(f"\n{i}. {issue['issue']} ({issue['severity']})")
                print(f"   Description: {issue['description']}")
                print(f"   Root Cause: {issue['root_cause']}")
                if 'chat_assets' in issue:
                    print(f"   Chat Assets: {issue['chat_assets']}")
                    print(f"   Rebalance Assets: {issue['rebalance_assets']}")
                if 'phantom_assets' in issue:
                    print(f"   Portfolio Assets: {issue['portfolio_assets']}")
                    print(f"   Trade Assets: {issue['trade_assets']}")
                    print(f"   Phantom Assets: {issue['phantom_assets']}")
        else:
            print(f"✅ No critical data flow issues found")
        
        return issues_found
    
    def run_deep_analysis(self):
        """Run comprehensive data flow analysis"""
        print("🔍 Starting Deep Data Flow Analysis")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not self.login() or not self.create_session():
            return
        
        # Run analysis steps
        self.analyze_portfolio_data_sources()
        self.analyze_rebalancing_data_source()
        self.compare_data_sources()
        self.analyze_optimization_engine_input()
        issues = self.generate_root_cause_analysis()
        
        print(f"\n⏰ Analysis completed: {datetime.now()}")
        return issues

def main():
    analyzer = DataFlowAnalyzer()
    issues = analyzer.run_deep_analysis()
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data_flow_analysis_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(issues, f, indent=2, default=str)
    
    print(f"\n💾 Detailed analysis saved to: {filename}")

if __name__ == "__main__":
    main()