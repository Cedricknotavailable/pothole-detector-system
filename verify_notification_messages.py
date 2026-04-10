#!/usr/bin/env python3
"""
Verification script to check that both community and admin/moderator flagging 
provide detailed count information in notifications.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_notification_implementations():
    """Verify both flagging functions include count information"""
    
    print("=== Verifying Notification Message Implementations ===")
    
    with open('app.py', 'r') as f:
        app_content = f.read()
    
    # Check 1: Community flagging includes count information
    community_checks = [
        'false_report_threshold = 5' in app_content,
        'author.false_reports_count += 1' in app_content,
        'remaining_flags = max(0, false_report_threshold - author.false_reports_count)' in app_content,
        'You have submitted {author.false_reports_count} false report(s)' in app_content,
        '{remaining_flags} more false report(s) will result in account suspension' in app_content,
        'flagged as a false report and removed by the community' in app_content
    ]
    
    print("Community Flagging Checks:")
    community_labels = [
        "Gets false report threshold setting",
        "Increments author's false report count", 
        "Calculates remaining flags",
        "Includes current count in message",
        "Includes remaining flags warning",
        "Identifies community as source"
    ]
    
    for i, (check, label) in enumerate(zip(community_checks, community_labels)):
        print(f"  ✓ {label}: {check}")
    
    # Check 2: Admin/Moderator flagging includes count information  
    admin_checks = [
        'user.false_reports_count += 1' in app_content,
        'remaining_flags = max(0, threshold - user.false_reports_count)' in app_content,
        'You have submitted {user.false_reports_count} false report(s)' in app_content,
        '{remaining_flags} more false report(s) will result in account suspension' in app_content,
        '_require_admin_or_moderator()' in app_content
    ]
    
    print("\nAdmin/Moderator Flagging Checks:")
    admin_labels = [
        "Increments user's false report count",
        "Calculates remaining flags", 
        "Includes current count in message",
        "Includes remaining flags warning",
        "Requires admin or moderator access"
    ]
    
    for i, (check, label) in enumerate(zip(admin_checks, admin_labels)):
        print(f"  ✓ {label}: {check}")
    
    # Check 3: Both handle account locking
    locking_checks = [
        'author.status = \'locked\'' in app_content,  # Community flagging
        'user.status = \'locked\'' in app_content,    # Admin flagging
        'User Auto-Locked' in app_content,
        'account has been locked due to submitting' in app_content
    ]
    
    print("\nAccount Locking Checks:")
    locking_labels = [
        "Community flagging can lock accounts",
        "Admin flagging can lock accounts",
        "Notifies admins about auto-lock",
        "Informs user about account lock"
    ]
    
    for i, (check, label) in enumerate(zip(locking_checks, locking_labels)):
        print(f"  ✓ {label}: {check}")
    
    # Summary
    all_checks = community_checks + admin_checks + locking_checks
    
    print(f"\n=== Summary ===")
    if all(all_checks):
        print("✅ All checks passed! Both flagging methods now provide detailed count information.")
        print("\nExpected notification messages:")
        print("\n📧 Community Flagging (Active User):")
        print("'Your report '[TITLE]' has been flagged as a false report and removed by the community. You have submitted [COUNT] false report(s). [REMAINING] more false report(s) will result in account suspension. Please ensure your reports are accurate.'")
        
        print("\n📧 Admin/Moderator Flagging (Active User):")
        print("'Your report '[TITLE]' has been flagged as a false report and removed. You have submitted [COUNT] false report(s). [REMAINING] more false report(s) will result in account suspension. Please ensure your reports are accurate.'")
        
        print("\n📧 Account Locked (Both Methods):")
        print("'Your report '[TITLE]' has been flagged as a false report and removed [by the community]. Your account has been locked due to submitting [COUNT] false reports.'")
        
    else:
        print("❌ Some checks failed. Please review the implementation.")
        failed_count = sum(1 for check in all_checks if not check)
        print(f"Failed checks: {failed_count}/{len(all_checks)}")

if __name__ == '__main__':
    verify_notification_implementations()