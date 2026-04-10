#!/usr/bin/env python3
"""
Test script to verify geographic filter functionality in analytics page.
This script tests both frontend and backend geographic filtering.
"""

import re
import os
import sys
import json

def test_data_files_structure():
    """Test that geographic data files have correct structure."""
    print("Testing geographic data files structure...")
    
    data_files = {
        'regions': 'static/data/regions.json',
        'provinces': 'static/data/provinces.json', 
        'municipalities': 'static/data/municipalities.json'
    }
    
    expected_properties = {
        'regions': ['name', 'REGION'],
        'provinces': ['NAME_1'],
        'municipalities': ['NAME_2']
    }
    
    for level, filepath in data_files.items():
        if not os.path.exists(filepath):
            print(f"❌ Missing data file: {filepath}")
            return False
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'features' not in data:
                print(f"❌ {level} file missing 'features' array")
                return False
                
            if not data['features']:
                print(f"❌ {level} file has empty 'features' array")
                return False
                
            # Check first feature for expected properties
            first_feature = data['features'][0]
            if 'properties' not in first_feature:
                print(f"❌ {level} feature missing 'properties'")
                return False
                
            props = first_feature['properties']
            expected_props = expected_properties[level]
            
            has_expected_prop = any(prop in props for prop in expected_props)
            if not has_expected_prop:
                print(f"❌ {level} missing expected properties {expected_props}")
                print(f"   Available properties: {list(props.keys())}")
                return False
                
            print(f"✓ {level} data file structure is correct")
            
        except Exception as e:
            print(f"❌ Error reading {level} file: {e}")
            return False
    
    return True

def test_loadareas_function():
    """Test that loadAreas function is correctly implemented."""
    print("Testing loadAreas function implementation...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for loadAreas function
    if 'function loadAreas' not in content:
        print("❌ loadAreas function not found")
        return False
    
    # Check for correct property handling
    required_patterns = [
        r"level === 'municipality'",
        r"f\.properties\.NAME_2",
        r"level === 'province'", 
        r"f\.properties\.NAME_1",
        r"level === 'region'",
        r"f\.properties\.REGION.*f\.properties\.name"
    ]
    
    missing_patterns = []
    for pattern in required_patterns:
        if not re.search(pattern, content):
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"❌ Missing patterns in loadAreas: {missing_patterns}")
        return False
    
    # Check for deduplication logic
    if 'nameSet' not in content or 'uniqueFeatures' not in content:
        print("❌ Deduplication logic not found in loadAreas")
        return False
    
    print("✓ loadAreas function is correctly implemented")
    return True

def test_backend_filtering():
    """Test that backend filtering functions are correctly implemented."""
    print("Testing backend filtering functions...")
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for filter_by_area function
    if 'def filter_by_area' not in content:
        print("❌ filter_by_area function not found")
        return False
    
    # Check for load_geojson_polygons function
    if 'def load_geojson_polygons' not in content:
        print("❌ load_geojson_polygons function not found")
        return False
    
    # Check for correct property handling in load_geojson_polygons
    required_patterns = [
        r"area_type == 'province'",
        r"props\.get\('NAME_1'\)",
        r"area_type == 'municipality'",
        r"props\.get\('NAME_2'\)",
        r"area_type == 'region'",
        r"props\.get\('name'\).*props\.get\('REGION'\)"
    ]
    
    missing_patterns = []
    for pattern in required_patterns:
        if not re.search(pattern, content):
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"❌ Missing patterns in backend filtering: {missing_patterns}")
        return False
    
    print("✓ Backend filtering functions are correctly implemented")
    return True

def test_frontend_event_handlers():
    """Test that frontend event handlers are properly set up."""
    print("Testing frontend event handlers...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for admin level change handler
    if 'onchange="onGlobalLevelChange()"' not in content:
        print("❌ Admin level change handler not found")
        return False
    
    # Check for onGlobalLevelChange function
    if 'function onGlobalLevelChange()' not in content:
        print("❌ onGlobalLevelChange function not found")
        return False
    
    # Check that onGlobalLevelChange calls loadAreas
    if 'loadAreas(\'globalAdminArea\'' not in content:
        print("❌ onGlobalLevelChange doesn't call loadAreas properly")
        return False
    
    print("✓ Frontend event handlers are properly set up")
    return True

def test_analytics_api_filtering():
    """Test that analytics API endpoints use geographic filtering."""
    print("Testing analytics API geographic filtering...")
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that analytics endpoints use filter_by_area
    analytics_endpoints = [
        'get_analytics_overview',
        'get_analytics_trends', 
        'get_analytics_heatmap',
        'get_analytics_status_distribution',
        'get_analytics_confidence',
        'get_analytics_repair_performance'
    ]
    
    missing_filtering = []
    for endpoint in analytics_endpoints:
        # Find the endpoint function
        endpoint_match = re.search(f'def {endpoint}.*?(?=def |$)', content, re.DOTALL)
        if not endpoint_match:
            missing_filtering.append(f"{endpoint} (function not found)")
            continue
            
        endpoint_code = endpoint_match.group(0)
        
        # Check if it uses admin_area and admin_level parameters
        if 'admin_area' not in endpoint_code or 'admin_level' not in endpoint_code:
            missing_filtering.append(f"{endpoint} (missing admin parameters)")
            continue
            
        # Check if it calls filter_by_area when admin_area is provided
        if 'filter_by_area' not in endpoint_code:
            missing_filtering.append(f"{endpoint} (missing filter_by_area call)")
    
    if missing_filtering:
        print(f"❌ Analytics endpoints missing geographic filtering: {missing_filtering}")
        return False
    
    print("✓ Analytics API endpoints use geographic filtering")
    return True

def test_html_structure():
    """Test that HTML has correct structure for geographic filters."""
    print("Testing HTML structure for geographic filters...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_elements = [
        'id="globalAdminLevel"',
        'id="globalAdminArea"',
        'value="region"',
        'value="province"', 
        'value="municipality"'
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print(f"❌ Missing HTML elements: {missing_elements}")
        return False
    
    print("✓ HTML structure for geographic filters is correct")
    return True

def main():
    """Run all tests."""
    print("Testing Geographic Filters in Analytics Page")
    print("=" * 50)
    
    try:
        data_ok = test_data_files_structure()
        loadareas_ok = test_loadareas_function()
        backend_ok = test_backend_filtering()
        handlers_ok = test_frontend_event_handlers()
        api_ok = test_analytics_api_filtering()
        html_ok = test_html_structure()
        
        print("\n" + "=" * 50)
        
        if all([data_ok, loadareas_ok, backend_ok, handlers_ok, api_ok, html_ok]):
            print("✅ All tests passed! Geographic filters should be working correctly.")
            print("\nIf you're still seeing issues:")
            print("1. Clear browser cache (Ctrl+F5)")
            print("2. Check browser console for JavaScript errors")
            print("3. Verify you're using the latest deployed version")
            print("4. Test with different admin levels:")
            print("   - Region: Should show region names")
            print("   - Province: Should show province names") 
            print("   - Municipality: Should show municipality names")
            print("5. Check that charts update when filters change")
            
            print("\nExpected behavior:")
            print("• Admin Level dropdown should have Region/Province/Municipality")
            print("• Changing admin level should populate area dropdown")
            print("• Area dropdown should show different options per level")
            print("• Charts should update when area filters are applied")
            print("• Apply Filters button should refresh all data")
            
        else:
            print("❌ Some tests failed. Geographic filters may not work correctly.")
            print("\nTo fix the issues:")
            print("• Ensure all data files exist and have correct structure")
            print("• Verify loadAreas function handles all admin levels")
            print("• Check that backend filtering uses correct property names")
            print("• Confirm event handlers are properly wired")
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()