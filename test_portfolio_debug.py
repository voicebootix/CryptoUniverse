#!/usr/bin/env python3
"""
Test portfolio endpoint with admin user
"""
import asyncio
import json

async def test_portfolio():
    try:
        # Test the portfolio functionality directly
        from app.core.database import AsyncSessionLocal
        from app.models.user import User
        from app.api.v1.endpoints.trading import get_portfolio_status
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            # Get admin user
            result = await db.execute(
                select(User).where(User.email == "admin@cryptouniverse.com")
            )
            admin_user = result.scalar_one_or_none()

            if not admin_user:
                print("❌ Admin user not found")
                return

            print(f"✅ Found admin user: {admin_user.email}")

            # Test portfolio status
            try:
                portfolio = await get_portfolio_status(current_user=admin_user, db=db)
                print("✅ Portfolio data retrieved successfully!")
                print(f"   Total Value: ${portfolio.total_value}")
                print(f"   Available Balance: ${portfolio.available_balance}")
                print(f"   Positions: {len(portfolio.positions)}")
                return True
            except Exception as e:
                print(f"❌ Portfolio retrieval failed: {e}")
                import traceback
                traceback.print_exc()
                return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_portfolio())