"""
Test suite for Task 8.2: Add audit log to analytics page

This test verifies that the audit log HTML section has been correctly added
to the analytics page with all required components.

Requirements tested:
- 4.2: THE System SHALL add an audit log section to the analytics page
- 4.3: THE Audit_Log section SHALL maintain all existing functionality including filters, pagination, and export
"""

import re


def test_audit_log_section_exists():
    """Verify audit log section exists in analytics.html"""
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for System Activity Log section
    assert 'System Activity Log' in content, "System Activity Log title not found"
    assert 'Chronological record of significant actions' in content, "Audit log description not found"
    
    print("✓ Audit log section exists in analytics.html")


def test_audit_log_filters_present():
    """Verify all audit log filters are present"""
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for filter elements
    assert 'id="auditActionFilter"' in content, "Action Type filter not found"
    assert 'id="auditActorFilter"' in content, "Actor filter not found"
    assert 'id="auditStartDate"' in content, "Start Date filter not found"
    assert 'id="auditEndDate"' in content, "End Date filter not found"
    
    # Check for filter labels
    assert 'Action Type' in content, "Action Type label not found"
    assert 'Actor' in content, "Actor label not found"
    assert 'Start Date' in content, "Start Date label not found"
    assert 'End Date' in content, "End Date label not found"
    
    print("✓ All audit log filters are present")


def test_audit_log_buttons_present():
    """Verify Apply and Export buttons are present"""
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for buttons
    assert 'onclick="loadAuditLog(1)"' in content, "Apply button (loadAuditLog) not found"
    assert 'onclick="exportAuditLog()"' in content, "Export button not found"
    
    # Check button text
    assert '>Apply</button>' in content, "Apply button text not found"
    assert '>Export</button>' in content, "Export button text not found"
    
    print("✓ Apply and Export buttons are present")


def test_audit_log_table_structure():
    """Verify audit log table has correct structure"""
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for table element
    assert 'id="auditTable"' in content, "Audit table not found"
    assert 'id="auditTableBody"' in content, "Audit table body not found"
    
    # Check for table headers
    required_headers = ['Timestamp', 'Actor', 'Action', 'Resource', 'Detail', 'IP Address']
    for header in required_headers:
        assert f'<th>{header}</th>' in content, f"Table header '{header}' not found"
    
    print("✓ Audit log table structure is correct")


def test_audit_log_pagination_present():
    """Verify pagination controls are present"""
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for pagination element
    assert 'id="auditPagination"' in content, "Audit pagination element not found"
    assert 'class="audit-pagination"' in content, "Audit pagination class not found"
    
    print("✓ Audit log pagination controls are present")


def test_audit_log_positioned_after_charts():
    """Verify audit log section is positioned after existing charts"""
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find positions of key elements
    repair_chart_pos = content.find('id="repairChart"')
    audit_log_pos = content.find('System Activity Log')
    
    assert repair_chart_pos > 0, "Repair chart not found"
    assert audit_log_pos > 0, "Audit log not found"
    assert audit_log_pos > repair_chart_pos, "Audit log should be positioned after repair chart"
    
    print("✓ Audit log is positioned after existing charts")


def test_audit_log_uses_chart_card_styling():
    """Verify audit log uses consistent chart-card styling"""
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract the audit log section
    audit_section_start = content.find('<!-- System Activity Log -->')
    audit_section_end = content.find('</div>\n\n          </div>', audit_section_start)
    audit_section = content[audit_section_start:audit_section_end]
    
    # Check for consistent styling classes
    assert 'class="chart-card span-12"' in audit_section, "chart-card class not found"
    assert 'class="chart-header"' in audit_section, "chart-header class not found"
    assert 'class="chart-title"' in audit_section, "chart-title class not found"
    assert 'class="chart-desc"' in audit_section, "chart-desc class not found"
    assert 'class="chart-filters' in audit_section, "chart-filters class not found"
    assert 'class="chart-body"' in audit_section, "chart-body class not found"
    
    print("✓ Audit log uses consistent chart-card styling")


def test_audit_log_filter_layout():
    """Verify audit log filters use proper layout classes"""
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for audit-filters class
    assert 'class="chart-filters audit-filters"' in content, "audit-filters class not found"
    
    # Check for control elements
    audit_section_start = content.find('<!-- Audit Log Filters -->')
    audit_section_end = content.find('<!-- Audit Log Table -->')
    audit_filters = content[audit_section_start:audit_section_end]
    
    # Count control divs (should have 5: action type, actor, start date, end date, actions)
    control_count = audit_filters.count('class="control')
    assert control_count >= 5, f"Expected at least 5 control elements, found {control_count}"
    
    print("✓ Audit log filters use proper layout classes")


def test_existing_analytics_preserved():
    """Verify existing analytics functionality is preserved"""
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for existing KPI cards
    assert 'Total Potholes' in content, "Total Potholes KPI not found"
    assert 'Active Defects' in content, "Active Defects KPI not found"
    assert 'Resolved' in content, "Resolved KPI not found"
    
    # Check for existing charts
    assert 'Detection Trends' in content, "Detection Trends chart not found"
    assert 'Geographic Heatmap' in content, "Geographic Heatmap not found"
    assert 'Defect Status Distribution' in content, "Defect Status Distribution not found"
    assert 'AI Confidence Distribution' in content, "AI Confidence Distribution not found"
    assert 'Weekly Repair Performance' in content, "Weekly Repair Performance not found"
    
    print("✓ Existing analytics functionality is preserved")


def test_audit_log_table_wrapper():
    """Verify audit log table has proper wrapper for styling"""
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for table-wrap class
    audit_section_start = content.find('<!-- Audit Log Table -->')
    audit_section_end = content.find('</div>\n            </div>\n\n          </div>')
    audit_table_section = content[audit_section_start:audit_section_end]
    
    assert 'class="table-wrap"' in audit_table_section, "table-wrap class not found"
    assert 'class="table"' in audit_table_section, "table class not found"
    
    print("✓ Audit log table has proper wrapper for styling")


def run_all_tests():
    """Run all test functions"""
    tests = [
        test_audit_log_section_exists,
        test_audit_log_filters_present,
        test_audit_log_buttons_present,
        test_audit_log_table_structure,
        test_audit_log_pagination_present,
        test_audit_log_positioned_after_charts,
        test_audit_log_uses_chart_card_styling,
        test_audit_log_filter_layout,
        test_existing_analytics_preserved,
        test_audit_log_table_wrapper,
    ]
    
    print("=" * 70)
    print("Task 8.2: Add Audit Log to Analytics Page - Test Suite")
    print("=" * 70)
    print()
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1
    
    print()
    print("=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("\n✅ All tests passed! Task 8.2 implementation is complete.")
        print("\nNext steps:")
        print("- Task 8.3: Migrate audit log JavaScript to analytics page")
        print("- Task 8.4: Add audit log CSS to analytics.css")
    else:
        print(f"\n❌ {failed} test(s) failed. Please review the implementation.")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
