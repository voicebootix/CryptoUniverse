#!/usr/bin/env python3
"""
Comprehensive Opportunity Discovery Test and Debug Script

This script tests and debugs the scanning opportunities issue where
you're getting zero opportunities all the time.

Author: AI Assistant
Date: 2025-09-16
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import httpx
import structlog
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Initialize logging
logger = structlog.get_logger()
console = Console()

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

class OpportunityDebugger:
    """Debug the opportunity discovery system."""
    
    def __init__(self):
        self.token = None
        self.user_id = None
        self.headers = {}
        self.test_results = []
        
    async def login(self):
        """Login and get authentication token."""
        console.print("\n[bold blue]🔐 Logging in...[/bold blue]")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/auth/login",
                    json={
                        "email": ADMIN_EMAIL,
                        "password": ADMIN_PASSWORD
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.token = data["access_token"]
                    self.user_id = data["user"]["id"]
                    self.headers = {"Authorization": f"Bearer {self.token}"}
                    console.print(f"[green]✅ Logged in successfully as {data['user']['email']}[/green]")
                    console.print(f"[dim]User ID: {self.user_id}[/dim]")
                    return True
                else:
                    console.print(f"[red]❌ Login failed: {response.status_code} - {response.text}[/red]")
                    return False
                    
            except Exception as e:
                console.print(f"[red]❌ Login error: {str(e)}[/red]")
                return False
    
    async def check_user_strategies(self):
        """Check what strategies the user has access to."""
        console.print("\n[bold blue]📊 Checking User Strategies...[/bold blue]")
        
        async with httpx.AsyncClient() as client:
            try:
                # Get user's strategies from marketplace
                response = await client.get(
                    f"{BASE_URL}/api/v1/strategies/my-strategies",
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    strategies = data.get("strategies", [])
                    console.print(f"[green]Found {len(strategies)} strategies for user[/green]")
                    
                    if strategies:
                        table = Table(title="User Strategies")
                        table.add_column("Strategy ID", style="cyan")
                        table.add_column("Name", style="yellow")
                        table.add_column("Type", style="green")
                        table.add_column("Status", style="magenta")
                        
                        for strategy in strategies:
                            table.add_row(
                                strategy.get("id", "N/A"),
                                strategy.get("name", "N/A"),
                                strategy.get("type", "N/A"),
                                strategy.get("status", "N/A")
                            )
                        
                        console.print(table)
                    else:
                        console.print("[yellow]⚠️  No strategies found for user[/yellow]")
                    
                    return strategies
                else:
                    console.print(f"[red]Failed to get strategies: {response.status_code}[/red]")
                    console.print(response.text)
                    return []
                    
            except Exception as e:
                console.print(f"[red]Error checking strategies: {str(e)}[/red]")
                return []
    
    async def check_onboarding_status(self):
        """Check user onboarding status."""
        console.print("\n[bold blue]🚀 Checking Onboarding Status...[/bold blue]")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{BASE_URL}/api/v1/opportunity/status",
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    onboarding = data.get("onboarding_status", {})
                    
                    console.print(f"[green]Onboarding Status:[/green]")
                    console.print(f"  - Onboarded: {onboarding.get('onboarded', False)}")
                    console.print(f"  - Active Strategies: {onboarding.get('active_strategies', 0)}")
                    console.print(f"  - Credit Balance: {onboarding.get('credit_balance', 0)}")
                    console.print(f"  - Free Strategies Granted: {onboarding.get('free_strategies_granted', False)}")
                    
                    if not onboarding.get('onboarded'):
                        console.print("[yellow]⚠️  User not onboarded! Running onboarding...[/yellow]")
                        await self.trigger_onboarding()
                    
                    return data
                else:
                    console.print(f"[red]Failed to check status: {response.status_code}[/red]")
                    return {}
                    
            except Exception as e:
                console.print(f"[red]Error checking status: {str(e)}[/red]")
                return {}
    
    async def trigger_onboarding(self):
        """Trigger user onboarding to get free strategies."""
        console.print("\n[bold blue]🎁 Triggering Onboarding...[/bold blue]")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/opportunity/onboard",
                    headers=self.headers,
                    json={
                        "welcome_package": "standard"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    console.print("[green]✅ Onboarding successful![/green]")
                    console.print(f"  - Onboarding ID: {data.get('onboarding_id')}")
                    console.print(f"  - Results: {json.dumps(data.get('results', {}), indent=2)}")
                    return data
                else:
                    console.print(f"[red]Onboarding failed: {response.status_code}[/red]")
                    console.print(response.text)
                    return {}
                    
            except Exception as e:
                console.print(f"[red]Onboarding error: {str(e)}[/red]")
                return {}
    
    async def test_opportunity_discovery(self, force_refresh=False):
        """Test the opportunity discovery endpoint."""
        console.print(f"\n[bold blue]🔍 Testing Opportunity Discovery (force_refresh={force_refresh})...[/bold blue]")
        
        async with httpx.AsyncClient() as client:
            try:
                start_time = time.time()
                
                response = await client.post(
                    f"{BASE_URL}/api/v1/opportunity/discover",
                    headers=self.headers,
                    json={
                        "force_refresh": force_refresh,
                        "include_strategy_recommendations": True
                    },
                    timeout=60.0  # Longer timeout for discovery
                )
                
                end_time = time.time()
                execution_time = (end_time - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    opportunities = data.get("opportunities", [])
                    
                    console.print(f"[green]✅ Discovery successful![/green]")
                    console.print(f"  - Scan ID: {data.get('scan_id')}")
                    console.print(f"  - Total Opportunities: {data.get('total_opportunities', 0)}")
                    console.print(f"  - Execution Time: {execution_time:.2f}ms")
                    console.print(f"  - Success: {data.get('success')}")
                    
                    if data.get('error'):
                        console.print(f"[red]  - Error: {data.get('error')}[/red]")
                    
                    if data.get('fallback_used'):
                        console.print(f"[yellow]  - Fallback Used: {data.get('fallback_used')}[/yellow]")
                    
                    # Display opportunities if found
                    if opportunities:
                        table = Table(title="Discovered Opportunities")
                        table.add_column("Strategy", style="cyan")
                        table.add_column("Type", style="yellow")
                        table.add_column("Symbol", style="green")
                        table.add_column("Exchange", style="blue")
                        table.add_column("Profit Potential", style="magenta")
                        table.add_column("Confidence", style="red")
                        
                        for opp in opportunities[:10]:  # Show first 10
                            table.add_row(
                                opp.get("strategy_name", "N/A"),
                                opp.get("opportunity_type", "N/A"),
                                opp.get("symbol", "N/A"),
                                opp.get("exchange", "N/A"),
                                f"${opp.get('profit_potential_usd', 0):.2f}",
                                f"{opp.get('confidence_score', 0):.1f}%"
                            )
                        
                        console.print(table)
                        
                        if len(opportunities) > 10:
                            console.print(f"[dim]... and {len(opportunities) - 10} more opportunities[/dim]")
                    else:
                        console.print("[yellow]⚠️  No opportunities found![/yellow]")
                    
                    # Show user profile
                    user_profile = data.get("user_profile", {})
                    if user_profile:
                        console.print("\n[bold]User Profile:[/bold]")
                        console.print(f"  - Active Strategies: {user_profile.get('active_strategy_count', 0)}")
                        console.print(f"  - User Tier: {user_profile.get('user_tier', 'N/A')}")
                        console.print(f"  - Scan Limit: {user_profile.get('opportunity_scan_limit', 0)}")
                    
                    # Show asset discovery info
                    asset_discovery = data.get("asset_discovery", {})
                    if asset_discovery:
                        console.print("\n[bold]Asset Discovery:[/bold]")
                        console.print(f"  - Total Assets Scanned: {asset_discovery.get('total_assets_scanned', 0)}")
                        console.print(f"  - Exchanges Covered: {asset_discovery.get('exchanges_covered', 0)}")
                        console.print(f"  - Tier: {asset_discovery.get('asset_tier', 'N/A')}")
                    
                    return data
                else:
                    console.print(f"[red]Discovery failed: {response.status_code}[/red]")
                    console.print(response.text)
                    return {}
                    
            except Exception as e:
                console.print(f"[red]Discovery error: {str(e)}[/red]")
                return {}
    
    async def test_direct_service_call(self):
        """Test calling the opportunity discovery service directly."""
        console.print("\n[bold blue]🔧 Testing Direct Service Call...[/bold blue]")
        
        try:
            # Import and test the service directly
            from app.services.user_opportunity_discovery import user_opportunity_discovery
            from app.services.strategy_marketplace_service import strategy_marketplace_service
            from app.services.trading_strategies import trading_strategies_service
            
            # Initialize services
            await user_opportunity_discovery.async_init()
            await strategy_marketplace_service.async_init()
            
            # Check user strategies directly
            console.print("[yellow]Checking user strategies in marketplace...[/yellow]")
            user_strategies = await strategy_marketplace_service.get_user_strategies(self.user_id)
            console.print(f"User has {len(user_strategies)} strategies")
            
            # Test discovery directly
            console.print("[yellow]Running discovery service directly...[/yellow]")
            result = await user_opportunity_discovery.discover_opportunities_for_user(
                user_id=self.user_id,
                force_refresh=True
            )
            
            console.print(f"Direct service result: Success={result.get('success')}")
            console.print(f"Opportunities found: {len(result.get('opportunities', []))}")
            
            if result.get('error'):
                console.print(f"[red]Error: {result.get('error')}[/red]")
            
            return result
            
        except Exception as e:
            console.print(f"[red]Direct service test error: {str(e)}[/red]")
            import traceback
            console.print(traceback.format_exc())
            return {}
    
    async def check_redis_cache(self):
        """Check Redis cache for opportunity data."""
        console.print("\n[bold blue]🗄️  Checking Redis Cache...[/bold blue]")
        
        try:
            from app.core.redis import get_redis_client
            redis = await get_redis_client()
            
            if redis:
                # Check for cached opportunities
                cache_key = f"user_opportunities:{self.user_id}"
                cached_data = await redis.get(cache_key)
                
                if cached_data:
                    console.print("[green]Found cached opportunity data[/green]")
                    data = json.loads(cached_data)
                    console.print(f"  - Cached opportunities: {len(data.get('opportunities', []))}")
                    console.print(f"  - Cache timestamp: {data.get('last_updated', 'N/A')}")
                else:
                    console.print("[yellow]No cached opportunity data found[/yellow]")
                
                # Check last scan time
                last_scan_key = f"user_opportunity_last_scan:{self.user_id}"
                last_scan = await redis.get(last_scan_key)
                if last_scan:
                    console.print(f"  - Last scan: {last_scan.decode()}")
            else:
                console.print("[yellow]Redis not available[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Redis check error: {str(e)}[/red]")
    
    async def test_chat_opportunity_discovery(self):
        """Test opportunity discovery through chat interface."""
        console.print("\n[bold blue]💬 Testing Chat-based Opportunity Discovery...[/bold blue]")
        
        async with httpx.AsyncClient() as client:
            try:
                # Test various chat messages that should trigger opportunity discovery
                test_messages = [
                    "Find me trading opportunities",
                    "Scan for profitable trades",
                    "What are the best opportunities right now?",
                    "Show me high confidence trading opportunities"
                ]
                
                for message in test_messages:
                    console.print(f"\n[yellow]Testing message: '{message}'[/yellow]")
                    
                    response = await client.post(
                        f"{BASE_URL}/api/v1/chat/unified/message",
                        headers=self.headers,
                        json={
                            "message": message,
                            "conversation_mode": "live_trading"
                        },
                        timeout=60.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        console.print(f"[green]Chat response received[/green]")
                        console.print(f"  - Intent: {data.get('intent')}")
                        console.print(f"  - Confidence: {data.get('confidence')}")
                        
                        # Check if opportunities were mentioned in response
                        content = data.get('content', '')
                        if 'opportunit' in content.lower():
                            console.print("[green]✅ Response mentions opportunities[/green]")
                        else:
                            console.print("[yellow]⚠️  Response doesn't mention opportunities[/yellow]")
                        
                        # Print first 500 chars of response
                        console.print(f"\n[dim]Response preview: {content[:500]}...[/dim]")
                    else:
                        console.print(f"[red]Chat failed: {response.status_code}[/red]")
                    
                    await asyncio.sleep(2)  # Rate limiting
                    
            except Exception as e:
                console.print(f"[red]Chat test error: {str(e)}[/red]")
    
    async def run_comprehensive_test(self):
        """Run all tests comprehensively."""
        console.print("[bold magenta]🚀 Starting Comprehensive Opportunity Discovery Debug[/bold magenta]")
        console.print(f"[dim]Testing against: {BASE_URL}[/dim]")
        console.print(f"[dim]Time: {datetime.now().isoformat()}[/dim]")
        
        # Login
        if not await self.login():
            console.print("[red]Failed to login. Exiting.[/red]")
            return
        
        # Check onboarding status
        await self.check_onboarding_status()
        
        # Check user strategies
        strategies = await self.check_user_strategies()
        
        # Check Redis cache
        await self.check_redis_cache()
        
        # Test opportunity discovery with cache
        console.print("\n[bold]Test 1: Discovery with cache[/bold]")
        result1 = await self.test_opportunity_discovery(force_refresh=False)
        
        # Test opportunity discovery without cache
        console.print("\n[bold]Test 2: Discovery without cache (force refresh)[/bold]")
        result2 = await self.test_opportunity_discovery(force_refresh=True)
        
        # Test direct service call
        console.print("\n[bold]Test 3: Direct service call[/bold]")
        result3 = await self.test_direct_service_call()
        
        # Test chat-based discovery
        console.print("\n[bold]Test 4: Chat-based discovery[/bold]")
        await self.test_chat_opportunity_discovery()
        
        # Summary
        console.print("\n[bold magenta]📊 Test Summary[/bold magenta]")
        console.print(f"User has {len(strategies)} strategies")
        console.print(f"Discovery Test 1 found: {len(result1.get('opportunities', []))} opportunities")
        console.print(f"Discovery Test 2 found: {len(result2.get('opportunities', []))} opportunities")
        console.print(f"Direct Service found: {len(result3.get('opportunities', []))} opportunities")
        
        # Analyze issues
        console.print("\n[bold red]🔍 Issue Analysis:[/bold red]")
        
        if not strategies:
            console.print("[red]❌ No strategies found - User needs to be onboarded or purchase strategies[/red]")
        
        if all(len(r.get('opportunities', [])) == 0 for r in [result1, result2, result3]):
            console.print("[red]❌ All tests returned zero opportunities[/red]")
            console.print("[yellow]Possible causes:[/yellow]")
            console.print("  1. User has no active strategies")
            console.print("  2. Strategy scanners are not implemented properly")
            console.print("  3. Asset discovery service is not returning assets")
            console.print("  4. Redis caching issues")
            console.print("  5. Service initialization problems")
        
        # Save results
        results_file = f"opportunity_debug_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "base_url": BASE_URL,
                "user_id": self.user_id,
                "strategies": strategies,
                "test_results": {
                    "discovery_cached": result1,
                    "discovery_fresh": result2,
                    "direct_service": result3
                }
            }, f, indent=2)
        
        console.print(f"\n[green]Results saved to: {results_file}[/green]")


async def main():
    """Main entry point."""
    debugger = OpportunityDebugger()
    await debugger.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())