#!/usr/bin/env python3
"""
Comprehensive Strategy Verification Script

This script tests all 14 opportunity discovery strategies to determine:
1. Which strategies are actually implemented
2. Which strategies work with real data
3. Which strategies fail and why
4. Overall system health

Usage: python3 verify_all_strategies.py
"""

import asyncio
import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Base configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
LOGIN_CREDENTIALS = {
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
}

class StrategyTester:
    def __init__(self):
        self.token = None
        self.headers = None
        self.results = {}
        
    async def setup(self):
        """Get authentication token."""
        try:
            response = requests.post(f"{BASE_URL}/auth/login", json=LOGIN_CREDENTIALS, timeout=30)
            if response.status_code == 200:
                self.token = response.json().get('access_token')
                self.headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    async def test_strategy(self, strategy_name: str, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single strategy execution."""
        print(f"\n🔍 Testing {strategy_name}...")
        
        payload = {
            "function": function_name,
            "symbol": "BTC/USDT",
            "parameters": parameters,
            "simulation_mode": True
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{BASE_URL}/strategies/execute",
                headers=self.headers,
                json=payload,
                timeout=120
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                
                if success:
                    print(f"✅ {strategy_name} - SUCCESS ({execution_time:.1f}s)")
                    return {
                        "status": "success",
                        "execution_time": execution_time,
                        "data": data,
                        "error": None
                    }
                else:
                    error_msg = data.get('error', 'Unknown error')
                    print(f"⚠️  {strategy_name} - PARTIAL SUCCESS ({execution_time:.1f}s) - {error_msg}")
                    return {
                        "status": "partial",
                        "execution_time": execution_time,
                        "data": data,
                        "error": error_msg
                    }
            else:
                error_msg = response.text
                print(f"❌ {strategy_name} - FAILED ({execution_time:.1f}s) - {error_msg}")
                return {
                    "status": "failed",
                    "execution_time": execution_time,
                    "data": None,
                    "error": error_msg
                }
                
        except requests.exceptions.Timeout:
            print(f"⏰ {strategy_name} - TIMEOUT (120s)")
            return {
                "status": "timeout",
                "execution_time": 120.0,
                "data": None,
                "error": "Request timeout after 120 seconds"
            }
        except Exception as e:
            print(f"💥 {strategy_name} - ERROR - {str(e)}")
            return {
                "status": "error",
                "execution_time": time.time() - start_time,
                "data": None,
                "error": str(e)
            }
    
    async def test_opportunity_discovery(self) -> Dict[str, Any]:
        """Test the opportunity discovery endpoint."""
        print(f"\n🔍 Testing Opportunity Discovery...")
        
        try:
            # Start opportunity discovery
            response = requests.post(
                f"{BASE_URL}/opportunities/discover",
                headers=self.headers,
                json={},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                scan_id = data.get('scan_id')
                
                if scan_id:
                    print(f"✅ Opportunity Discovery - STARTED (scan_id: {scan_id})")
                    
                    # Poll for results
                    for attempt in range(10):
                        await asyncio.sleep(5)
                        
                        status_response = requests.get(
                            f"{BASE_URL}/opportunities/status/{scan_id}",
                            headers=self.headers,
                            timeout=30
                        )
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            status = status_data.get('status', 'unknown')
                            progress = status_data.get('progress_percent', 0)
                            strategies_completed = status_data.get('strategies_completed', 0)
                            
                            print(f"   Status: {status}, Progress: {progress}%, Strategies: {strategies_completed}")
                            
                            if status == 'completed':
                                # Get results
                                results_response = requests.get(
                                    f"{BASE_URL}/opportunities/results/{scan_id}",
                                    headers=self.headers,
                                    timeout=30
                                )
                                
                                if results_response.status_code == 200:
                                    results_data = results_response.json()
                                    opportunities = results_data.get('opportunities', [])
                                    print(f"✅ Opportunity Discovery - COMPLETED - {len(opportunities)} opportunities found")
                                    return {
                                        "status": "success",
                                        "opportunities_count": len(opportunities),
                                        "data": results_data
                                    }
                                else:
                                    print(f"❌ Opportunity Discovery - RESULTS FAILED - {results_response.status_code}")
                                    return {
                                        "status": "results_failed",
                                        "opportunities_count": 0,
                                        "data": None
                                    }
                            elif status == 'failed':
                                print(f"❌ Opportunity Discovery - FAILED")
                                return {
                                    "status": "failed",
                                    "opportunities_count": 0,
                                    "data": status_data
                                }
                        else:
                            print(f"⚠️  Opportunity Discovery - STATUS CHECK FAILED - {status_response.status_code}")
                    
                    print(f"⏰ Opportunity Discovery - TIMEOUT (50s)")
                    return {
                        "status": "timeout",
                        "opportunities_count": 0,
                        "data": None
                    }
                else:
                    print(f"❌ Opportunity Discovery - NO SCAN ID")
                    return {
                        "status": "no_scan_id",
                        "opportunities_count": 0,
                        "data": data
                    }
            else:
                print(f"❌ Opportunity Discovery - FAILED - {response.status_code}")
                return {
                    "status": "failed",
                    "opportunities_count": 0,
                    "data": None
                }
                
        except Exception as e:
            print(f"💥 Opportunity Discovery - ERROR - {str(e)}")
            return {
                "status": "error",
                "opportunities_count": 0,
                "data": None,
                "error": str(e)
            }
    
    async def run_comprehensive_test(self):
        """Run comprehensive test of all strategies."""
        print("🚀 Starting Comprehensive Strategy Verification")
        print("=" * 60)
        
        # Setup authentication
        if not await self.setup():
            return
        
        # Define all 14 strategies to test
        strategies = [
            {
                "name": "Risk Management",
                "function": "risk_management",
                "parameters": {
                    "analysis_type": "comprehensive",
                    "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
                }
            },
            {
                "name": "Portfolio Optimization",
                "function": "portfolio_optimization",
                "parameters": {
                    "rebalance_frequency": "weekly",
                    "risk_target": "balanced",
                    "portfolio_snapshot": {
                        "cash": 1500,
                        "positions": [
                            {"symbol": "BTC/USDT", "quantity": 0.05, "entry_price": 42000},
                            {"symbol": "ETH/USDT", "quantity": 0.75, "entry_price": 2500}
                        ]
                    }
                }
            },
            {
                "name": "Spot Momentum",
                "function": "spot_momentum_strategy",
                "parameters": {"timeframe": "1h", "lookback": 50}
            },
            {
                "name": "Spot Mean Reversion",
                "function": "spot_mean_reversion",
                "parameters": {"timeframe": "1h", "lookback": 40}
            },
            {
                "name": "Spot Breakout",
                "function": "spot_breakout_strategy",
                "parameters": {"timeframe": "4h", "sensitivity": 2.0}
            },
            {
                "name": "Scalping",
                "function": "scalping_strategy",
                "parameters": {"timeframe": "5m", "profit_target": 0.5}
            },
            {
                "name": "Pairs Trading",
                "function": "pairs_trading",
                "parameters": {"symbol1": "BTC/USDT", "symbol2": "ETH/USDT", "lookback": 100}
            },
            {
                "name": "Statistical Arbitrage",
                "function": "statistical_arbitrage",
                "parameters": {"universe": ["BTC/USDT", "ETH/USDT", "SOL/USDT"], "lookback": 50}
            },
            {
                "name": "Market Making",
                "function": "market_making",
                "parameters": {"symbol": "BTC/USDT", "spread_bps": 10, "size": 0.1}
            },
            {
                "name": "Futures Trading",
                "function": "futures_trade",
                "parameters": {"symbol": "BTCUSDT", "side": "long", "leverage": 2}
            },
            {
                "name": "Options Trading",
                "function": "options_trade",
                "parameters": {"symbol": "BTC/USDT", "option_type": "call", "strike": 45000}
            },
            {
                "name": "Funding Arbitrage",
                "function": "funding_arbitrage",
                "parameters": {"symbol": "BTC/USDT", "exchanges": ["binance", "okx"]}
            },
            {
                "name": "Hedge Position",
                "function": "hedge_position",
                "parameters": {"symbol": "BTC/USDT", "hedge_ratio": 0.5}
            },
            {
                "name": "Complex Strategy",
                "function": "complex_strategy",
                "parameters": {"strategy_type": "butterfly", "symbol": "BTC/USDT"}
            }
        ]
        
        # Test each strategy
        for strategy in strategies:
            result = await self.test_strategy(
                strategy["name"],
                strategy["function"],
                strategy["parameters"]
            )
            self.results[strategy["name"]] = result
        
        # Test opportunity discovery
        opportunity_result = await self.test_opportunity_discovery()
        self.results["Opportunity Discovery"] = opportunity_result
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate a comprehensive summary report."""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE STRATEGY VERIFICATION REPORT")
        print("=" * 60)
        
        # Categorize results
        successful = []
        partial = []
        failed = []
        timeout = []
        error = []
        
        for name, result in self.results.items():
            status = result.get('status', 'unknown')
            if status == 'success':
                successful.append(name)
            elif status == 'partial':
                partial.append(name)
            elif status == 'timeout':
                timeout.append(name)
            elif status == 'error':
                error.append(name)
            else:
                failed.append(name)
        
        print(f"\n✅ SUCCESSFUL STRATEGIES ({len(successful)}/14):")
        for name in successful:
            exec_time = self.results[name].get('execution_time', 0)
            print(f"   - {name} ({exec_time:.1f}s)")
        
        print(f"\n⚠️  PARTIAL SUCCESS ({len(partial)}/14):")
        for name in partial:
            exec_time = self.results[name].get('execution_time', 0)
            error_msg = self.results[name].get('error', 'Unknown')
            print(f"   - {name} ({exec_time:.1f}s) - {error_msg}")
        
        print(f"\n❌ FAILED STRATEGIES ({len(failed)}/14):")
        for name in failed:
            exec_time = self.results[name].get('execution_time', 0)
            error_msg = self.results[name].get('error', 'Unknown')
            print(f"   - {name} ({exec_time:.1f}s) - {error_msg}")
        
        print(f"\n⏰ TIMEOUT STRATEGIES ({len(timeout)}/14):")
        for name in timeout:
            exec_time = self.results[name].get('execution_time', 0)
            print(f"   - {name} ({exec_time:.1f}s)")
        
        print(f"\n💥 ERROR STRATEGIES ({len(error)}/14):")
        for name in error:
            exec_time = self.results[name].get('execution_time', 0)
            error_msg = self.results[name].get('error', 'Unknown')
            print(f"   - {name} ({exec_time:.1f}s) - {error_msg}")
        
        # Overall health score
        total_strategies = len(self.results)
        working_strategies = len(successful) + len(partial)
        health_score = (working_strategies / total_strategies) * 100
        
        print(f"\n📈 OVERALL HEALTH SCORE: {health_score:.1f}%")
        print(f"   Working: {working_strategies}/{total_strategies}")
        print(f"   Failed: {len(failed) + len(timeout) + len(error)}/{total_strategies}")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"strategy_verification_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {filename}")
        
        # Recommendations
        print(f"\n🔧 RECOMMENDATIONS:")
        if health_score < 50:
            print("   - CRITICAL: System is not production-ready")
            print("   - Fix infrastructure issues (timeouts, data access)")
            print("   - Implement missing strategy logic")
        elif health_score < 80:
            print("   - WARNING: System needs improvements")
            print("   - Fix failing strategies")
            print("   - Optimize performance")
        else:
            print("   - GOOD: System is mostly functional")
            print("   - Address remaining issues")
            print("   - Consider performance optimization")

async def main():
    """Main execution function."""
    tester = StrategyTester()
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())