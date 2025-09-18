#!/usr/bin/env python3
"""
Direct database fix for admin credits
"""

import sqlite3
import uuid
from datetime import datetime

def fix_admin_credits():
    """Add credits directly to admin user in local database."""

    print("FIXING ADMIN CREDITS IN LOCAL DATABASE")
    print("=" * 50)

    conn = None
    try:
        # Connect to local database
        conn = sqlite3.connect('cryptouniverse.db')
        cursor = conn.cursor()

        # Find admin user
        cursor.execute("SELECT id, email, role FROM users WHERE email = ?", ("admin@cryptouniverse.com",))
        admin_user = cursor.fetchone()

        if not admin_user:
            print("Admin user not found in local database")
            return False

        user_id, email, role = admin_user
        print(f"Found admin user: {email} (ID: {user_id}, Role: {role})")

        # Get existing credit account info (ID and current balances) upfront
        cursor.execute("""
            SELECT id, total_credits, available_credits, used_credits, expired_credits
            FROM credit_accounts WHERE user_id = ?
        """, (user_id,))
        account_info = cursor.fetchone()

        if account_info:
            # Account exists - get current values
            account_id, prev_total, prev_available, prev_used, prev_expired = account_info
            print(f"Credit account already exists (ID: {account_id})")

            # Calculate new balances
            new_total = prev_total + 1000
            new_available = prev_available + 1000
            balance_before = prev_available
            balance_after = new_available

            # Update existing account
            cursor.execute("""
                UPDATE credit_accounts
                SET total_credits = ?, available_credits = ?, updated_at = ?
                WHERE id = ?
            """, (new_total, new_available, datetime.utcnow().isoformat(), account_id))
            print(f"Added 1000 credits to existing account (Total: {new_total}, Available: {new_available})")

        else:
            # Create new credit account
            account_id = str(uuid.uuid4())
            balance_before = 0
            balance_after = 1000

            cursor.execute("""
                INSERT INTO credit_accounts (
                    id, user_id, total_credits, available_credits,
                    used_credits, expired_credits, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account_id, user_id, 1000, 1000, 0, 0,
                datetime.utcnow().isoformat(), datetime.utcnow().isoformat()
            ))
            print("Created new credit account with 1000 credits")

        # Add credit transaction record using the account_id (idempotent)
        # Create stable reference_id for idempotency
        reference_id = f"admin_grant:{account_id}"

        # Check if provider column exists in schema
        cursor.execute("PRAGMA table_info(credit_transactions)")
        columns = [row[1] for row in cursor.fetchall()]
        has_provider_column = 'provider' in columns

        if has_provider_column:
            # Check if transaction already exists with new schema
            cursor.execute("""
                SELECT id FROM credit_transactions
                WHERE provider = ? AND reference_id = ?
            """, ('local', reference_id))
            existing_transaction = cursor.fetchone()

            if existing_transaction:
                print(f"Credit transaction already exists (ID: {existing_transaction[0]}) - skipping")
            else:
                # Insert with provider column
                transaction_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO credit_transactions (
                        id, account_id, transaction_type, amount,
                        description, reference_id, balance_before, balance_after,
                        source, status, provider, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transaction_id, account_id, 'bonus', 1000,
                    'Admin testing credits', reference_id,
                    balance_before, balance_after,
                    'admin_script', 'completed', 'local', datetime.utcnow().isoformat()
                ))
                print("Added credit transaction record with provider")
        else:
            # Fallback for older schema without provider column
            cursor.execute("""
                SELECT id FROM credit_transactions
                WHERE reference_id = ?
            """, (reference_id,))
            existing_transaction = cursor.fetchone()

            if existing_transaction:
                print(f"Credit transaction already exists (ID: {existing_transaction[0]}) - skipping")
            else:
                # Insert without provider column
                transaction_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO credit_transactions (
                        id, account_id, transaction_type, amount,
                        description, reference_id, balance_before, balance_after,
                        source, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transaction_id, account_id, 'bonus', 1000,
                    'Admin testing credits', reference_id,
                    balance_before, balance_after,
                    'admin_script', 'completed', datetime.utcnow().isoformat()
                ))
                print("Added credit transaction record (legacy schema)")

        # Commit changes
        conn.commit()

        # Verify the fix using correct column names
        cursor.execute("""
            SELECT total_credits, available_credits, used_credits, expired_credits
            FROM credit_accounts WHERE user_id = ?
        """, (user_id,))

        credits_info = cursor.fetchone()
        if credits_info:
            total, available, used, expired = credits_info
            print(f"\nCREDIT ACCOUNT VERIFICATION:")
            print(f"Total credits: {total}")
            print(f"Available credits: {available}")
            print(f"Used credits: {used}")
            print(f"Expired credits: {expired}")
            print("\nSUCCESS: Admin credits fixed!")

        return True

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def check_database_structure():
    """Check database tables to understand structure."""

    print("\nCHECKING DATABASE STRUCTURE...")

    try:
        conn = sqlite3.connect('cryptouniverse.db')
        cursor = conn.cursor()

        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print(f"Database tables: {[t[0] for t in tables]}")

        # Check users table structure
        if any('users' in str(t) for t in tables):
            cursor.execute("PRAGMA table_info(users)")
            user_columns = cursor.fetchall()
            print(f"Users table columns: {[col[1] for col in user_columns]}")

        # Check credit tables
        credit_tables = [t[0] for t in tables if 'credit' in t[0].lower()]
        if credit_tables:
            print(f"Credit tables: {credit_tables}")
            for table in credit_tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                print(f"{table} columns: {[col[1] for col in columns]}")

        conn.close()

    except Exception as e:
        print(f"Error checking database: {e}")

def main():
    print("ADMIN CREDIT DATABASE FIX")
    print("=" * 30)

    # First check database structure
    check_database_structure()

    # Then try to fix credits
    success = fix_admin_credits()

    if success:
        print("\nNEXT STEPS:")
        print("1. Restart the application if needed")
        print("2. Login to check if credits now show correctly")
        print("3. Try purchasing strategies from marketplace")
    else:
        print("\nFIX FAILED - May need to:")
        print("1. Check if database schema matches expected structure")
        print("2. Run database migrations first")
        print("3. Use production database instead of local")

if __name__ == "__main__":
    main()