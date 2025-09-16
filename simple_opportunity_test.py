#!/usr/bin/env python3
"""
Simple Opportunity Discovery Test Script

Tests the opportunity discovery endpoint directly using requests.
"""

import asyncio
import json
import requests
from datetime import datetime

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

class SimpleOpportunityTester:
    def __init__(self):
        self.token = None
        self.headers = {}
        
    def login(self):
        """Login and get authentication token."""
        print("\n🔐 Logging in...")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            print(f"✅ Logged in successfully as {data['user']['email']}")
            print(f"User ID: {data['user']['id']}")
            return True
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    
    def check_onboarding_status(self):
        """Check user onboarding status."""
        print("\n🚀 Checking Onboarding Status...")
        
        response = requests.get(
            f"{BASE_URL}/api/v1/opportunity/status",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            onboarding = data.get("onboarding_status", {})
            
            print(f"Onboarding Status:")
            print(f"  - Onboarded: {onboarding.get('onboarded', False)}")
            print(f"  - Active Strategies: {onboarding.get('active_strategies', 0)}")
            print(f"  - Credit Balance: {onboarding.get('credit_balance', 0)}")
            print(f"  - Free Strategies Granted: {onboarding.get('free_strategies_granted', False)}")
            
            if not onboarding.get('onboarded'):
                print("⚠️  User not onboarded! Running onboarding...")
                self.trigger_onboarding()
            
            return data
        else:
            print(f"❌ Failed to check status: {response.status_code}")
            print(response.text)
            return {}
    
    def trigger_onboarding(self):
        """Trigger user onboarding to get free strategies."""
        print("\n🎁 Triggering Onboarding...")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/opportunity/onboard",
            headers=self.headers,
            json={"welcome_package": "standard"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Onboarding successful!")
            print(f"  - Onboarding ID: {data.get('onboarding_id')}")
            print(f"  - Results: {json.dumps(data.get('results', {}), indent=2)}")
            return data
        else:
            print(f"❌ Onboarding failed: {response.status_code}")
            print(response.text)
            return {}
    
    def check_user_strategies(self):
        """Check what strategies the user has."""
        print("\n📊 Checking User Strategies...")
        
        response = requests.get(
            f"{BASE_URL}/api/v1/strategies/my-strategies",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            strategies = data.get("strategies", [])
            print(f"Found {len(strategies)} strategies for user")
            
            if strategies:
                print("\nUser Strategies:")
                for idx, strategy in enumerate(strategies):
                    print(f"  {idx+1}. {strategy.get('name', 'N/A')} (ID: {strategy.get('id', 'N/A')})")
            else:
                print("⚠️  No strategies found for user")
            
            return strategies
        else:
            print(f"❌ Failed to get strategies: {response.status_code}")
            print(response.text)
            return []
    
    def test_opportunity_discovery(self, force_refresh=False):
        """Test the opportunity discovery endpoint."""
        print(f"\n🔍 Testing Opportunity Discovery (force_refresh={force_refresh})...")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/opportunity/discover",
            headers=self.headers,
            json={
                "force_refresh": force_refresh,
                "include_strategy_recommendations": True
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            opportunities = data.get("opportunities", [])
            
            print(f"✅ Discovery successful!")
            print(f"  - Scan ID: {data.get('scan_id')}")
            print(f"  - Total Opportunities: {data.get('total_opportunities', 0)}")
            print(f"  - Success: {data.get('success')}")
            
            if data.get('error'):
                print(f"  - Error: {data.get('error')}")
            
            if data.get('fallback_used'):
                print(f"  - Fallback Used: {data.get('fallback_used')}")
            
            # Display opportunities if found
            if opportunities:
                print("\nDiscovered Opportunities:")
                for idx, opp in enumerate(opportunities[:5]):
                    print(f"\n  {idx+1}. {opp.get('strategy_name', 'N/A')}")
                    print(f"     Type: {opp.get('opportunity_type', 'N/A')}")
                    print(f"     Symbol: {opp.get('symbol', 'N/A')} on {opp.get('exchange', 'N/A')}")
                    print(f"     Profit Potential: ${opp.get('profit_potential_usd', 0):.2f}")
                    print(f"     Confidence: {opp.get('confidence_score', 0):.1f}%")
                
                if len(opportunities) > 5:
                    print(f"\n  ... and {len(opportunities) - 5} more opportunities")
            else:
                print("⚠️  No opportunities found!")
            
            # Show user profile
            user_profile = data.get("user_profile", {})
            if user_profile:
                print("\nUser Profile:")
                print(f"  - Active Strategies: {user_profile.get('active_strategy_count', 0)}")
                print(f"  - User Tier: {user_profile.get('user_tier', 'N/A')}")
                print(f"  - Scan Limit: {user_profile.get('opportunity_scan_limit', 0)}")
            
            return data
        else:
            print(f"❌ Discovery failed: {response.status_code}")
            print(response.text)
            return {}
    
    def test_chat_opportunity_discovery(self):
        """Test opportunity discovery through chat."""
        print("\n💬 Testing Chat-based Opportunity Discovery...")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/unified/message",
            headers=self.headers,
            json={
                "message": "Find me trading opportunities",
                "conversation_mode": "live_trading"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat response received")
            print(f"  - Intent: {data.get('intent')}")
            print(f"  - Confidence: {data.get('confidence')}")
            
            content = data.get('content', '')
            if 'opportunit' in content.lower():
                print("✅ Response mentions opportunities")
            else:
                print("⚠️  Response doesn't mention opportunities")
            
            # Print preview of response
            print(f"\nResponse preview: {content[:200]}...")
        else:
            print(f"❌ Chat failed: {response.status_code}")
            print(response.text)
    
    def run_tests(self):
        """Run all tests."""
        print("🚀 Starting Opportunity Discovery Tests")
        print(f"Testing against: {BASE_URL}")
        print(f"Time: {datetime.now().isoformat()}")
        
        # Login
        if not self.login():
            print("Failed to login. Exiting.")
            return
        
        # Check onboarding status
        self.check_onboarding_status()
        
        # Check user strategies
        strategies = self.check_user_strategies()
        
        # Test opportunity discovery
        print("\n=== Test 1: Discovery with cache ===")
        result1 = self.test_opportunity_discovery(force_refresh=False)
        
        print("\n=== Test 2: Discovery without cache (force refresh) ===")
        result2 = self.test_opportunity_discovery(force_refresh=True)
        
        # Test chat-based discovery
        print("\n=== Test 3: Chat-based discovery ===")
        self.test_chat_opportunity_discovery()
        
        # Summary
        print("\n📊 Test Summary")
        print(f"User has {len(strategies)} strategies")
        print(f"Discovery Test 1 found: {len(result1.get('opportunities', []))} opportunities")
        print(f"Discovery Test 2 found: {len(result2.get('opportunities', []))} opportunities")
        
        # Analysis
        print("\n🔍 Issue Analysis:")
        
        if not strategies:
            print("❌ No strategies found - User needs to be onboarded or purchase strategies")
        
        if all(len(r.get('opportunities', [])) == 0 for r in [result1, result2]):
            print("❌ All tests returned zero opportunities")
            print("Possible causes:")
            print("  1. User has no active strategies")
            print("  2. Strategy scanners are not finding qualifying signals")
            print("  3. Asset discovery service is not returning assets")
            print("  4. Signal strength thresholds are too high")
            print("  5. Service initialization or configuration issues")
        
        # Save results
        results_file = f"opportunity_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "base_url": BASE_URL,
                "strategies": strategies,
                "test_results": {
                    "discovery_cached": result1,
                    "discovery_fresh": result2
                }
            }, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    tester = SimpleOpportunityTester()
    tester.run_tests()