#!/usr/bin/env python3
"""
Script to create a new user account: testuser10
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
from werkzeug.security import generate_password_hash
import time

def create_testuser10():
    """Create testuser10 with specified credentials"""
    
    with app.app_context():
        print("=== Creating testuser10 Account ===")
        
        # Check if user already exists
        existing_user = User.query.filter_by(username='testuser10').first()
        if existing_user:
            print("❌ User 'testuser10' already exists!")
            print(f"   Current role: {existing_user.role}")
            print(f"   Current status: {existing_user.status}")
            print(f"   Current email: {existing_user.email}")
            return False
        
        # Create new user
        try:
            # Hash the password
            password_hash = generate_password_hash('12345678Jj!')
            
            # Create user object
            new_user = User(
                username='testuser10',
                email='testuser10@example.com',  # Default email
                password_hash=password_hash,
                role='user',  # Default role
                status='active',
                created_at=int(time.time()),
                false_reports_count=0
            )
            
            # Add to database
            db.session.add(new_user)
            db.session.commit()
            
            print("✅ Successfully created testuser10!")
            print(f"   Username: testuser10")
            print(f"   Password: 12345678Jj!")
            print(f"   Email: testuser10@example.com")
            print(f"   Role: user")
            print(f"   Status: active")
            print(f"   User ID: {new_user.id}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating user: {str(e)}")
            return False

if __name__ == '__main__':
    success = create_testuser10()
    if success:
        print("\n🎉 testuser10 is ready to use!")
        print("You can now log in with:")
        print("Username: testuser10")
        print("Password: 12345678Jj!")
    else:
        print("\n💥 Failed to create testuser10")