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

        # Check if credit account exists
        cursor.execute("SELECT * FROM credit_accounts WHERE user_id = ?", (user_id,))
        credit_account = cursor.fetchone()

        if credit_account:
            print("Credit account already exists")
            # Update existing account
            cursor.execute("""
                UPDATE credit_accounts
                SET total_credits = total_credits + 1000,
                    available_credits = available_credits + 1000,
                    total_earned_credits = total_earned_credits + 1000,
                    updated_at = ?
                WHERE user_id = ?
            """, (datetime.utcnow().isoformat(), user_id))
            print("Added 1000 credits to existing account")
        else:
            # Create new credit account
            account_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO credit_accounts (
                    id, user_id, total_credits, available_credits,
                    total_earned_credits, total_spent_credits,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account_id, user_id, 1000, 1000, 1000, 0,
                datetime.utcnow().isoformat(), datetime.utcnow().isoformat()
            ))
            print("Created new credit account with 1000 credits")

        # Add credit transaction record
        transaction_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO credit_transactions (
                id, user_id, transaction_type, amount,
                description, reference_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_id, user_id, 'EARNED', 1000,
            'Admin testing credits', 'admin_local_provision',
            datetime.utcnow().isoformat()
        ))
        print("Added credit transaction record")

        # Commit changes
        conn.commit()

        # Verify the fix
        cursor.execute("""
            SELECT total_credits, available_credits, total_earned_credits
            FROM credit_accounts WHERE user_id = ?
        """, (user_id,))

        credits_info = cursor.fetchone()
        if credits_info:
            total, available, earned = credits_info
            print(f"\nCREDIT ACCOUNT VERIFICATION:")
            print(f"Total credits: {total}")
            print(f"Available credits: {available}")
            print(f"Total earned: {earned}")
            print("\nSUCCESS: Admin credits fixed!")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

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