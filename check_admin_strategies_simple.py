import sqlite3
import sys

def check_admin_strategies():
    try:
        conn = sqlite3.connect('cryptouniverse.db')
        cursor = conn.cursor()

        # Check admin users
        cursor.execute('SELECT id, email, role FROM users WHERE role = "admin"')
        admin_users = cursor.fetchall()
        print('Admin users:', admin_users)

        if admin_users:
            user_id = admin_users[0][0]

            # Check user strategies
            cursor.execute('SELECT COUNT(*) FROM user_strategies WHERE user_id = ?', (user_id,))
            count = cursor.fetchone()[0]
            print(f'Strategies for admin user {user_id}: {count}')

            # Get strategy IDs
            cursor.execute('SELECT strategy_id FROM user_strategies WHERE user_id = ?', (user_id,))
            strategies = cursor.fetchall()
            print('Strategy IDs:', strategies)

            # Check available strategies in marketplace
            cursor.execute('SELECT COUNT(*) FROM strategies')
            total_strategies = cursor.fetchone()[0]
            print(f'Total strategies in marketplace: {total_strategies}')

        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_admin_strategies()