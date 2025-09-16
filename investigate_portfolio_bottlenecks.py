#!/usr/bin/env python3
"""
Portfolio Performance Bottleneck Investigation
Detailed timing analysis of portfolio fetching pipeline
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

class PortfolioBottleneckInvestigator:
    def __init__(self):
        self.base_url = "https://cryptouniverse.onrender.com"
        self.session = None
        self.auth_token = None
        self.timings = {}
        
    async def authenticate(self) -> bool:
        """Authenticate and get access token"""
        try:
            async with aiohttp.ClientSession() as session:
                # Login request
                login_data = {
                    "email": "admin@cryptouniverse.com",
                    "password": "AdminPass123!"
                }
                
                async with session.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json=login_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.auth_token = result.get("access_token")
                        print("✅ Authenticated successfully")
                        return True
                    else:
                        print(f"❌ Authentication failed: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    async def time_operation(self, name: str, operation_func, *args, **kwargs):
        """Time an async operation and store results"""
        start_time = time.time()
        try:
            result = await operation_func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            
            self.timings[name] = {
                "duration": duration,
                "success": True,
                "result_size": len(str(result)) if result else 0,
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"⏱️  {name}: {duration:.2f}s")
            return result
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            self.timings[name] = {
                "duration": duration,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"❌ {name}: {duration:.2f}s - ERROR: {e}")
            return None

    async def test_individual_components(self):
        """Test individual components of portfolio fetching"""
        print("\n" + "="*60)
        print("🔍 TESTING INDIVIDUAL PORTFOLIO COMPONENTS")
        print("="*60)
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            
            # 1. Test basic user info
            await self.time_operation(
                "user_profile",
                self._get_endpoint,
                session, "/api/v1/users/me", headers
            )
            
            # 2. Test exchange accounts
            await self.time_operation(
                "exchange_accounts",
                self._get_endpoint,
                session, "/api/v1/exchanges/accounts", headers
            )
            
            # 3. Test exchange balances (likely bottleneck)
            await self.time_operation(
                "exchange_balances",
                self._get_endpoint,
                session, "/api/v1/exchanges/balances", headers
            )
            
            # 4. Test portfolio positions
            await self.time_operation(
                "portfolio_positions",
                self._get_endpoint,
                session, "/api/v1/portfolio/positions", headers
            )
            
            # 5. Test portfolio summary (full pipeline)
            await self.time_operation(
                "portfolio_summary_full",
                self._get_endpoint,
                session, "/api/v1/portfolio/summary", headers, timeout=120
            )

    async def test_exchange_specific_performance(self):
        """Test performance of individual exchange operations"""
        print("\n" + "="*60)
        print("🔍 TESTING EXCHANGE-SPECIFIC PERFORMANCE")
        print("="*60)
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            
            # Test each exchange individually if possible
            exchanges = ["binance", "kraken", "kucoin", "coinbase"]
            
            for exchange in exchanges:
                await self.time_operation(
                    f"exchange_{exchange}_balance",
                    self._get_endpoint,
                    session, f"/api/v1/exchanges/{exchange}/balance", headers
                )

    async def test_database_operations(self):
        """Test database-heavy operations"""
        print("\n" + "="*60)
        print("🔍 TESTING DATABASE OPERATIONS")
        print("="*60)
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            
            # Test operations that likely hit database
            await self.time_operation(
                "trading_history",
                self._get_endpoint,
                session, "/api/v1/trading/history", headers
            )
            
            await self.time_operation(
                "portfolio_history",
                self._get_endpoint,
                session, "/api/v1/portfolio/history", headers
            )
            
            await self.time_operation(
                "user_settings",
                self._get_endpoint,
                session, "/api/v1/users/settings", headers
            )

    async def test_risk_calculations(self):
        """Test risk calculation components"""
        print("\n" + "="*60)
        print("🔍 TESTING RISK CALCULATION COMPONENTS")
        print("="*60)
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            
            # Test risk-related endpoints
            await self.time_operation(
                "portfolio_risk",
                self._get_endpoint,
                session, "/api/v1/portfolio/risk", headers
            )
            
            await self.time_operation(
                "portfolio_analytics",
                self._get_endpoint,
                session, "/api/v1/portfolio/analytics", headers
            )

    async def test_market_data_operations(self):
        """Test market data fetching"""
        print("\n" + "="*60)
        print("🔍 TESTING MARKET DATA OPERATIONS")
        print("="*60)
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            
            # Test market data endpoints
            await self.time_operation(
                "market_prices",
                self._get_endpoint,
                session, "/api/v1/market/prices", headers
            )
            
            await self.time_operation(
                "market_analysis",
                self._get_endpoint,
                session, "/api/v1/market/analysis", headers
            )

    async def _get_endpoint(self, session, endpoint: str, headers: Dict, timeout: int = 60):
        """Helper to make GET request to endpoint"""
        async with session.get(
            f"{self.base_url}{endpoint}",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return {"error": "endpoint_not_found", "status": 404}
            else:
                response.raise_for_status()

    async def analyze_bottlenecks(self):
        """Analyze timing results to identify bottlenecks"""
        print("\n" + "="*60)
        print("📊 BOTTLENECK ANALYSIS RESULTS")
        print("="*60)
        
        # Sort operations by duration
        successful_ops = {k: v for k, v in self.timings.items() if v["success"]}
        failed_ops = {k: v for k, v in self.timings.items() if not v["success"]}
        
        if successful_ops:
            sorted_ops = sorted(successful_ops.items(), key=lambda x: x[1]["duration"], reverse=True)
            
            print("\n🐌 SLOWEST OPERATIONS:")
            for i, (name, data) in enumerate(sorted_ops[:5], 1):
                print(f"   {i}. {name}: {data['duration']:.2f}s")
            
            print("\n⚡ FASTEST OPERATIONS:")
            for i, (name, data) in enumerate(reversed(sorted_ops[-3:]), 1):
                print(f"   {i}. {name}: {data['duration']:.2f}s")
        
        if failed_ops:
            print(f"\n❌ FAILED OPERATIONS ({len(failed_ops)}):")
            for name, data in failed_ops.items():
                print(f"   • {name}: {data.get('error', 'Unknown error')}")
        
        # Identify critical bottlenecks
        print("\n🎯 CRITICAL BOTTLENECK ANALYSIS:")
        
        critical_threshold = 10.0  # seconds
        critical_ops = [
            (name, data) for name, data in successful_ops.items() 
            if data["duration"] > critical_threshold
        ]
        
        if critical_ops:
            print(f"   Found {len(critical_ops)} operations taking >{critical_threshold}s:")
            for name, data in critical_ops:
                print(f"   🚨 {name}: {data['duration']:.2f}s")
        else:
            print("   No individual operations taking >10s found")
        
        # Calculate total time if operations were sequential
        total_time = sum(data["duration"] for data in successful_ops.values())
        print(f"\n⏱️  TOTAL TIME (if sequential): {total_time:.2f}s")
        
        return {
            "successful_operations": len(successful_ops),
            "failed_operations": len(failed_ops),
            "slowest_operation": max(successful_ops.items(), key=lambda x: x[1]["duration"]) if successful_ops else None,
            "total_sequential_time": total_time,
            "critical_operations": critical_ops
        }

    async def run_investigation(self):
        """Run complete bottleneck investigation"""
        print("🔍 Starting Portfolio Bottleneck Investigation")
        print(f"🌐 Target: {self.base_url}")
        print(f"⏰ Started: {datetime.now()}")
        
        # Authenticate
        if not await self.authenticate():
            return
        
        # Run all tests
        await self.test_individual_components()
        await self.test_exchange_specific_performance()
        await self.test_database_operations()
        await self.test_risk_calculations()
        await self.test_market_data_operations()
        
        # Analyze results
        analysis = await self.analyze_bottlenecks()
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"portfolio_bottleneck_analysis_{timestamp}.json"
        
        report = {
            "investigation_time": datetime.now().isoformat(),
            "base_url": self.base_url,
            "timings": self.timings,
            "analysis": analysis
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Detailed analysis saved to: {filename}")
        print(f"⏰ Investigation completed: {datetime.now()}")

async def main():
    investigator = PortfolioBottleneckInvestigator()
    await investigator.run_investigation()

if __name__ == "__main__":
    asyncio.run(main())