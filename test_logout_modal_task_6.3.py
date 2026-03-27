"""
Test script to verify Task 6.3: Apply logout confirmation to all pages

This script verifies that:
1. The logout modal HTML is included in all required pages
2. Each page has logout links that will trigger the modal
3. The modal component exists and is properly structured
"""

import os
import re

def test_logout_modal_inclusion():
    """Test that all required pages include the logout modal"""
    
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
    
    print("=" * 70)
    print("TASK 6.3 VERIFICATION: Logout Modal Inclusion")
    print("=" * 70)
    print()
    
    all_passed = True
    
    for page_path in pages_to_check:
        if not os.path.exists(page_path):
            print(f"❌ FAIL: {page_path} - File not found")
            all_passed = False
            continue
        
        with open(page_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for logout modal include
        has_modal_include = "{% include 'logout_modal.html' %}" in content
        
        # Check for logout links
        has_logout_link = 'href="/logout"' in content
        
        # Check that modal include is before closing body tag
        modal_before_body = False
        if has_modal_include:
            modal_pos = content.find("{% include 'logout_modal.html' %}")
            body_close_pos = content.rfind('</body>')
            modal_before_body = modal_pos < body_close_pos if body_close_pos > 0 else False
        
        status = "✅ PASS" if (has_modal_include and has_logout_link and modal_before_body) else "❌ FAIL"
        
        print(f"{status}: {page_path}")
        print(f"  - Modal include: {'✓' if has_modal_include else '✗'}")
        print(f"  - Logout link: {'✓' if has_logout_link else '✗'}")
        print(f"  - Correct position: {'✓' if modal_before_body else '✗'}")
        print()
        
        if not (has_modal_include and has_logout_link and modal_before_body):
            all_passed = False
    
    return all_passed


def test_logout_modal_component():
    """Test that the logout modal component is properly structured"""
    
    print("=" * 70)
    print("LOGOUT MODAL COMPONENT VERIFICATION")
    print("=" * 70)
    print()
    
    modal_path = 'templates/logout_modal.html'
    
    if not os.path.exists(modal_path):
        print(f"❌ FAIL: {modal_path} not found")
        return False
    
    with open(modal_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'Modal container': 'id="logoutModal"' in content,
        'Modal overlay': 'class="modal-overlay"' in content,
        'Modal content': 'class="modal-content"' in content,
        'Modal title': 'Confirm Logout' in content,
        'Modal message': 'Are you sure you want to log out?' in content,
        'Cancel button': 'onclick="closeLogoutModal()"' in content,
        'Confirm button': 'onclick="confirmLogout()"' in content,
        'JavaScript handler': 'function showLogoutModal()' in content,
        'Event listener': "querySelectorAll('a[href=\"/logout\"]')" in content,
        'Escape key handler': "e.key === 'Escape'" in content,
        'CSS styling': '.modal {' in content,
        'Animation': '@keyframes modalSlideIn' in content
    }
    
    all_passed = True
    
    for check_name, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False
    
    print()
    
    if all_passed:
        print("✅ All modal component checks passed")
    else:
        print("❌ Some modal component checks failed")
    
    return all_passed


def test_logout_links_count():
    """Count logout links across all pages"""
    
    print("=" * 70)
    print("LOGOUT LINKS SUMMARY")
    print("=" * 70)
    print()
    
    pages = [
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
    
    total_links = 0
    
    for page_path in pages:
        if os.path.exists(page_path):
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            count = content.count('href="/logout"')
            total_links += count
            
            if count > 0:
                print(f"  {page_path}: {count} logout link(s)")
    
    print()
    print(f"Total logout links across all pages: {total_links}")
    print()
    
    return total_links > 0


if __name__ == '__main__':
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "TASK 6.3 VERIFICATION REPORT" + " " * 25 + "║")
    print("║" + " " * 10 + "Apply logout confirmation to all pages" + " " * 20 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    test1 = test_logout_modal_inclusion()
    test2 = test_logout_modal_component()
    test3 = test_logout_links_count()
    
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)
    
    if test1 and test2 and test3:
        print()
        print("✅ ALL TESTS PASSED")
        print()
        print("Task 6.3 is complete:")
        print("  ✓ Logout modal included on all required pages")
        print("  ✓ Modal component is properly structured")
        print("  ✓ All pages have logout links that will trigger the modal")
        print("  ✓ Modal positioned correctly before closing body tag")
        print()
        print("The logout confirmation dialog will now appear on:")
        print("  - index.html (Survey page)")
        print("  - map.html (Map page)")
        print("  - users.html (User management)")
        print("  - settings.html (Settings)")
        print("  - analytics.html (Analytics)")
        print("  - reports.html (Submit report)")
        print("  - my_reports.html (My reports)")
        print("  - defects.html (Defects management)")
        print("  - backup_management.html (Backup management)")
        print()
    else:
        print()
        print("❌ SOME TESTS FAILED")
        print()
        print("Please review the failures above and fix any issues.")
        print()
    
    print("=" * 70)
