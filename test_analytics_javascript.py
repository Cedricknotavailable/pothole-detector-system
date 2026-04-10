#!/usr/bin/env python3
"""
Test script to verify analytics JavaScript functionality.
This script checks for common JavaScript syntax errors and missing functions.
"""

import re
import os
import sys

def test_javascript_syntax():
    """Test for JavaScript syntax errors in analytics template."""
    print("Testing JavaScript syntax...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for common syntax errors
    
    # Check for unmatched braces
    open_braces = content.count('{')
    close_braces = content.count('}')
    print(f"Open braces: {open_braces}, Close braces: {close_braces}")
    
    # Check for unmatched parentheses in script sections
    script_sections = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
    for i, script in enumerate(script_sections):
        open_parens = script.count('(')
        close_parens = script.count(')')
        if open_parens != close_parens:
            print(f"WARNING: Unmatched parentheses in script section {i+1}")
    
    # Check for duplicate function definitions
    function_names = re.findall(r'function\s+(\w+)\s*\(', content)
    duplicates = [name for name in set(function_names) if function_names.count(name) > 1]
    if duplicates:
        print(f"WARNING: Duplicate functions found: {duplicates}")
    
    # Check for orphaned code (code outside functions)
    orphaned_patterns = [
        r'document\.body\.removeChild\(a\);',
        r'window\.URL\.revokeObjectURL\(url\);',
        r'console\.log\(\'PDF export completed successfully\'\);'
    ]
    
    for pattern in orphaned_patterns:
        matches = re.findall(pattern, content)
        if matches:
            print(f"WARNING: Found orphaned code: {pattern}")
    
    print("✓ JavaScript syntax check completed")

def test_required_functions():
    """Test that all required functions are present."""
    print("Testing required functions...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_functions = [
        'fetchOverview',
        'fetchTrends', 
        'fetchHeatmap',
        'fetchStatus',
        'fetchConfidence',
        'fetchRepair',
        'onTimeRangePresetChange',
        'loadAreas',
        'refreshAll',
        'exportAnalyticsPDF',
        'captureChartsForPDF',
        'captureMapAsImage'
    ]
    
    missing_functions = []
    for func in required_functions:
        if f'function {func}' not in content and f'{func} = ' not in content:
            missing_functions.append(func)
    
    if missing_functions:
        print(f"❌ Missing functions: {missing_functions}")
        return False
    
    print("✓ All required functions are present")
    return True

def test_event_handlers():
    """Test that event handlers are properly set up."""
    print("Testing event handlers...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for required event handlers
    required_handlers = [
        'onchange="onTimeRangePresetChange()"',
        'onclick="exportAnalyticsPDF()"',
        'onclick="refreshAll()"'
    ]
    
    missing_handlers = []
    for handler in required_handlers:
        if handler not in content:
            missing_handlers.append(handler)
    
    if missing_handlers:
        print(f"❌ Missing event handlers: {missing_handlers}")
        return False
    
    print("✓ All event handlers are present")
    return True

def test_html_structure():
    """Test that required HTML elements are present."""
    print("Testing HTML structure...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_elements = [
        'id="timeRangePreset"',
        'id="customDateRange"',
        'id="customDateRangeEnd"',
        'id="startDate"',
        'id="endDate"',
        'id="exportPdfBtn"',
        'id="heatmapMap"',
        'id="globalAdminArea"',
        'id="globalAdminLevel"'
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print(f"❌ Missing HTML elements: {missing_elements}")
        return False
    
    print("✓ All required HTML elements are present")
    return True

def test_script_loading():
    """Test that required scripts are loaded."""
    print("Testing script loading...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_scripts = [
        'chart.js',
        'leaflet.js',
        'leaflet-heat.js',
        'html2canvas'
    ]
    
    missing_scripts = []
    for script in required_scripts:
        if script not in content:
            missing_scripts.append(script)
    
    if missing_scripts:
        print(f"❌ Missing scripts: {missing_scripts}")
        return False
    
    print("✓ All required scripts are loaded")
    return True

def main():
    """Run all tests."""
    print("Testing Analytics Page JavaScript")
    print("=" * 40)
    
    try:
        test_javascript_syntax()
        functions_ok = test_required_functions()
        handlers_ok = test_event_handlers()
        html_ok = test_html_structure()
        scripts_ok = test_script_loading()
        
        if all([functions_ok, handlers_ok, html_ok, scripts_ok]):
            print("\n" + "=" * 40)
            print("✅ All tests passed! Analytics page should be working.")
            print("\nIf the page is still not working, check:")
            print("1. Browser console for JavaScript errors")
            print("2. Network tab for failed API requests")
            print("3. Server logs for backend errors")
            print("4. Database connectivity")
        else:
            print("\n" + "=" * 40)
            print("❌ Some tests failed. Fix the issues above.")
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()