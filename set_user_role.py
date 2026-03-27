"""
Script to manually set a user's role in the database
Usage: python set_user_role.py <username> <role>
Example: python set_user_role.py modAcc moderator
"""

import sys
import sqlite3

DB_PATH = 'instance/users.db'

if len(sys.argv) != 3:
    print("Usage: python set_user_role.py <username> <role>")
    print("Example: python set_user_role.py modAcc moderator")
    print("Valid roles: admin, moderator, user")
    sys.exit(1)

username = sys.argv[1]
new_role = sys.argv[2].lower()

ALLOWED_ROLES = {'admin', 'moderator', 'user'}

if new_role not in ALLOWED_ROLES:
    print(f"❌ Invalid role: {new_role}")
    print(f"Valid roles: {', '.join(ALLOWED_ROLES)}")
    sys.exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Check if user exists
    cursor.execute("SELECT id, username, role FROM user WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if not user:
        print(f"❌ User '{username}' not found")
        sys.exit(1)
    
    user_id, current_username, current_role = user
    print(f"Found user: ID={user_id}, Username={current_username}, Current Role={current_role}")
    
    # Update role
    cursor.execute("UPDATE user SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    
    # Verify update
    cursor.execute("SELECT role FROM user WHERE id = ?", (user_id,))
    updated_role = cursor.fetchone()[0]
    
    print(f"✅ Successfully updated role from '{current_role}' to '{updated_role}'")
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    conn.close()
