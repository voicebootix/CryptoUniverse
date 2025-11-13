#!/usr/bin/env python3
"""
Test opportunity discovery service directly to debug portfolio issues
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_opportunity_discovery_direct():
    """Test opportunity discovery service directly"""
    
    try:
        from app.services.user_opportunity_discovery import UserOpportunityDiscoveryService
        
        print("🔧 Testing Opportunity Discovery Service Directly")
        print("=" * 60)
        
        # Create service instance
        service = UserOpportunityDiscoveryService()
        
        # Test with admin user ID
        admin_user_id = "7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af"
        
        print(f"👤 Testing with admin user: {admin_user_id}")
        
        # Test _get_user_portfolio_cached
        print("\n1️⃣ Testing _get_user_portfolio_cached...")
        try:
            portfolio_result = await service._get_user_portfolio_cached(admin_user_id)
            print(f"   Success: {portfolio_result.get('success')}")
            print(f"   Active strategies: {len(portfolio_result.get('active_strategies', []))}")
            print(f"   Total strategies: {portfolio_result.get('total_strategies', 0)}")
            print(f"   Error: {portfolio_result.get('error', 'None')}")
            
            if portfolio_result.get('active_strategies'):
                strategies = portfolio_result.get('active_strategies', [])
                print(f"   Strategy names: {[s.get('name') for s in strategies[:5]]}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test _get_user_portfolio
        print("\n2️⃣ Testing _get_user_portfolio...")
        try:
            portfolio_result = await service._get_user_portfolio(admin_user_id)
            print(f"   Success: {portfolio_result.get('success')}")
            print(f"   Active strategies: {len(portfolio_result.get('active_strategies', []))}")
            print(f"   Total strategies: {portfolio_result.get('total_strategies', 0)}")
            print(f"   Error: {portfolio_result.get('error', 'None')}")
            
            if portfolio_result.get('active_strategies'):
                strategies = portfolio_result.get('active_strategies', [])
                print(f"   Strategy names: {[s.get('name') for s in strategies[:5]]}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print("\n✅ Direct service test completed")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("This is expected in test environment without full app setup")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_opportunity_discovery_direct())