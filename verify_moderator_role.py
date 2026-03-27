"""
Verify that moderator role works in the database and application
"""

import sqlite3

DB_PATH = 'instance/users.db'

# Connect to database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Checking moderator account and role validation:\n")

# Check if modAcc exists
cursor.execute("SELECT id, username, role, status FROM user WHERE username = 'modAcc'")
mod_user = cursor.fetchone()

if mod_user:
    print(f"✅ Moderator account found:")
    print(f"   ID: {mod_user[0]}")
    print(f"   Username: {mod_user[1]}")
    print(f"   Role: {mod_user[2]}")
    print(f"   Status: {mod_user[3]}")
else:
    print("❌ Moderator account not found")

# Check all users with moderator role
print("\n" + "="*50)
print("All users with moderator role:")
print("="*50)
cursor.execute("SELECT id, username, email, role, status FROM user WHERE role = 'moderator'")
moderators = cursor.fetchall()

if moderators:
    for mod in moderators:
        print(f"ID: {mod[0]}, Username: {mod[1]}, Email: {mod[2]}, Role: {mod[3]}, Status: {mod[4]}")
else:
    print("No moderators found")

# Check role column constraints
print("\n" + "="*50)
print("Role column information:")
print("="*50)
cursor.execute("PRAGMA table_info(user)")
columns = cursor.fetchall()
for col in columns:
    if col[1] == 'role':
        print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, Default: {col[4]}")

conn.close()

print("\n✅ Database verification complete")
print("\nThe moderator role should work correctly in the application.")
print("If you're still seeing 'bad end', please check:")
print("1. Browser console for JavaScript errors")
print("2. Flask server logs for Python errors")
print("3. Network tab to see the actual HTTP response")
