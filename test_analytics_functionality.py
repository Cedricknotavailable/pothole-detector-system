#!/usr/bin/env python3
"""
Test script to verify analytics page functionality.
This script tests both frontend and backend components.
"""

import re
import os
import sys

def test_analytics_api_routes():
    """Test that all analytics API routes exist."""
    print("Testing analytics API routes...")
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_routes = [
        '/api/analytics/overview',
        '/api/analytics/trends',
        '/api/analytics/heatmap',
        '/api/analytics/status',
        '/api/analytics/confidence',
        '/api/analytics/repair',
        '/api/analytics/export-pdf'
    ]
    
    missing_routes = []
    for route in required_routes:
        if route not in content:
            missing_routes.append(route)
    
    if missing_routes:
        print(f"❌ Missing API routes: {missing_routes}")
        return False
    
    print("✓ All analytics API routes are present")
    return True

def test_frontend_structure():
    """Test that the frontend has all required elements."""
    print("Testing frontend structure...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for KPI elements
    kpi_elements = [
        'id="kpi-potholes"',
        'id="kpi-active"',
        'id="kpi-resolved"',
        'id="kpi-repair-time"',
        'id="kpi-reports"',
        'id="kpi-accuracy"'
    ]
    
    # Check for chart containers
    chart_elements = [
        'id="trendsChart"',
        'id="statusChart"',
        'id="confidenceChart"',
        'id="repairChart"',
        'id="heatmapMap"'
    ]
    
    # Check for filter controls
    filter_elements = [
        'id="timeRangePreset"',
        'id="customDateRange"',
        'id="startDate"',
        'id="endDate"',
        'id="globalAdminLevel"',
        'id="globalAdminArea"',
        'id="applyFiltersBtn"',
        'id="clearFiltersBtn"'
    ]
    
    all_elements = kpi_elements + chart_elements + filter_elements
    missing_elements = []
    
    for element in all_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print(f"❌ Missing frontend elements: {missing_elements}")
        return False
    
    print("✓ All frontend elements are present")
    return True

def test_javascript_functions():
    """Test that all JavaScript functions are properly defined."""
    print("Testing JavaScript functions...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract all function definitions
    function_pattern = r'(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s+)?function|\basync\s+function\s+(\w+))'
    matches = re.findall(function_pattern, content)
    
    # Flatten the matches (regex groups)
    defined_functions = []
    for match in matches:
        for group in match:
            if group:
                defined_functions.append(group)
    
    required_functions = [
        'fetchOverview',
        'fetchTrends',
        'fetchHeatmap',
        'fetchStatus',
        'fetchConfidence',
        'fetchRepair',
        'onTimeRangePresetChange',
        'onGlobalLevelChange',
        'loadAreas',
        'refreshAll',
        'exportAnalyticsPDF',
        'captureChartsForPDF',
        'captureMapAsImage'
    ]
    
    missing_functions = []
    for func in required_functions:
        if func not in defined_functions:
            missing_functions.append(func)
    
    if missing_functions:
        print(f"❌ Missing JavaScript functions: {missing_functions}")
        return False
    
    print("✓ All JavaScript functions are defined")
    return True

def test_pdf_export_functionality():
    """Test that PDF export functionality is complete."""
    print("Testing PDF export functionality...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for PDF export button
    if 'id="exportPdfBtn"' not in content:
        print("❌ PDF export button not found")
        return False
    
    # Check for PDF export function
    if 'function exportAnalyticsPDF' not in content:
        print("❌ PDF export function not found")
        return False
    
    # Check for chart capture functions
    if 'function captureChartsForPDF' not in content:
        print("❌ Chart capture function not found")
        return False
    
    # Check for map capture function
    if 'function captureMapAsImage' not in content:
        print("❌ Map capture function not found")
        return False
    
    # Check for html2canvas library
    if 'html2canvas' not in content:
        print("❌ html2canvas library not loaded")
        return False
    
    print("✓ PDF export functionality is complete")
    return True

def test_custom_date_range():
    """Test that custom date range functionality is working."""
    print("Testing custom date range functionality...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for custom date range option
    if 'value="custom"' not in content:
        print("❌ Custom date range option not found")
        return False
    
    # Check for custom date inputs
    if 'id="startDate"' not in content or 'id="endDate"' not in content:
        print("❌ Custom date inputs not found")
        return False
    
    # Check for show/hide logic
    if 'customDateRange.style.display' not in content:
        print("❌ Custom date range show/hide logic not found")
        return False
    
    # Check for custom date handling in getGlobalFilters
    if 'preset === \'custom\'' not in content:
        print("❌ Custom date handling not found")
        return False
    
    print("✓ Custom date range functionality is complete")
    return True

def test_chart_libraries():
    """Test that all required chart libraries are loaded."""
    print("Testing chart libraries...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_libraries = [
        'chart.js',
        'leaflet.js',
        'leaflet-heat.js',
        'html2canvas'
    ]
    
    missing_libraries = []
    for lib in required_libraries:
        if lib not in content:
            missing_libraries.append(lib)
    
    if missing_libraries:
        print(f"❌ Missing chart libraries: {missing_libraries}")
        return False
    
    print("✓ All chart libraries are loaded")
    return True

def main():
    """Run all tests."""
    print("Testing Analytics Page Functionality")
    print("=" * 45)
    
    try:
        api_ok = test_analytics_api_routes()
        frontend_ok = test_frontend_structure()
        js_ok = test_javascript_functions()
        pdf_ok = test_pdf_export_functionality()
        date_ok = test_custom_date_range()
        libs_ok = test_chart_libraries()
        
        print("\n" + "=" * 45)
        
        if all([api_ok, frontend_ok, js_ok, pdf_ok, date_ok, libs_ok]):
            print("✅ All tests passed! Analytics page should be fully functional.")
            print("\nIf you're still experiencing issues:")
            print("1. Check browser console (F12) for JavaScript errors")
            print("2. Check Network tab for failed API requests")
            print("3. Verify you're logged in as an admin user")
            print("4. Check server logs for backend errors")
            print("5. Try hard refresh (Ctrl+F5) to clear cache")
            print("6. Test with different browsers")
            
            print("\nExpected functionality:")
            print("• KPI cards should display current statistics")
            print("• Charts should load and display data")
            print("• Time range filters should work (including custom dates)")
            print("• Area filters should populate and filter data")
            print("• PDF export should generate and download reports")
            print("• Geographic heatmap should show defect locations")
            
        else:
            print("❌ Some tests failed. Please fix the issues above.")
            print("\nCommon fixes:")
            print("• Ensure all required API routes are implemented")
            print("• Check for JavaScript syntax errors")
            print("• Verify all HTML elements have correct IDs")
            print("• Make sure all libraries are properly loaded")
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()