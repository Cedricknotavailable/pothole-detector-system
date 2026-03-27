"""
Test Task 8.1: Verify audit log removal from settings page
"""
import os


def test_audit_log_removed_from_settings_html():
    """Verify that audit log HTML section has been removed from settings.html"""
    with open('templates/settings.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that audit log section is removed
    assert 'Activity &amp; Audit Log' not in content, "Audit log accordion header should be removed"
    assert 'auditLogAccordion' not in content, "Audit log accordion ID should be removed"
    assert 'auditActionFilter' not in content, "Audit action filter should be removed"
    assert 'auditActorFilter' not in content, "Audit actor filter should be removed"
    assert 'auditStartDate' not in content, "Audit start date filter should be removed"
    assert 'auditEndDate' not in content, "Audit end date filter should be removed"
    assert 'auditTable' not in content, "Audit table should be removed"
    assert 'auditTableBody' not in content, "Audit table body should be removed"
    assert 'auditPagination' not in content, "Audit pagination should be removed"
    
    # Check that other sections remain
    assert 'General Configuration' in content, "General Configuration section should remain"
    assert 'Backup and Recovery' in content, "Backup and Recovery section should remain"
    
    print("✓ Audit log HTML section successfully removed from settings.html")


def test_audit_log_javascript_removed_from_settings_html():
    """Verify that audit log JavaScript functions have been removed from settings.html"""
    with open('templates/settings.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that JavaScript functions are removed
    assert 'function loadAuditLog' not in content, "loadAuditLog function should be removed"
    assert 'function renderAuditPagination' not in content, "renderAuditPagination function should be removed"
    assert 'function exportAuditLog' not in content, "exportAuditLog function should be removed"
    assert 'ACTION_CATEGORIES' not in content, "ACTION_CATEGORIES constant should be removed"
    assert 'CATEGORY_BADGE' not in content, "CATEGORY_BADGE constant should be removed"
    
    # Check that toggleAccordion function still exists but without audit log logic
    assert 'function toggleAccordion' in content, "toggleAccordion function should remain"
    assert 'auditLogAccordion' not in content, "Audit log accordion reference should be removed from toggleAccordion"
    
    print("✓ Audit log JavaScript functions successfully removed from settings.html")


def test_audit_log_css_removed_from_settings_css():
    """Verify that audit log specific CSS has been removed from settings.css"""
    with open('static/css/settings.css', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that audit log CSS is removed
    assert '.audit-filters-bar' not in content, "Audit filters bar CSS should be removed"
    assert '.audit-control-row' not in content, "Audit control row CSS should be removed"
    assert '.audit-pagination' not in content, "Audit pagination CSS should be removed"
    assert '#auditTable' not in content, "Audit table CSS should be removed"
    assert '.audit-detail-cell' not in content, "Audit detail cell CSS should be removed"
    assert '.audit-detail-kv' not in content, "Audit detail kv CSS should be removed"
    assert '.audit-badge' not in content, "Audit badge CSS should be removed"
    assert '.audit-badge--auth' not in content, "Audit badge auth CSS should be removed"
    
    # Check that other CSS remains
    assert '.settings-form' in content, "Settings form CSS should remain"
    assert '.accordion-item' in content, "Accordion item CSS should remain"
    assert '.modal' in content, "Modal CSS should remain"
    
    print("✓ Audit log CSS successfully removed from settings.css")


def test_settings_page_structure_intact():
    """Verify that settings page structure remains intact after removal"""
    with open('templates/settings.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check essential page structure
    assert '<title>Settings - Surveyor.AI</title>' in content, "Page title should be present"
    assert 'System Settings' in content, "Page header should be present"
    assert 'logout_modal.html' in content, "Logout modal include should be present"
    assert 'toggleAccordion' in content, "Accordion functionality should be present"
    
    # Check that there are still accordion items
    assert content.count('accordion-item') >= 2, "At least 2 accordion items should remain"
    
    print("✓ Settings page structure remains intact")


if __name__ == '__main__':
    print("Testing Task 8.1: Audit Log Removal from Settings Page\n")
    
    test_audit_log_removed_from_settings_html()
    test_audit_log_javascript_removed_from_settings_html()
    test_audit_log_css_removed_from_settings_css()
    test_settings_page_structure_intact()
    
    print("\n✅ All Task 8.1 tests passed!")
    print("\nSummary:")
    print("- Removed 'Activity & Audit Log' accordion section from settings.html")
    print("- Removed loadAuditLog(), renderAuditPagination(), and exportAuditLog() functions")
    print("- Removed audit log specific CSS from settings.css")
    print("- Preserved all other settings page functionality")
