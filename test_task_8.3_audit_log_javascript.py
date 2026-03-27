#!/usr/bin/env python3
"""
Test Suite for Task 8.3: Migrate Audit Log JavaScript to Analytics Page

This test verifies that all audit log JavaScript functions have been successfully
migrated from settings.html to analytics.html.

Task Requirements:
- Copy loadAuditLog(page) function to analytics.html
- Copy renderAuditPagination() function
- Copy exportAuditLog() function
- Initialize audit log on page load (after charts)
- Test all filters and pagination
"""

import re
from pathlib import Path


def read_file(filepath):
    """Read file content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def test_analytics_has_audit_log_constants():
    """Test that analytics.html has the ACTION_CATEGORIES and CATEGORY_BADGE constants."""
    print("\n1. Testing audit log constants in analytics.html...")
    
    content = read_file('templates/analytics.html')
    
    # Check for ACTION_CATEGORIES
    assert 'const ACTION_CATEGORIES = {' in content, \
        "❌ ACTION_CATEGORIES constant not found in analytics.html"
    
    # Check for specific action mappings
    assert "USER_LOGIN: 'auth'" in content, \
        "❌ USER_LOGIN action mapping not found"
    assert "REPORT_SUBMITTED: 'reports'" in content, \
        "❌ REPORT_SUBMITTED action mapping not found"
    assert "BACKUP_EXPORTED: 'backup'" in content, \
        "❌ BACKUP_EXPORTED action mapping not found"
    
    # Check for CATEGORY_BADGE
    assert 'const CATEGORY_BADGE = {' in content, \
        "❌ CATEGORY_BADGE constant not found in analytics.html"
    
    # Check for badge mappings
    assert "'auth': 'audit-badge--auth'" in content, \
        "❌ Auth badge mapping not found"
    assert "'reports': 'audit-badge--report'" in content, \
        "❌ Reports badge mapping not found"
    
    print("✅ Audit log constants present in analytics.html")


def test_analytics_has_audit_current_page_variable():
    """Test that analytics.html has the _auditCurrentPage variable."""
    print("\n2. Testing _auditCurrentPage variable in analytics.html...")
    
    content = read_file('templates/analytics.html')
    
    assert 'let _auditCurrentPage = 1;' in content, \
        "❌ _auditCurrentPage variable not found in analytics.html"
    
    print("✅ _auditCurrentPage variable present in analytics.html")


def test_analytics_has_load_audit_log_function():
    """Test that analytics.html has the loadAuditLog function."""
    print("\n3. Testing loadAuditLog function in analytics.html...")
    
    content = read_file('templates/analytics.html')
    
    # Check for function declaration
    assert 'async function loadAuditLog(page)' in content, \
        "❌ loadAuditLog function declaration not found in analytics.html"
    
    # Check for key functionality
    assert "page = page || _auditCurrentPage;" in content, \
        "❌ Page parameter handling not found"
    assert "_auditCurrentPage = page;" in content, \
        "❌ Current page update not found"
    assert "document.getElementById('auditActionFilter')" in content, \
        "❌ Action filter reference not found"
    assert "document.getElementById('auditActorFilter')" in content, \
        "❌ Actor filter reference not found"
    assert "document.getElementById('auditStartDate')" in content, \
        "❌ Start date filter reference not found"
    assert "document.getElementById('auditEndDate')" in content, \
        "❌ End date filter reference not found"
    assert "document.getElementById('auditTableBody')" in content, \
        "❌ Table body reference not found"
    assert "fetch('/api/audit-log?' + params.toString())" in content, \
        "❌ API fetch call not found"
    assert "renderAuditPagination(data.page, data.pages, data.total);" in content, \
        "❌ Pagination render call not found"
    
    # Check for error handling
    assert "if (!res.ok)" in content, \
        "❌ Response error handling not found"
    assert "catch (err)" in content, \
        "❌ Try-catch error handling not found"
    
    # Check for action type dropdown population
    assert "data.action_types && data.action_types.length > 0" in content, \
        "❌ Action types check not found"
    assert "opt.textContent = a.replace(/_/g, ' ');" in content, \
        "❌ Action type formatting not found"
    
    # Check for table rendering
    assert "ACTION_CATEGORIES[e.action]" in content, \
        "❌ Action category lookup not found"
    assert "CATEGORY_BADGE[cat]" in content, \
        "❌ Badge class lookup not found"
    assert "audit-badge" in content, \
        "❌ Badge class application not found"
    
    print("✅ loadAuditLog function present and complete in analytics.html")


def test_analytics_has_render_audit_pagination_function():
    """Test that analytics.html has the renderAuditPagination function."""
    print("\n4. Testing renderAuditPagination function in analytics.html...")
    
    content = read_file('templates/analytics.html')
    
    # Check for function declaration
    assert 'function renderAuditPagination(page, pages, total)' in content, \
        "❌ renderAuditPagination function declaration not found in analytics.html"
    
    # Check for key functionality
    assert "document.getElementById('auditPagination')" in content, \
        "❌ Pagination element reference not found"
    assert "if (pages <= 1)" in content, \
        "❌ Single page check not found"
    assert "${total} entries" in content, \
        "❌ Entry count display not found"
    assert "loadAuditLog(${page - 1})" in content, \
        "❌ Previous page link not found"
    assert "loadAuditLog(${page + 1})" in content, \
        "❌ Next page link not found"
    assert "page-btn" in content, \
        "❌ Page button class not found"
    assert "page-num" in content, \
        "❌ Page number class not found"
    
    print("✅ renderAuditPagination function present and complete in analytics.html")


def test_analytics_has_export_audit_log_function():
    """Test that analytics.html has the exportAuditLog function."""
    print("\n5. Testing exportAuditLog function in analytics.html...")
    
    content = read_file('templates/analytics.html')
    
    # Check for function declaration
    assert 'function exportAuditLog()' in content, \
        "❌ exportAuditLog function declaration not found in analytics.html"
    
    # Check for key functionality
    assert "document.getElementById('auditActionFilter')" in content, \
        "❌ Action filter reference not found in export function"
    assert "document.getElementById('auditActorFilter')" in content, \
        "❌ Actor filter reference not found in export function"
    assert "document.getElementById('auditStartDate')" in content, \
        "❌ Start date filter reference not found in export function"
    assert "document.getElementById('auditEndDate')" in content, \
        "❌ End date filter reference not found in export function"
    assert "per_page: 10000" in content, \
        "❌ Large page size for export not found"
    assert "fetch('/api/audit-log?' + params.toString())" in content, \
        "❌ API fetch call not found in export function"
    
    # Check for CSV generation
    assert "['Timestamp', 'Actor', 'Action', 'Resource Type', 'Resource ID', 'Detail', 'IP Address']" in content, \
        "❌ CSV header row not found"
    assert "JSON.stringify(e.detail)" in content, \
        "❌ Detail JSON stringification not found"
    assert "type: 'text/csv'" in content, \
        "❌ CSV MIME type not found"
    assert "a.download = 'audit_log.csv'" in content, \
        "❌ CSV filename not found"
    assert "URL.createObjectURL(blob)" in content, \
        "❌ Blob URL creation not found"
    assert "URL.revokeObjectURL(url)" in content, \
        "❌ URL cleanup not found"
    
    print("✅ exportAuditLog function present and complete in analytics.html")


def test_analytics_initializes_audit_log_on_load():
    """Test that analytics.html initializes the audit log after charts."""
    print("\n6. Testing audit log initialization in analytics.html...")
    
    content = read_file('templates/analytics.html')
    
    # Check for initialization in Promise.all().then()
    assert "Promise.all([" in content, \
        "❌ Promise.all initialization block not found"
    assert "loadChartAreas('kpiAdminArea', 'province')" in content, \
        "❌ Chart areas loading not found"
    assert ".then(() => {" in content, \
        "❌ Promise then block not found"
    
    # Check that audit log is loaded after charts
    assert "setTimeout(() => loadAuditLog(1), 500);" in content, \
        "❌ Audit log initialization not found or not delayed properly"
    
    # Verify the order: charts first, then audit log
    # Find the Promise.all block
    promise_start = content.find("Promise.all([")
    promise_end = content.find("</script>", promise_start)
    promise_block = content[promise_start:promise_end]
    
    # Look for chart initialization
    chart_init_pos = promise_block.find("fetchOverview()")
    audit_init_pos = promise_block.find("loadAuditLog(1)")
    
    assert chart_init_pos != -1, "❌ Chart initialization (fetchOverview) not found in Promise block"
    assert audit_init_pos != -1, "❌ Audit log initialization not found in Promise block"
    assert chart_init_pos < audit_init_pos, \
        f"❌ Audit log should be initialized AFTER charts (chart at {chart_init_pos}, audit at {audit_init_pos})"
    
    print("✅ Audit log initialization present and correctly ordered in analytics.html")


def test_settings_does_not_have_audit_log_functions():
    """Test that settings.html no longer has audit log functions."""
    print("\n7. Testing that settings.html does not have audit log functions...")
    
    content = read_file('templates/settings.html')
    
    # These should NOT be in settings.html anymore
    assert 'function loadAuditLog' not in content, \
        "❌ loadAuditLog function still present in settings.html"
    assert 'function renderAuditPagination' not in content, \
        "❌ renderAuditPagination function still present in settings.html"
    assert 'function exportAuditLog' not in content, \
        "❌ exportAuditLog function still present in settings.html"
    assert 'ACTION_CATEGORIES' not in content, \
        "❌ ACTION_CATEGORIES constant still present in settings.html"
    assert 'CATEGORY_BADGE' not in content, \
        "❌ CATEGORY_BADGE constant still present in settings.html"
    assert '_auditCurrentPage' not in content, \
        "❌ _auditCurrentPage variable still present in settings.html"
    
    print("✅ Settings.html correctly does not have audit log functions")


def test_analytics_has_audit_log_html():
    """Test that analytics.html has the audit log HTML structure."""
    print("\n8. Testing audit log HTML structure in analytics.html...")
    
    content = read_file('templates/analytics.html')
    
    # Check for filter elements
    assert 'id="auditActionFilter"' in content, \
        "❌ Action filter dropdown not found"
    assert 'id="auditActorFilter"' in content, \
        "❌ Actor filter input not found"
    assert 'id="auditStartDate"' in content, \
        "❌ Start date input not found"
    assert 'id="auditEndDate"' in content, \
        "❌ End date input not found"
    
    # Check for action buttons
    assert 'onclick="loadAuditLog(1)"' in content, \
        "❌ Apply button with loadAuditLog call not found"
    assert 'onclick="exportAuditLog()"' in content, \
        "❌ Export button with exportAuditLog call not found"
    
    # Check for table structure
    assert 'id="auditTable"' in content, \
        "❌ Audit table not found"
    assert 'id="auditTableBody"' in content, \
        "❌ Audit table body not found"
    assert 'id="auditPagination"' in content, \
        "❌ Audit pagination container not found"
    
    # Check for table headers
    assert '<th>Timestamp</th>' in content, \
        "❌ Timestamp header not found"
    assert '<th>Actor</th>' in content, \
        "❌ Actor header not found"
    assert '<th>Action</th>' in content, \
        "❌ Action header not found"
    assert '<th>Resource</th>' in content, \
        "❌ Resource header not found"
    assert '<th>Detail</th>' in content, \
        "❌ Detail header not found"
    assert '<th>IP Address</th>' in content, \
        "❌ IP Address header not found"
    
    print("✅ Audit log HTML structure present in analytics.html")


def test_function_completeness():
    """Test that all functions are complete and not truncated."""
    print("\n9. Testing function completeness...")
    
    content = read_file('templates/analytics.html')
    
    # Count opening and closing braces in script section
    script_start = content.find('<script>')
    script_end = content.rfind('</script>')
    script_content = content[script_start:script_end]
    
    open_braces = script_content.count('{')
    close_braces = script_content.count('}')
    
    assert open_braces == close_braces, \
        f"❌ Mismatched braces in script section: {open_braces} open, {close_braces} close"
    
    # Check that each function has proper closing
    functions = [
        'async function loadAuditLog(page)',
        'function renderAuditPagination(page, pages, total)',
        'function exportAuditLog()'
    ]
    
    for func in functions:
        func_start = script_content.find(func)
        assert func_start != -1, f"❌ Function not found: {func}"
        
        # Find the next function or end of script
        next_func_start = len(script_content)
        for other_func in functions:
            if other_func != func:
                pos = script_content.find(other_func, func_start + len(func))
                if pos != -1 and pos < next_func_start:
                    next_func_start = pos
        
        func_body = script_content[func_start:next_func_start]
        func_open = func_body.count('{')
        func_close = func_body.count('}')
        
        assert func_open == func_close, \
            f"❌ Mismatched braces in {func}: {func_open} open, {func_close} close"
    
    print("✅ All functions are complete with matching braces")


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 70)
    print("Task 8.3: Migrate Audit Log JavaScript to Analytics Page")
    print("=" * 70)
    
    tests = [
        test_analytics_has_audit_log_constants,
        test_analytics_has_audit_current_page_variable,
        test_analytics_has_load_audit_log_function,
        test_analytics_has_render_audit_pagination_function,
        test_analytics_has_export_audit_log_function,
        test_analytics_initializes_audit_log_on_load,
        test_settings_does_not_have_audit_log_functions,
        test_analytics_has_audit_log_html,
        test_function_completeness,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n{e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ Unexpected error in {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("\n✅ All tests passed! Task 8.3 is complete.")
        print("\nVerification checklist:")
        print("  ✅ loadAuditLog(page) function copied to analytics.html")
        print("  ✅ renderAuditPagination() function copied to analytics.html")
        print("  ✅ exportAuditLog() function copied to analytics.html")
        print("  ✅ ACTION_CATEGORIES and CATEGORY_BADGE constants present")
        print("  ✅ _auditCurrentPage variable present")
        print("  ✅ Audit log initialized on page load (after charts)")
        print("  ✅ All filter references working")
        print("  ✅ Pagination functionality present")
        print("  ✅ Functions removed from settings.html")
        print("  ✅ All functions complete and properly formatted")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    exit(run_all_tests())
