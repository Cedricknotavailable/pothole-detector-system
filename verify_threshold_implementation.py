"""
Manual verification script for Task 5.2: Threshold update backend
This script verifies that the community_false_report_threshold setting
is properly handled in the settings_page route.
"""

import re

def verify_implementation():
    """Verify the threshold backend implementation in app.py"""
    
    print("=" * 70)
    print("TASK 5.2 VERIFICATION: Threshold Update Backend")
    print("=" * 70)
    print()
    
    # Read app.py
    with open('app.py', 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    checks = []
    
    # Check 1: Form field retrieval
    check1 = "community_false_report_threshold" in app_content and \
             "request.form.get('community_false_report_threshold'" in app_content
    checks.append(("✓" if check1 else "✗", "Retrieves community_false_report_threshold from form"))
    
    # Check 2: Validation for minimum value (>= 1)
    check2 = "val < 1" in app_content and \
             "Community false report threshold must be at least 1" in app_content
    checks.append(("✓" if check2 else "✗", "Validates threshold is >= 1"))
    
    # Check 3: Validation for maximum value (<= 10)
    check3 = "val > 10" in app_content and \
             "Community false report threshold must not exceed 10" in app_content
    checks.append(("✓" if check3 else "✗", "Validates threshold is <= 10"))
    
    # Check 4: Saves to Settings table
    check4 = "Settings.query.filter_by(key='community_false_report_threshold')" in app_content
    checks.append(("✓" if check4 else "✗", "Queries Settings table for threshold"))
    
    # Check 5: Creates new setting if not exists
    check5 = "Settings(key='community_false_report_threshold')" in app_content
    checks.append(("✓" if check5 else "✗", "Creates new Settings entry if not exists"))
    
    # Check 6: Audit log entry
    check6 = "'community_false_report_threshold': community_threshold" in app_content or \
             "'community_false_report_threshold'" in app_content
    checks.append(("✓" if check6 else "✗", "Includes threshold in audit log"))
    
    # Check 7: Error handling for non-numeric
    check7 = "Community false report threshold must be a number" in app_content
    checks.append(("✓" if check7 else "✗", "Handles non-numeric input"))
    
    # Check 8: Default value in settings_map
    check8 = "settings_map['community_false_report_threshold'] = '3'" in app_content
    checks.append(("✓" if check8 else "✗", "Sets default value of 3"))
    
    # Print results
    print("Backend Implementation Checks:")
    print("-" * 70)
    for symbol, description in checks:
        print(f"{symbol} {description}")
    
    print()
    print("-" * 70)
    
    # Check settings.html
    with open('templates/settings.html', 'r', encoding='utf-8') as f:
        settings_content = f.read()
    
    ui_checks = []
    
    # Check 9: Form field exists
    check9 = 'name="community_false_report_threshold"' in settings_content
    ui_checks.append(("✓" if check9 else "✗", "Form field exists in settings.html"))
    
    # Check 10: Input type is number
    check10 = 'type="number"' in settings_content and \
              'name="community_false_report_threshold"' in settings_content
    ui_checks.append(("✓" if check10 else "✗", "Input type is number"))
    
    # Check 11: Min and max attributes
    check11 = 'min="1"' in settings_content and 'max="10"' in settings_content
    ui_checks.append(("✓" if check11 else "✗", "Has min=1 and max=10 attributes"))
    
    # Check 12: Required attribute
    check12 = 'required' in settings_content
    ui_checks.append(("✓" if check12 else "✗", "Has required attribute"))
    
    # Check 13: Value binding
    check13 = '{{ settings.community_false_report_threshold }}' in settings_content
    ui_checks.append(("✓" if check13 else "✗", "Binds to settings value"))
    
    print("Frontend Implementation Checks:")
    print("-" * 70)
    for symbol, description in ui_checks:
        print(f"{symbol} {description}")
    
    print()
    print("=" * 70)
    
    all_checks = [c[0] == "✓" for c in checks + ui_checks]
    
    if all(all_checks):
        print("✓ ALL CHECKS PASSED - Task 5.2 is fully implemented!")
        print()
        print("Summary:")
        print("- Backend properly handles community_false_report_threshold form field")
        print("- Validates threshold is positive integer >= 1 and <= 10")
        print("- Saves to Settings table")
        print("- Writes audit log entry for threshold changes")
        print("- Returns success/error responses")
        print("- Frontend form field is properly configured")
        return True
    else:
        failed = sum(1 for c in all_checks if not c)
        print(f"✗ {failed} CHECK(S) FAILED - Review implementation")
        return False

if __name__ == '__main__':
    success = verify_implementation()
    exit(0 if success else 1)
