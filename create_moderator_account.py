"""
Script to create a moderator account in the database
Username: modAcc
Password: Password1!
Role: moderator
"""

import sqlite3
from werkzeug.security import generate_password_hash

# Database path
DB_PATH = 'instance/users.db'

# Account details
USERNAME = 'modAcc'
EMAIL = 'moderator@surveyor.ai'
PASSWORD = 'Password1!'
ROLE = 'moderator'
STATUS = 'active'

# Generate password hash
password_hash = generate_password_hash(PASSWORD)

# Connect to database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Check if username already exists
    cursor.execute("SELECT id FROM user WHERE username = ?", (USERNAME,))
    existing = cursor.fetchone()
    
    if existing:
        print(f"❌ User '{USERNAME}' already exists with ID {existing[0]}")
    else:
        # Insert new user
        cursor.execute("""
            INSERT INTO user (username, email, password_hash, role, status)
            VALUES (?, ?, ?, ?, ?)
        """, (USERNAME, EMAIL, password_hash, ROLE, STATUS))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        print(f"✅ Moderator account created successfully!")
        print(f"   ID: {user_id}")
        print(f"   Username: {USERNAME}")
        print(f"   Email: {EMAIL}")
        print(f"   Role: {ROLE}")
        print(f"   Status: {STATUS}")
        print(f"\n   Login credentials:")
        print(f"   Username: {USERNAME}")
        print(f"   Password: {PASSWORD}")
        
except Exception as e:
    print(f"❌ Error creating account: {e}")
    conn.rollback()
finally:
    conn.close()
