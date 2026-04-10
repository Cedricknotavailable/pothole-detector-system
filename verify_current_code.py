#!/usr/bin/env python3
"""
Script to verify the current code has the updated notification messages
"""

def check_current_code():
    """Check if the current app.py has the updated notification code"""
    
    print("=== Checking Current Code in app.py ===")
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Check for new notification message patterns
    checks = [
        # Community flagging checks
        ('Community: Gets threshold setting', 'false_report_threshold = 5' in content),
        ('Community: Calculates remaining flags', 'remaining_flags = max(0, false_report_threshold - author.false_reports_count)' in content),
        ('Community: Includes count in message', 'You have submitted {author.false_reports_count} false report(s)' in content),
        ('Community: Includes remaining warning', '{remaining_flags} more false report(s) will result in account suspension' in content),
        ('Community: Identifies source', 'flagged as a false report and removed by the community' in content),
        
        # Admin/moderator flagging checks  
        ('Admin: Calculates remaining flags', 'remaining_flags = max(0, threshold - user.false_reports_count)' in content),
        ('Admin: Includes count in message', 'You have submitted {user.false_reports_count} false report(s)' in content),
        ('Admin: Uses admin/moderator access', '_require_admin_or_moderator()' in content),
        
        # Old message patterns (should NOT exist)
        ('OLD: Simple community message', 'has been flagged as false by the community.' in content and 'You have submitted' not in content),
        ('OLD: Simple repeated message', 'Repeated false reports may lead to account suspension.' in content),
    ]
    
    print("Code Analysis:")
    for description, result in checks:
        status = "✅" if result else "❌"
        if description.startswith('OLD:'):
            status = "❌" if result else "✅"  # Reverse for old patterns
        print(f"  {status} {description}")
    
    # Check specific notification creation lines
    print("\n=== Notification Message Lines ===")
    
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'Your report' in line and 'flagged as a false report' in line:
            print(f"Line {i}: {line.strip()}")
    
    # Look for the specific old message
    old_message_found = 'Please ensure your reports are accurate. Repeated false reports may lead to account suspension.' in content
    print(f"\n❌ Old message pattern found: {old_message_found}")
    
    if old_message_found:
        print("\n🚨 ISSUE DETECTED: The old notification message is still in the code!")
        print("This means the Flask app is using cached/old code.")
        print("\nSOLUTION: Restart the Flask application to load the updated code.")
    else:
        print("\n✅ Code appears to be updated correctly.")
        print("If you're still seeing old notifications, the Flask app needs to be restarted.")

if __name__ == '__main__':
    check_current_code()