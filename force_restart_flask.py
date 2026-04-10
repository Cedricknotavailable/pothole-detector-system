#!/usr/bin/env python3
"""
Script to force restart Flask and clear all caches
"""

import os
import sys
import subprocess
import shutil

def force_restart_flask():
    """Force restart Flask application and clear caches"""
    
    print("=== Force Restart Flask Application ===")
    
    # Step 1: Clear Python cache files
    print("1. Clearing Python cache files...")
    
    # Remove __pycache__ directories
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            cache_dir = os.path.join(root, '__pycache__')
            try:
                shutil.rmtree(cache_dir)
                print(f"   Removed: {cache_dir}")
            except Exception as e:
                print(f"   Failed to remove {cache_dir}: {e}")
    
    # Remove .pyc files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                pyc_file = os.path.join(root, file)
                try:
                    os.remove(pyc_file)
                    print(f"   Removed: {pyc_file}")
                except Exception as e:
                    print(f"   Failed to remove {pyc_file}: {e}")
    
    # Step 2: Check for running Python processes
    print("\n2. Checking for running Python processes...")
    
    try:
        # Use PowerShell to get Python processes
        result = subprocess.run([
            'powershell', '-Command', 
            'Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, StartTime | Format-Table -AutoSize'
        ], capture_output=True, text=True)
        
        if result.stdout.strip():
            print("   Found Python processes:")
            print(result.stdout)
            print("   ⚠️  You may need to manually stop these processes if they're running Flask")
        else:
            print("   No Python processes found")
            
    except Exception as e:
        print(f"   Error checking processes: {e}")
    
    # Step 3: Verify code changes
    print("\n3. Verifying code changes...")
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Check for version identifiers
    admin_v2 = '[ADMIN-v2]' in content
    community_v2 = '[COMMUNITY-v2]' in content
    
    print(f"   Admin notification v2: {'✅' if admin_v2 else '❌'}")
    print(f"   Community notification v2: {'✅' if community_v2 else '❌'}")
    
    # Step 4: Instructions
    print("\n4. Next Steps:")
    print("   📋 RESTART YOUR FLASK APPLICATION NOW")
    print("   🔄 Stop the current Flask process (Ctrl+C in terminal)")
    print("   ▶️  Start Flask again (python app.py or flask run)")
    print("   🧪 Test admin flagging - you should see '[ADMIN-v2]' in the notification")
    print("   🧪 Test community flagging - you should see '[COMMUNITY-v2]' in the notification")
    
    print("\n✅ Cache clearing complete!")
    print("🚨 IMPORTANT: You MUST restart Flask for changes to take effect!")

if __name__ == '__main__':
    force_restart_flask()