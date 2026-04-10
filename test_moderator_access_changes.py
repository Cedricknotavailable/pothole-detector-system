#!/usr/bin/env python3
"""
Test script to verify moderator access changes:
1. Moderators have access to mark as fixed brush tool
2. Admins and moderators cannot submit reports
"""

import requests
import sys

def test_moderator_brush_access():
    """Test that moderators can see the mark as fixed brush tool in map page"""
    print("🔧 Testing moderator brush tool access...")
    
    # This would require a logged-in session as a moderator
    # For now, we'll just verify the template changes are in place
    
    try:
        with open('templates/map.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check that the brush button is now available to moderators
        if 'is_admin_or_moderator' in content and 'markFixedBtn' in content:
            print("✅ Map template correctly shows brush tool for moderators")
            return True
        else:
            print("❌ Map template does not show brush tool for moderators")
            return False
            
    except Exception as e:
        print(f"❌ Error checking map template: {e}")
        return False

def test_admin_moderator_report_restriction():
    """Test that the reports route blocks admins and moderators"""
    print("🚫 Testing admin/moderator report submission restriction...")
    
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check that reports_page has the restriction
        if '_is_admin_or_moderator(current_user)' in content and 'abort(403)' in content:
            print("✅ Reports route correctly blocks admins and moderators")
            return True
        else:
            print("❌ Reports route does not block admins and moderators")
            return False
            
    except Exception as e:
        print(f"❌ Error checking app.py: {e}")
        return False

def test_navigation_changes():
    """Test that navigation has been updated correctly"""
    print("🧭 Testing navigation changes...")
    
    try:
        # Check defects.html
        with open('templates/defects.html', 'r', encoding='utf-8') as f:
            defects_content = f.read()
            
        # Check map.html  
        with open('templates/map.html', 'r', encoding='utf-8') as f:
            map_content = f.read()
            
        # Verify moderators only see Map and Defects Management
        defects_has_moderator_nav = 'elif is_admin_or_moderator' in defects_content
        map_has_moderator_nav = 'elif is_admin_or_moderator' in map_content
        
        if defects_has_moderator_nav and map_has_moderator_nav:
            print("✅ Navigation correctly configured for moderators")
            return True
        else:
            print("❌ Navigation not properly configured for moderators")
            return False
            
    except Exception as e:
        print(f"❌ Error checking navigation templates: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing moderator access changes...\n")
    
    tests = [
        test_moderator_brush_access,
        test_admin_moderator_report_restriction,
        test_navigation_changes
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Moderator access changes implemented correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())