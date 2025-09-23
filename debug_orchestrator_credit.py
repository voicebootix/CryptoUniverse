#!/usr/bin/env python3
"""
Debug the orchestrator credit lookup directly to see what's happening
"""

import asyncio
import sys
import os
import uuid

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def debug_orchestrator_credit():
    print("=== DEBUGGING ORCHESTRATOR CREDIT LOOKUP ===")

    # Known user_id from JWT token
    user_id_str = "7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af"

    print(f"Testing orchestrator credit lookup for user: {user_id_str}")

    try:
        # Test the exact same logic as orchestrator
        from app.core.database import get_database
        from app.api.v1.endpoints.credits import get_or_create_credit_account

        # Convert string user_id to UUID (same as credit API)
        user_uuid = uuid.UUID(user_id_str)
        print(f"Converted to UUID: {user_uuid} (type: {type(user_uuid)})")

        async with get_database() as db:
            print("Calling get_or_create_credit_account...")
            # Use the EXACT same function as credit API
            credit_account = await get_or_create_credit_account(user_uuid, db)

            print(f"Result: {credit_account}")
            print(f"Available credits: {credit_account.available_credits}")
            print(f"Total credits: {credit_account.total_credits}")

            return {
                "available_credits": float(credit_account.available_credits),
                "total_earned": float(credit_account.total_credits),
                "credit_tier": "premium" if credit_account.available_credits > 100 else "basic"
            }

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"available_credits": 0}

if __name__ == "__main__":
    result = asyncio.run(debug_orchestrator_credit())
    print(f"Final result: {result}")