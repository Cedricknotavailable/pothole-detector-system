#!/usr/bin/env python3
"""
Verification script for Task 6.2: Implement logout confirmation JavaScript
Checks that all required JavaScript functionality is present in logout_modal.html
"""

import re
import sys

def verify_logout_modal_javascript():
    """Verify all required JavaScript functions and event handlers are present."""
    
    print("=" * 70)
    print("Task 6.2 Verification: Logout Confirmation JavaScript")
    print("=" * 70)
    print()
    
    # Read the logout_modal.html file
    try:
        with open('templates/logout_modal.html', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ FAILED: templates/logout_modal.html not found")
        return False
    
    all_passed = True
    
    # Test 1: Check for event listener that intercepts logout links
    print("Test 1: Event listener intercepts logout link clicks")
    if re.search(r'querySelectorAll\([\'"]a\[href=[\'"]\/logout[\'"]\][\'"]', content):
        print("  ✓ PASS: Event listener selects all logout links")
    else:
        print("  ✗ FAIL: Missing querySelectorAll for logout links")
        all_passed = False
    
    # Test 2: Check for preventDefault call
    print("\nTest 2: Prevent default navigation on logout click")
    if 'e.preventDefault()' in content or 'event.preventDefault()' in content:
        print("  ✓ PASS: preventDefault() called to stop navigation")
    else:
        print("  ✗ FAIL: Missing preventDefault() call")
        all_passed = False
    
    # Test 3: Check for showLogoutModal function call
    print("\nTest 3: Show modal on logout click")
    if 'showLogoutModal()' in content:
        print("  ✓ PASS: showLogoutModal() called on click")
    else:
        print("  ✗ FAIL: Missing showLogoutModal() call")
        all_passed = False
    
    # Test 4: Check for closeLogoutModal function definition
    print("\nTest 4: closeLogoutModal() function exists")
    if re.search(r'function\s+closeLogoutModal\s*\(\)', content):
        print("  ✓ PASS: closeLogoutModal() function defined")
        # Check it sets display to none
        if "modal.style.display = 'none'" in content:
            print("  ✓ PASS: Function hides modal by setting display to 'none'")
        else:
            print("  ✗ FAIL: Function doesn't hide modal properly")
            all_passed = False
    else:
        print("  ✗ FAIL: closeLogoutModal() function not found")
        all_passed = False
    
    # Test 5: Check for confirmLogout function definition
    print("\nTest 5: confirmLogout() function exists")
    if re.search(r'function\s+confirmLogout\s*\(\)', content):
        print("  ✓ PASS: confirmLogout() function defined")
        # Check it navigates to /logout
        if "window.location.href = '/logout'" in content:
            print("  ✓ PASS: Function navigates to /logout")
        else:
            print("  ✗ FAIL: Function doesn't navigate to /logout")
            all_passed = False
    else:
        print("  ✗ FAIL: confirmLogout() function not found")
        all_passed = False
    
    # Test 6: Check for Escape key handler
    print("\nTest 6: Escape key handler closes modal")
    if re.search(r"e\.key\s*===?\s*['\"]Escape['\"]", content):
        print("  ✓ PASS: Escape key event listener found")
        # Check it calls closeLogoutModal
        escape_section = re.search(r"e\.key\s*===?\s*['\"]Escape['\"].*?closeLogoutModal", content, re.DOTALL)
        if escape_section:
            print("  ✓ PASS: Escape key calls closeLogoutModal()")
        else:
            print("  ✗ FAIL: Escape key doesn't call closeLogoutModal()")
            all_passed = False
    else:
        print("  ✗ FAIL: Escape key handler not found")
        all_passed = False
    
    # Test 7: Check for overlay click handler
    print("\nTest 7: Overlay click handler closes modal")
    if 'onclick="closeLogoutModal()"' in content:
        # Check it's on the overlay element
        if re.search(r'class=["\']modal-overlay["\'].*?onclick=["\']closeLogoutModal\(\)["\']', content, re.DOTALL) or \
           re.search(r'onclick=["\']closeLogoutModal\(\)["\'].*?class=["\']modal-overlay["\']', content, re.DOTALL):
            print("  ✓ PASS: Overlay has onclick handler to close modal")
        else:
            print("  ⚠ WARNING: onclick handler found but may not be on overlay")
    else:
        print("  ✗ FAIL: Overlay click handler not found")
        all_passed = False
    
    # Test 8: Check for DOMContentLoaded event
    print("\nTest 8: DOMContentLoaded event listener")
    if "document.addEventListener('DOMContentLoaded'" in content or \
       'document.addEventListener("DOMContentLoaded"' in content:
        print("  ✓ PASS: DOMContentLoaded event listener found")
    else:
        print("  ✗ FAIL: DOMContentLoaded event listener not found")
        all_passed = False
    
    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED - Task 6.2 implementation is complete!")
        print("=" * 70)
        return True
    else:
        print("✗ SOME TESTS FAILED - Please review the implementation")
        print("=" * 70)
        return False

if __name__ == '__main__':
    success = verify_logout_modal_javascript()
    sys.exit(0 if success else 1)
