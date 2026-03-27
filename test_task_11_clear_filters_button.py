"""
Test Task 11: Rename Reset to Clear Filters
Validates that all filter reset buttons have been renamed to "Clear Filters"
"""

import re
from pathlib import Path


def test_users_page_clear_filters_button():
    """Test that users.html has Clear Filters button"""
    content = Path('templates/users.html').read_text(encoding='utf-8')
    
    # Should have "Clear Filters" button
    assert 'Clear Filters</a>' in content, "users.html should have 'Clear Filters' button"
    
    # Should NOT have old "Reset" button in filter context
    # Check that Reset doesn't appear near url_for('users_page')
    pattern = r'url_for\([\'"]users_page[\'"]\)[^>]*>Reset</a>'
    assert not re.search(pattern, content), "users.html should not have 'Reset' button for filters"
    
    print("✓ users.html: Clear Filters button verified")


def test_defects_page_clear_filters_button():
    """Test that defects.html has Clear Filters button"""
    content = Path('templates/defects.html').read_text(encoding='utf-8')
    
    # Should have "Clear Filters" button
    assert 'Clear Filters</a>' in content, "defects.html should have 'Clear Filters' button"
    
    # Should NOT have old "Reset" button in filter context
    pattern = r'url_for\([\'"]defects_page[\'"]\)[^>]*>Reset</a>'
    assert not re.search(pattern, content), "defects.html should not have 'Reset' button for filters"
    
    print("✓ defects.html: Clear Filters button verified")


def test_my_reports_page_clear_filters_button():
    """Test that my_reports.html has Clear Filters button"""
    content = Path('templates/my_reports.html').read_text(encoding='utf-8')
    
    # Should have "Clear Filters" button
    assert 'Clear Filters</a>' in content, "my_reports.html should have 'Clear Filters' button"
    
    # Should NOT have old "Reset" button in filter context
    pattern = r'url_for\([\'"]my_reports_page[\'"]\)[^>]*>Reset</a>'
    assert not re.search(pattern, content), "my_reports.html should not have 'Reset' button for filters"
    
    print("✓ my_reports.html: Clear Filters button verified")


def test_map_page_clear_filters_button():
    """Test that map.html has Clear Filters button"""
    content = Path('templates/map.html').read_text(encoding='utf-8')
    
    # Should have "Clear Filters" button
    assert 'Clear Filters</button>' in content, "map.html should have 'Clear Filters' button"
    
    # Should NOT have old "Reset" button for filters
    # The resetFilters ID should still exist (JavaScript function name unchanged)
    assert 'id="resetFilters"' in content, "map.html should still have resetFilters ID"
    
    # But the button text should be "Clear Filters"
    pattern = r'id="resetFilters"[^>]*>Reset</button>'
    assert not re.search(pattern, content), "map.html should not have 'Reset' text on filter button"
    
    print("✓ map.html: Clear Filters button verified")


def test_password_reset_unchanged():
    """Test that password reset buttons remain unchanged"""
    content = Path('templates/recover.html').read_text(encoding='utf-8')
    
    # Password reset buttons should still say "Reset Password"
    assert 'Reset Password</button>' in content, "recover.html should still have 'Reset Password' button"
    
    print("✓ recover.html: Password reset buttons unchanged (correct)")


def test_button_functionality_unchanged():
    """Test that button functionality remains the same"""
    
    # Check users.html - should link to users_page
    users_content = Path('templates/users.html').read_text(encoding='utf-8')
    assert "url_for('users_page')" in users_content, "users.html filter clear should link to users_page"
    
    # Check defects.html - should link to defects_page
    defects_content = Path('templates/defects.html').read_text(encoding='utf-8')
    assert "url_for('defects_page')" in defects_content, "defects.html filter clear should link to defects_page"
    
    # Check my_reports.html - should link to my_reports_page
    reports_content = Path('templates/my_reports.html').read_text(encoding='utf-8')
    assert "url_for('my_reports_page')" in reports_content, "my_reports.html filter clear should link to my_reports_page"
    
    # Check map.html - should have resetFilters ID
    map_content = Path('templates/map.html').read_text(encoding='utf-8')
    assert 'id="resetFilters"' in map_content, "map.html should have resetFilters ID"
    
    print("✓ All button functionality unchanged")


def test_responsive_layout():
    """Test that button text works in responsive layouts"""
    
    # Check that buttons are in control actions divs (existing responsive structure)
    for template in ['users.html', 'defects.html', 'my_reports.html']:
        content = Path(f'templates/{template}').read_text(encoding='utf-8')
        assert 'control actions' in content, f"{template} should have control actions div"
        assert 'Clear Filters' in content, f"{template} should have Clear Filters text"
    
    print("✓ Responsive layout structure maintained")


if __name__ == '__main__':
    print("Testing Task 11: Rename Reset to Clear Filters\n")
    
    test_users_page_clear_filters_button()
    test_defects_page_clear_filters_button()
    test_my_reports_page_clear_filters_button()
    test_map_page_clear_filters_button()
    test_password_reset_unchanged()
    test_button_functionality_unchanged()
    test_responsive_layout()
    
    print("\n✅ All Task 11 tests passed!")
    print("\nSummary:")
    print("- users.html: Reset → Clear Filters ✓")
    print("- defects.html: Reset → Clear Filters ✓")
    print("- my_reports.html: Reset → Clear Filters ✓")
    print("- map.html: Reset → Clear Filters ✓")
    print("- Button functionality unchanged ✓")
    print("- Responsive layout maintained ✓")
