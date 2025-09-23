#!/usr/bin/env python3
"""
Debug Credit Duplication - Find why there are separate credit accounts
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def debug_credit_accounts():
    print("=== INVESTIGATING CREDIT ACCOUNT DUPLICATION ===")

    from app.core.database import get_database
    from app.models.credit import CreditAccount
    from app.models.user import User
    from sqlalchemy import select, text
    import uuid

    # Known user_id from JWT token
    user_id_str = "7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af"
    user_uuid = uuid.UUID(user_id_str)

    async with get_database() as db:
        print(f"1. Searching for ALL credit accounts for user_id: {user_id_str}")

        # Search by UUID
        print("\n   A. Searching by UUID...")
        stmt_uuid = select(CreditAccount).where(CreditAccount.user_id == user_uuid)
        result_uuid = await db.execute(stmt_uuid)
        accounts_uuid = result_uuid.scalars().all()

        print(f"      Found {len(accounts_uuid)} accounts with UUID:")
        for acc in accounts_uuid:
            print(f"        Account ID: {acc.id}")
            print(f"        User ID: {acc.user_id} (type: {type(acc.user_id)})")
            print(f"        Available Credits: {acc.available_credits}")
            print(f"        Total Credits: {acc.total_credits}")
            print(f"        Created: {acc.created_at}")
            print()

        # Search by string
        print("   B. Searching by String...")
        stmt_str = select(CreditAccount).where(CreditAccount.user_id == user_id_str)
        result_str = await db.execute(stmt_str)
        accounts_str = result_str.scalars().all()

        print(f"      Found {len(accounts_str)} accounts with String:")
        for acc in accounts_str:
            print(f"        Account ID: {acc.id}")
            print(f"        User ID: {acc.user_id} (type: {type(acc.user_id)})")
            print(f"        Available Credits: {acc.available_credits}")
            print(f"        Total Credits: {acc.total_credits}")
            print(f"        Created: {acc.created_at}")
            print()

        # Get ALL credit accounts to see if there are more
        print("2. Getting ALL credit accounts in database...")
        all_stmt = select(CreditAccount)
        all_result = await db.execute(all_stmt)
        all_accounts = all_result.scalars().all()

        print(f"   Total credit accounts: {len(all_accounts)}")
        for acc in all_accounts:
            print(f"     Account {acc.id}: User {acc.user_id} -> {acc.available_credits} credits")

        # Check user table
        print(f"\n3. Verifying user exists...")
        user_stmt = select(User).where(User.id == user_uuid)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if user:
            print(f"   User found: {user.email}, Role: {user.role}, ID: {user.id} (type: {type(user.id)})")
        else:
            print("   User NOT found!")

        # Raw SQL check to be absolutely sure
        print(f"\n4. Raw SQL verification...")
        raw_result = await db.execute(
            text("SELECT id, user_id, available_credits, total_credits FROM credit_accounts WHERE user_id::text = :user_id"),
            {"user_id": user_id_str}
        )
        raw_accounts = raw_result.fetchall()
        print(f"   Raw SQL found {len(raw_accounts)} accounts:")
        for acc in raw_accounts:
            print(f"     {acc.id}: {acc.user_id} -> {acc.available_credits}/{acc.total_credits}")

if __name__ == "__main__":
    asyncio.run(debug_credit_accounts())