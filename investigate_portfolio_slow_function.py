#!/usr/bin/env python3
"""
Portfolio Slow Function Investigation
Deep dive into get_user_portfolio_from_exchanges performance
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

class PortfolioSlowFunctionInvestigator:
    def __init__(self):
        self.base_url = "https://cryptouniverse.onrender.com"
        self.auth_token = None
        self.timings = {}
        
    async def authenticate(self) -> bool:
        """Authenticate and get access token"""
        try:
            async with aiohttp.ClientSession() as session:
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

    async def test_actual_endpoints(self):
        """Test the actual endpoints that exist"""
        print("\n" + "="*60)
        print("🔍 TESTING ACTUAL PORTFOLIO ENDPOINTS")
        print("="*60)
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            
            # 1. Test the actual portfolio endpoint
            await self.time_operation(
                "trading_portfolio_endpoint",
                self._get_endpoint,
                session, "/api/v1/trading/portfolio", headers, 120
            )
            
            # 2. Test exchange list endpoint
            await self.time_operation(
                "exchanges_list",
                self._get_endpoint,
                session, "/api/v1/exchanges/list", headers
            )
            
            # 3. Test specific exchange balances (if any exchanges are connected)
            exchanges = ["binance", "kraken", "kucoin", "coinbase"]
            for exchange in exchanges:
                await self.time_operation(
                    f"exchange_{exchange}_balances",
                    self._get_endpoint,
                    session, f"/api/v1/exchanges/{exchange}/balances", headers
                )

    async def test_chat_portfolio_queries(self):
        """Test portfolio queries through chat system (which calls the slow function)"""
        print("\n" + "="*60)
        print("🔍 TESTING CHAT PORTFOLIO QUERIES")
        print("="*60)
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            
            # Test different portfolio-related chat queries
            portfolio_queries = [
                "What's my current portfolio balance?",
                "Show me my portfolio",
                "What are my current positions?",
                "How much money do I have?",
                "Portfolio summary"
            ]
            
            for i, query in enumerate(portfolio_queries, 1):
                await self.time_operation(
                    f"chat_portfolio_query_{i}",
                    self._post_chat_message,
                    session, query, headers, 90
                )

    async def test_rebalancing_queries(self):
        """Test rebalancing queries that internally call portfolio functions"""
        print("\n" + "="*60)
        print("🔍 TESTING REBALANCING QUERIES (INTERNAL PORTFOLIO CALLS)")
        print("="*60)
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            
            # Test rebalancing queries that should call get_user_portfolio_from_exchanges internally
            rebalancing_queries = [
                "Analyze my portfolio for rebalancing opportunities",
                "What trades should I make to optimize my portfolio?",
                "Suggest portfolio rebalancing",
                "Optimize my current holdings"
            ]
            
            for i, query in enumerate(rebalancing_queries, 1):
                await self.time_operation(
                    f"rebalancing_query_{i}",
                    self._post_chat_message,
                    session, query, headers, 120
                )

    async def test_component_isolation(self):
        """Test individual components that might be slow"""
        print("\n" + "="*60)
        print("🔍 TESTING COMPONENT ISOLATION")
        print("="*60)
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            
            # Test health endpoints to see if system is generally slow
            await self.time_operation(
                "health_check",
                self._get_endpoint,
                session, "/api/v1/health", headers
            )
            
            # Test auth-related endpoints (should be fast)
            await self.time_operation(
                "auth_me",
                self._get_endpoint,
                session, "/api/v1/auth/me", headers
            )
            
            # Test simple chat message (no portfolio data)
            await self.time_operation(
                "simple_chat",
                self._post_chat_message,
                session, "Hello, how are you?", headers, 30
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
            elif response.status == 405:
                return {"error": "method_not_allowed", "status": 405}
            else:
                response.raise_for_status()

    async def _post_chat_message(self, session, message: str, headers: Dict, timeout: int = 60):
        """Helper to send chat message"""
        chat_data = {
            "message": message,
            "conversation_id": None
        }
        
        async with session.post(
            f"{self.base_url}/api/v1/chat/message",
            json=chat_data,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                response.raise_for_status()

    async def analyze_performance_patterns(self):
        """Analyze timing patterns to identify bottlenecks"""
        print("\n" + "="*60)
        print("📊 PERFORMANCE PATTERN ANALYSIS")
        print("="*60)
        
        successful_ops = {k: v for k, v in self.timings.items() if v["success"]}
        failed_ops = {k: v for k, v in self.timings.items() if not v["success"]}
        
        if successful_ops:
            sorted_ops = sorted(successful_ops.items(), key=lambda x: x[1]["duration"], reverse=True)
            
            print("\n🐌 SLOWEST OPERATIONS:")
            for i, (name, data) in enumerate(sorted_ops[:10], 1):
                print(f"   {i:2d}. {name:30s}: {data['duration']:6.2f}s")
            
            print("\n⚡ FASTEST OPERATIONS:")
            for i, (name, data) in enumerate(reversed(sorted_ops[-5:]), 1):
                print(f"   {i:2d}. {name:30s}: {data['duration']:6.2f}s")
        
        if failed_ops:
            print(f"\n❌ FAILED OPERATIONS ({len(failed_ops)}):")
            for name, data in failed_ops.items():
                error_msg = data.get('error', 'Unknown error')
                if len(error_msg) > 80:
                    error_msg = error_msg[:77] + "..."
                print(f"   • {name:30s}: {error_msg}")
        
        # Identify patterns
        print("\n🔍 PATTERN ANALYSIS:")
        
        # Portfolio vs non-portfolio operations
        portfolio_ops = [k for k in successful_ops.keys() if 'portfolio' in k.lower()]
        non_portfolio_ops = [k for k in successful_ops.keys() if 'portfolio' not in k.lower()]
        
        if portfolio_ops:
            avg_portfolio_time = sum(successful_ops[k]["duration"] for k in portfolio_ops) / len(portfolio_ops)
            print(f"   📊 Average Portfolio Operation Time: {avg_portfolio_time:.2f}s")
        
        if non_portfolio_ops:
            avg_non_portfolio_time = sum(successful_ops[k]["duration"] for k in non_portfolio_ops) / len(non_portfolio_ops)
            print(f"   ⚡ Average Non-Portfolio Operation Time: {avg_non_portfolio_time:.2f}s")
        
        # Chat vs direct API
        chat_ops = [k for k in successful_ops.keys() if 'chat' in k.lower()]
        direct_ops = [k for k in successful_ops.keys() if 'chat' not in k.lower()]
        
        if chat_ops:
            avg_chat_time = sum(successful_ops[k]["duration"] for k in chat_ops) / len(chat_ops)
            print(f"   💬 Average Chat Operation Time: {avg_chat_time:.2f}s")
        
        if direct_ops:
            avg_direct_time = sum(successful_ops[k]["duration"] for k in direct_ops) / len(direct_ops)
            print(f"   🔗 Average Direct API Operation Time: {avg_direct_time:.2f}s")
        
        # Identify critical bottlenecks
        critical_threshold = 30.0
        critical_ops = [(k, v) for k, v in successful_ops.items() if v["duration"] > critical_threshold]
        
        if critical_ops:
            print(f"\n🚨 CRITICAL BOTTLENECKS (>{critical_threshold}s):")
            for name, data in critical_ops:
                print(f"   🔥 {name}: {data['duration']:.2f}s")
        
        return {
            "total_operations": len(self.timings),
            "successful_operations": len(successful_ops),
            "failed_operations": len(failed_ops),
            "slowest_operation": max(successful_ops.items(), key=lambda x: x[1]["duration"]) if successful_ops else None,
            "critical_operations": critical_ops,
            "average_portfolio_time": sum(successful_ops[k]["duration"] for k in portfolio_ops) / len(portfolio_ops) if portfolio_ops else 0,
            "average_non_portfolio_time": sum(successful_ops[k]["duration"] for k in non_portfolio_ops) / len(non_portfolio_ops) if non_portfolio_ops else 0
        }

    async def run_investigation(self):
        """Run complete slow function investigation"""
        print("🔍 Starting Portfolio Slow Function Investigation")
        print(f"🌐 Target: {self.base_url}")
        print(f"⏰ Started: {datetime.now()}")
        
        # Authenticate
        if not await self.authenticate():
            return
        
        # Run all tests
        await self.test_actual_endpoints()
        await self.test_component_isolation()
        await self.test_chat_portfolio_queries()
        await self.test_rebalancing_queries()
        
        # Analyze results
        analysis = await self.analyze_performance_patterns()
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"portfolio_slow_function_analysis_{timestamp}.json"
        
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
    investigator = PortfolioSlowFunctionInvestigator()
    await investigator.run_investigation()

if __name__ == "__main__":
    asyncio.run(main())