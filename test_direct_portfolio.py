#!/usr/bin/env python3
"""
Test portfolio fetch directly from exchanges
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_portfolio():
    from app.api.v1.endpoints.exchanges import get_user_portfolio_from_exchanges
    from app.core.database import get_database_session

    user_id = '7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af'

    print(f"Testing portfolio for user: {user_id}")

    async with get_database_session() as db:
        result = await get_user_portfolio_from_exchanges(user_id, db)
        print(f'Success: {result.get("success")}')
        print(f'Total value: ${result.get("total_value_usd", 0):,.2f}')
        print(f'Balances: {result.get("balances", [])}')

        if not result.get("success"):
            print(f'Error: {result.get("error")}')

        return result

if __name__ == "__main__":
    result = asyncio.run(test_portfolio())
