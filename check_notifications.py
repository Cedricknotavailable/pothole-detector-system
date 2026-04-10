#!/usr/bin/env python3
"""
Script to check what notifications exist in the database for false report flagging
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Notification, User

def check_notifications():
    """Check existing notifications in the database"""
    
    with app.app_context():
        print("=== Checking False Report Notifications ===")
        
        # Get all notifications with "Report Flagged as False" title
        notifications = Notification.query.filter(
            Notification.title.like('%Report Flagged as False%')
        ).order_by(Notification.id.desc()).limit(10).all()
        
        if not notifications:
            print("No false report notifications found in database.")
            return
        
        print(f"Found {len(notifications)} recent false report notifications:")
        print()
        
        for i, notif in enumerate(notifications, 1):
            # Get user info
            user = User.query.get(notif.user_id)
            username = user.username if user else f"User ID {notif.user_id}"
            
            print(f"--- Notification {i} ---")
            print(f"ID: {notif.id}")
            print(f"User: {username}")
            print(f"Title: {notif.title}")
            print(f"Message: {notif.message}")
            print(f"Created: {getattr(notif, 'created_at', 'N/A')}")
            print()
        
        # Check if there are users with false report counts
        print("=== Users with False Report Counts ===")
        users_with_false_reports = User.query.filter(User.false_reports_count > 0).all()
        
        if not users_with_false_reports:
            print("No users with false report counts found.")
        else:
            for user in users_with_false_reports:
                print(f"User: {user.username}, False Reports: {user.false_reports_count}, Status: {user.status}")

if __name__ == '__main__':
    check_notifications()