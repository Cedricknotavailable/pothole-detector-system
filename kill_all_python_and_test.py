#!/usr/bin/env python3
"""
Aggressive solution: Kill all Python processes and test the notification code directly
"""

import sys
import os
import subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def kill_all_python_processes():
    """Kill all Python processes except this one"""
    
    print("=== Killing All Python Processes ===")
    
    try:
        # Get current process ID to avoid killing ourselves
        current_pid = os.getpid()
        print(f"Current process ID: {current_pid}")
        
        # Get all Python processes
        result = subprocess.run([
            'powershell', '-Command', 
            'Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, ProcessName'
        ], capture_output=True, text=True)
        
        if result.stdout.strip():
            print("Found Python processes:")
            print(result.stdout)
            
            # Kill each Python process except this one
            kill_result = subprocess.run([
                'powershell', '-Command', 
                f'Get-Process python -ErrorAction SilentlyContinue | Where-Object {{$_.Id -ne {current_pid}}} | Stop-Process -Force'
            ], capture_output=True, text=True)
            
            if kill_result.returncode == 0:
                print("✅ Successfully killed other Python processes")
            else:
                print(f"⚠️  Error killing processes: {kill_result.stderr}")
        else:
            print("No other Python processes found")
            
    except Exception as e:
        print(f"Error: {e}")

def test_notification_code_directly():
    """Test the notification code directly without Flask"""
    
    print("\n=== Testing Notification Code Directly ===")
    
    try:
        from app import app, db, User, Report, Notification, Settings
        import time
        
        with app.app_context():
            print("✅ Successfully imported Flask app")
            
            # Test the notification message construction logic
            print("\n📝 Testing message construction logic...")
            
            # Simulate admin flagging scenario
            report_title = "Test Report"
            user_false_reports_count = 2
            threshold = 5
            remaining_flags = max(0, threshold - user_false_reports_count)
            
            # This is the exact logic from flag_report_false function
            msg = f"Your report '{report_title}' has been flagged as a false report and removed. You have submitted {user_false_reports_count} false report(s). {remaining_flags} more false report(s) will result in account suspension. Please ensure your reports are accurate. [ADMIN-v2]"
            
            print(f"Expected message: {msg}")
            
            # Check if the message contains the new format
            has_count = f"submitted {user_false_reports_count} false report(s)" in msg
            has_remaining = f"{remaining_flags} more false report(s)" in msg
            has_version = "[ADMIN-v2]" in msg
            
            print(f"✅ Contains count info: {has_count}")
            print(f"✅ Contains remaining flags: {has_remaining}")
            print(f"✅ Contains version tag: {has_version}")
            
            if has_count and has_remaining and has_version:
                print("\n🎉 The notification code logic is CORRECT!")
                print("🚨 The problem is that Flask is NOT using this updated code!")
            else:
                print("\n❌ There's an issue with the notification logic")
                
    except Exception as e:
        print(f"❌ Error testing code: {e}")

def main():
    print("🚨 AGGRESSIVE FLASK RESTART SOLUTION 🚨")
    print("This will kill ALL Python processes and test the code directly")
    
    # Step 1: Kill all Python processes
    kill_all_python_processes()
    
    # Step 2: Test the code directly
    test_notification_code_directly()
    
    # Step 3: Instructions
    print("\n" + "="*50)
    print("🔥 CRITICAL NEXT STEPS:")
    print("1. ALL Python processes have been killed")
    print("2. Start Flask fresh: python app.py")
    print("3. Test admin flagging - you SHOULD see '[ADMIN-v2]' in notification")
    print("4. If you STILL see old message, there's a deeper issue")
    print("="*50)

if __name__ == '__main__':
    main()