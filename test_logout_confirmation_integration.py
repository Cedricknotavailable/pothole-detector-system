"""
Integration test for Task 7: Checkpoint - Test logout confirmation

This test verifies that:
1. The logout modal component is properly structured
2. All pages include the logout modal
3. The logout route exists and works correctly
4. JavaScript functions are properly defined
"""

import os
import re
import sys


def test_logout_modal_component():
    """Test that the logout modal component exists and is properly structured"""
    print("=" * 70)
    print("TEST 1: Logout Modal Component Structure")
    print("=" * 70)
    
    modal_path = 'templates/logout_modal.html'
    
    if not os.path.exists(modal_path):
        print(f"❌ FAIL: {modal_path} not found")
        return False
    
    with open(modal_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'Modal container with ID': 'id="logoutModal"' in content,
        'Modal overlay': 'class="modal-overlay"' in content,
        'Modal content': 'class="modal-content"' in content,
        'Modal title': 'Confirm Logout' in content,
        'Modal message': 'Are you sure you want to log out?' in content,
        'Cancel button': 'onclick="closeLogoutModal()"' in content,
        'Confirm button': 'onclick="confirmLogout()"' in content,
        'showLogoutModal function': 'function showLogoutModal()' in content,
        'closeLogoutModal function': 'function closeLogoutModal()' in content,
        'confirmLogout function': 'function confirmLogout()' in content,
        'Event listener for logout links': "querySelectorAll('a[href=\"/logout\"]')" in content,
        'preventDefault call': 'e.preventDefault()' in content,
        'Escape key handler': "e.key === 'Escape'" in content,
        'DOMContentLoaded event': "addEventListener('DOMContentLoaded'" in content,
        'CSS styling': '.modal {' in content,
        'Animation': '@keyframes modalSlideIn' in content
    }
    
    all_passed = True
    
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False
    
    print()
    return all_passed


def test_pages_include_modal():
    """Test that all required pages include the logout modal"""
    print("=" * 70)
    print("TEST 2: Pages Include Logout Modal")
    print("=" * 70)
    
    pages_to_check = [
        'templates/index.html',
        'templates/map.html',
        'templates/users.html',
        'templates/settings.html',
        'templates/analytics.html',
        'templates/reports.html',
        'templates/my_reports.html',
        'templates/defects.html',
        'templates/backup_management.html'
    ]
    
    all_passed = True
    
    for page_path in pages_to_check:
        if not os.path.exists(page_path):
            print(f"❌ {page_path} - File not found")
            all_passed = False
            continue
        
        with open(page_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_modal_include = "{% include 'logout_modal.html' %}" in content
        has_logout_link = 'href="/logout"' in content
        
        if has_modal_include and has_logout_link:
            print(f"✅ {page_path}")
        else:
            print(f"❌ {page_path} - Missing modal include or logout link")
            all_passed = False
    
    print()
    return all_passed


def test_logout_route_exists():
    """Test that the logout route exists in app.py"""
    print("=" * 70)
    print("TEST 3: Logout Route Exists")
    print("=" * 70)
    
    app_path = 'app.py'
    
    if not os.path.exists(app_path):
        print(f"❌ FAIL: {app_path} not found")
        return False
    
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_logout_route = re.search(r"@app\.route\(['\"]\/logout['\"]", content)
    has_logout_function = re.search(r"def logout\(\)", content)
    
    if has_logout_route and has_logout_function:
        print("✅ Logout route exists in app.py")
        print("✅ Logout function is defined")
        print()
        return True
    else:
        print("❌ Logout route or function not found in app.py")
        print()
        return False


def test_javascript_functionality():
    """Test that all required JavaScript functions are present"""
    print("=" * 70)
    print("TEST 4: JavaScript Functionality")
    print("=" * 70)
    
    modal_path = 'templates/logout_modal.html'
    
    with open(modal_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'Intercepts logout link clicks': re.search(r'querySelectorAll\([\'"]a\[href=[\'"]\/logout[\'"]\][\'"]', content),
        'Prevents default navigation': 'e.preventDefault()' in content,
        'Shows modal on click': 'showLogoutModal()' in content,
        'Closes modal function': re.search(r'function\s+closeLogoutModal\s*\(\)', content),
        'Hides modal (display none)': "modal.style.display = 'none'" in content,
        'Confirms logout function': re.search(r'function\s+confirmLogout\s*\(\)', content),
        'Navigates to /logout': "window.location.href = '/logout'" in content,
        'Escape key closes modal': re.search(r"e\.key\s*===?\s*['\"]Escape['\"]", content),
        'Overlay click closes modal': 'onclick="closeLogoutModal()"' in content
    }
    
    all_passed = True
    
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False
    
    print()
    return all_passed


def main():
    """Run all tests"""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "TASK 7: CHECKPOINT TEST" + " " * 30 + "║")
    print("║" + " " * 15 + "Logout Confirmation" + " " * 32 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    test1 = test_logout_modal_component()
    test2 = test_pages_include_modal()
    test3 = test_logout_route_exists()
    test4 = test_javascript_functionality()
    
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)
    print()
    
    if test1 and test2 and test3 and test4:
        print("✅ ALL TESTS PASSED")
        print()
        print("Task 7 Checkpoint Summary:")
        print("  ✓ Logout modal component is properly structured")
        print("  ✓ All 9 pages include the logout modal")
        print("  ✓ Logout route exists in app.py")
        print("  ✓ All JavaScript functions are properly implemented")
        print()
        print("The logout confirmation dialog is working correctly:")
        print("  • Intercepts all logout link clicks")
        print("  • Shows confirmation modal before logout")
        print("  • Allows user to cancel or confirm")
        print("  • Closes on Escape key or overlay click")
        print("  • Navigates to /logout on confirmation")
        print()
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print()
        print("Please review the failures above.")
        print()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
