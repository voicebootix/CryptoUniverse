#!/usr/bin/env python3
"""
Test strategy marketplace service directly to debug portfolio issues
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_strategy_marketplace_direct():
    """Test strategy marketplace service directly"""
    
    try:
        from app.services.strategy_marketplace_service import StrategyMarketplaceService
        
        print("🔧 Testing Strategy Marketplace Service Directly")
        print("=" * 60)
        
        # Create service instance
        service = StrategyMarketplaceService()
        
        # Test with admin user ID
        admin_user_id = "7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af"
        
        print(f"👤 Testing with admin user: {admin_user_id}")
        
        # Test get_user_strategy_portfolio
        print("\n1️⃣ Testing get_user_strategy_portfolio...")
        try:
            portfolio_result = await service.get_user_strategy_portfolio(admin_user_id)
            print(f"   Success: {portfolio_result.get('success')}")
            print(f"   Active strategies: {len(portfolio_result.get('active_strategies', []))}")
            print(f"   Total strategies: {portfolio_result.get('total_strategies', 0)}")
            print(f"   Error: {portfolio_result.get('error', 'None')}")
            
            if portfolio_result.get('active_strategies'):
                strategies = portfolio_result.get('active_strategies', [])
                print(f"   Strategy names: {[s.get('name') for s in strategies[:5]]}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test get_admin_portfolio_snapshot
        print("\n2️⃣ Testing get_admin_portfolio_snapshot...")
        try:
            admin_snapshot = await service.get_admin_portfolio_snapshot(admin_user_id)
            if admin_snapshot:
                print(f"   Success: {admin_snapshot.get('success')}")
                print(f"   Active strategies: {len(admin_snapshot.get('active_strategies', []))}")
                print(f"   Total strategies: {admin_snapshot.get('total_strategies', 0)}")
                print(f"   Error: {admin_snapshot.get('error', 'None')}")
                
                if admin_snapshot.get('active_strategies'):
                    strategies = admin_snapshot.get('active_strategies', [])
                    print(f"   Strategy names: {[s.get('name') for s in strategies[:5]]}")
            else:
                print("   Admin snapshot returned None")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print("\n✅ Direct service test completed")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("This is expected in test environment without full app setup")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_strategy_marketplace_direct())