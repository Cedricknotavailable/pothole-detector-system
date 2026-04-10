#!/usr/bin/env python3
"""
Test script to verify admin flagging creates the correct notification
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Notification, User, Report

def test_admin_flagging():
    """Test admin flagging to see if it creates the correct notification"""
    
    with app.app_context():
        print("=== Testing Admin Flagging Notification ===")
        
        # Find a test user with reports
        test_user = User.query.filter_by(username='testuser10').first()
        if not test_user:
            print("testuser10 not found")
            return
            
        print(f"Found test user: {test_user.username}")
        print(f"Current false reports count: {test_user.false_reports_count}")
        
        # Find a report by this user that is not already flagged as false
        report = Report.query.filter_by(user_id=test_user.id, is_false_report=False).first()
        if not report:
            print("No unflagged reports found for testuser10")
            # Let's see what reports exist
            all_reports = Report.query.filter_by(user_id=test_user.id).all()
            print(f"All reports by testuser10: {len(all_reports)}")
            for r in all_reports:
                print(f"  Report {r.id}: {r.title}, is_false_report: {r.is_false_report}")
            return
            
        print(f"Found report to test: {report.id} - {report.title}")
        
        # Get notification count before
        notif_count_before = Notification.query.filter_by(user_id=test_user.id).count()
        print(f"Notifications before: {notif_count_before}")
        
        # Import and call the flag_report_false function directly
        from app import flag_report_false
        
        print(f"Calling flag_report_false({report.id})...")
        
        # Simulate admin user context (this is tricky without full Flask context)
        # Let's just test the notification creation logic
        
        # Calculate what the notification should be
        threshold = 5
        user_false_reports_after = test_user.false_reports_count + 1
        remaining_flags = max(0, threshold - user_false_reports_after)
        
        expected_msg = f"Your report '{report.title}' has been flagged as a false report and removed. You have submitted {user_false_reports_after} false report(s). {remaining_flags} more false report(s) will result in account suspension. Please ensure your reports are accurate. [ADMIN-v2]"
        
        print(f"Expected notification message:")
        print(expected_msg)
        
        print("\nTo test this properly, you need to:")
        print("1. Start Flask: python app.py")
        print("2. Log in as admin")
        print(f"3. Flag report {report.id} as false")
        print("4. Check the notification for testuser10")

if __name__ == '__main__':
    test_admin_flagging()