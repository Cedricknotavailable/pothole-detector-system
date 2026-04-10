#!/usr/bin/env python3
"""
Test script to verify the current notification code works correctly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Notification, User, Report, Settings

def test_notification_logic():
    """Test the notification logic directly"""
    
    with app.app_context():
        print("=== Testing Notification Logic ===")
        
        # Test the logic for creating admin notification message
        user_false_reports_count = 2
        threshold = 5
        remaining_flags = max(0, threshold - user_false_reports_count)
        report_title = "Test Report"
        
        # Admin notification message (should have [ADMIN-v2] tag)
        admin_msg = f"Your report '{report_title}' has been flagged as a false report and removed. You have submitted {user_false_reports_count} false report(s). {remaining_flags} more false report(s) will result in account suspension. Please ensure your reports are accurate. [ADMIN-v2]"
        
        print("Expected Admin Message:")
        print(admin_msg)
        print()
        
        # Community notification message (should have [COMMUNITY-v2] tag)
        community_msg = f"Your report '{report_title}' has been flagged as a false report and removed by the community. You have submitted {user_false_reports_count} false report(s). {remaining_flags} more false report(s) will result in account suspension. Please ensure your reports are accurate. [COMMUNITY-v2]"
        
        print("Expected Community Message:")
        print(community_msg)
        print()
        
        # Check if the functions exist in the current app context
        from app import flag_report_false, flag_report
        print("✓ flag_report_false function exists")
        print("✓ flag_report function exists")
        
        # Check the source code of the functions to see if they have the updated logic
        import inspect
        
        print("\n=== Checking flag_report_false source ===")
        source = inspect.getsource(flag_report_false)
        if "[ADMIN-v2]" in source:
            print("✓ flag_report_false contains [ADMIN-v2] tag")
        else:
            print("✗ flag_report_false does NOT contain [ADMIN-v2] tag")
            
        if "false_reports_count" in source and "remaining_flags" in source:
            print("✓ flag_report_false contains count logic")
        else:
            print("✗ flag_report_false does NOT contain count logic")
        
        print("\n=== Checking flag_report source ===")
        source = inspect.getsource(flag_report)
        if "[COMMUNITY-v2]" in source:
            print("✓ flag_report contains [COMMUNITY-v2] tag")
        else:
            print("✗ flag_report does NOT contain [COMMUNITY-v2] tag")
            
        if "false_reports_count" in source and "remaining_flags" in source:
            print("✓ flag_report contains count logic")
        else:
            print("✗ flag_report does NOT contain count logic")

if __name__ == '__main__':
    test_notification_logic()