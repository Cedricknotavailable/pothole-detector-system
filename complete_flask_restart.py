#!/usr/bin/env python3
"""
Complete Flask restart script to ensure updated code is loaded
"""

import os
import sys
import subprocess
import time
import shutil

def complete_restart():
    """Perform a complete restart of the Flask environment"""
    
    print("=== Complete Flask Restart Process ===")
    
    # 1. Kill any existing Python processes
    print("1. Killing any existing Python processes...")
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['taskkill', '/f', '/im', 'python.exe'], 
                         capture_output=True, text=True)
            subprocess.run(['taskkill', '/f', '/im', 'pythonw.exe'], 
                         capture_output=True, text=True)
        else:  # Unix-like
            subprocess.run(['pkill', '-f', 'python'], 
                         capture_output=True, text=True)
    except Exception as e:
        print(f"   Note: {e}")
    
    # 2. Clear Python cache
    print("2. Clearing Python cache...")
    cache_dirs = []
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                cache_dirs.append(os.path.join(root, dir_name))
    
    for cache_dir in cache_dirs:
        try:
            shutil.rmtree(cache_dir)
            print(f"   Removed: {cache_dir}")
        except Exception as e:
            print(f"   Could not remove {cache_dir}: {e}")
    
    # 3. Clear .pyc files
    print("3. Clearing .pyc files...")
    pyc_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                pyc_files.append(os.path.join(root, file))
    
    for pyc_file in pyc_files:
        try:
            os.remove(pyc_file)
            print(f"   Removed: {pyc_file}")
        except Exception as e:
            print(f"   Could not remove {pyc_file}: {e}")
    
    # 4. Wait a moment
    print("4. Waiting for cleanup...")
    time.sleep(2)
    
    # 5. Test import
    print("5. Testing fresh import...")
    try:
        # Clear module cache
        modules_to_clear = [name for name in sys.modules.keys() if name.startswith('app')]
        for module in modules_to_clear:
            del sys.modules[module]
        
        # Fresh import
        from app import app, flag_report_false, flag_report
        print("   ✓ Fresh import successful")
        
        # Verify the functions have the updated code
        import inspect
        source_false = inspect.getsource(flag_report_false)
        source_community = inspect.getsource(flag_report)
        
        if "[ADMIN-v2]" in source_false and "[COMMUNITY-v2]" in source_community:
            print("   ✓ Updated notification code confirmed")
        else:
            print("   ✗ Updated notification code NOT found")
            
    except Exception as e:
        print(f"   ✗ Import failed: {e}")
    
    print("\n=== Restart Complete ===")
    print("You can now start Flask with: python app.py")
    print("The updated notification code should now be active.")

if __name__ == '__main__':
    complete_restart()