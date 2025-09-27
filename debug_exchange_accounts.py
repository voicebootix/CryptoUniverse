#!/usr/bin/env python3
"""
Debug why exchange accounts aren't being found
"""

import asyncio
import sys
import os
from uuid import UUID

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def debug_exchanges():
    from app.core.database import get_database_session
    from app.models.exchange import ExchangeAccount, ExchangeApiKey, ExchangeBalance, ApiKeyStatus, ExchangeStatus
    from sqlalchemy import select, and_, or_

    user_id = '7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af'

    async with get_database_session() as db:
        print(f"\n=== DEBUGGING EXCHANGE ACCOUNTS FOR USER {user_id} ===\n")

        # 1. Check all exchange accounts for this user
        print("1. All ExchangeAccount records:")
        stmt = select(ExchangeAccount).where(ExchangeAccount.user_id == user_id)
        result = await db.execute(stmt)
        accounts = result.scalars().all()

        for acc in accounts:
            print(f"   - Exchange: {acc.exchange_type}, Status: {acc.status}, ID: {acc.id}")

        # 2. Check all API keys for these accounts
        if accounts:
            print("\n2. API Keys for these accounts:")
            account_ids = [acc.id for acc in accounts]
            stmt = select(ExchangeApiKey).where(ExchangeApiKey.account_id.in_(account_ids))
            result = await db.execute(stmt)
            api_keys = result.scalars().all()

            for key in api_keys:
                print(f"   - Account ID: {key.account_id}")
                print(f"     Status: {key.status}, Validated: {key.is_validated}")
                print(f"     Has API Key: {bool(key.api_key)}, Has Secret: {bool(key.api_secret)}")

        # 3. Check the exact query used in get_user_portfolio_from_exchanges
        print("\n3. Testing the EXACT query from exchanges.py:")
        stmt = select(ExchangeAccount, ExchangeApiKey).join(
            ExchangeApiKey, ExchangeAccount.id == ExchangeApiKey.account_id
        ).where(
            and_(
                ExchangeAccount.user_id == user_id,
                ExchangeAccount.status == ExchangeStatus.ACTIVE.value,
                ExchangeApiKey.status == ApiKeyStatus.ACTIVE.value,
                ExchangeApiKey.is_validated == True
            )
        )

        result = await db.execute(stmt)
        user_exchanges = result.fetchall()

        print(f"   Found {len(user_exchanges)} matching exchanges")

        if not user_exchanges:
            # Debug why they don't match
            print("\n4. Checking why no matches:")

            # Check status values
            print("   Status values in DB:")
            for acc in accounts:
                print(f"   - Account status: '{acc.status}' (type: {type(acc.status)})")
                print(f"     Expected: '{ExchangeStatus.ACTIVE.value}'")

            if api_keys:
                for key in api_keys:
                    print(f"   - API Key status: '{key.status}' (type: {type(key.status)})")
                    print(f"     Expected: '{ApiKeyStatus.ACTIVE.value}'")
                    print(f"   - is_validated: {key.is_validated} (type: {type(key.is_validated)})")

        # 5. Check ExchangeBalance table
        print("\n5. Checking ExchangeBalance records:")
        if accounts:
            stmt = select(ExchangeBalance).where(ExchangeBalance.account_id.in_(account_ids))
            result = await db.execute(stmt)
            balances = result.scalars().all()

            total = 0
            for bal in balances:
                print(f"   - {bal.asset}: {bal.balance} (${bal.value_usd})")
                total += float(bal.value_usd or 0)
            print(f"   TOTAL: ${total:,.2f}")

if __name__ == "__main__":
    asyncio.run(debug_exchanges())