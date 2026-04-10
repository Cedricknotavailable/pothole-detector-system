#!/usr/bin/env python3
"""
Test script to verify the geographic filtering fix is working correctly.
This tests the actual analytics API endpoints to ensure the fix works in practice.
"""

import requests
import json
import time

def test_geographic_filtering_fix():
    """Test the geographic filtering fix by calling the analytics API endpoints."""
    
    print("🧪 Testing Geographic Filtering Fix")
    print("=" * 50)
    
    base_url = "http://localhost:5000"  # Adjust if your app runs on a different port
    
    # Test parameters
    test_params = {
        'start_date': '2024-01-01',
        'end_date': '2026-12-31',
        'admin_level': 'province'
    }
    
    try:
        print("\n🚀 Testing Analytics Overview Endpoint")
        print("-" * 40)
        
        # Test 1: All Areas (should be fast)
        print("1. Testing 'All Areas' (fast path)...")
        all_areas_params = {**test_params, 'admin_area': 'all'}
        
        start_time = time.time()
        response = requests.get(f"{base_url}/api/analytics/overview", params=all_areas_params)
        all_areas_time = time.time() - start_time
        
        if response.status_code == 200:
            all_areas_data = response.json()
            print(f"   ✅ All Areas: {all_areas_data['total_potholes']} potholes, {all_areas_data['total_reports']} reports")
            print(f"   ⏱️  Response time: {all_areas_time:.3f}s")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
            return False
        
        # Test 2: Specific Province (should use geographic filtering)
        print("\n2. Testing 'Ilocos Norte' province (geographic filtering)...")
        ilocos_params = {**test_params, 'admin_area': 'Ilocos Norte'}
        
        start_time = time.time()
        response = requests.get(f"{base_url}/api/analytics/overview", params=ilocos_params)
        ilocos_time = time.time() - start_time
        
        if response.status_code == 200:
            ilocos_data = response.json()
            print(f"   ✅ Ilocos Norte: {ilocos_data['total_potholes']} potholes, {ilocos_data['total_reports']} reports")
            print(f"   ⏱️  Response time: {ilocos_time:.3f}s")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
            return False
        
        # Test 3: Different Province (should return different results)
        print("\n3. Testing 'Bataan' province (different area)...")
        bataan_params = {**test_params, 'admin_area': 'Bataan'}
        
        start_time = time.time()
        response = requests.get(f"{base_url}/api/analytics/overview", params=bataan_params)
        bataan_time = time.time() - start_time
        
        if response.status_code == 200:
            bataan_data = response.json()
            print(f"   ✅ Bataan: {bataan_data['total_potholes']} potholes, {bataan_data['total_reports']} reports")
            print(f"   ⏱️  Response time: {bataan_time:.3f}s")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
            return False
        
        print("\n📊 Testing Heatmap Endpoint")
        print("-" * 30)
        
        # Test 4: Heatmap with All Areas
        print("4. Testing heatmap with 'All Areas'...")
        response = requests.get(f"{base_url}/api/analytics/heatmap", params=all_areas_params)
        
        if response.status_code == 200:
            all_heatmap_points = response.json()
            print(f"   ✅ All Areas heatmap: {len(all_heatmap_points)} points")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
            return False
        
        # Test 5: Heatmap with Specific Province
        print("5. Testing heatmap with 'Ilocos Norte'...")
        response = requests.get(f"{base_url}/api/analytics/heatmap", params=ilocos_params)
        
        if response.status_code == 200:
            ilocos_heatmap_points = response.json()
            print(f"   ✅ Ilocos Norte heatmap: {len(ilocos_heatmap_points)} points")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
            return False
        
        print("\n🎯 Results Analysis")
        print("-" * 25)
        
        # Analyze results
        success = True
        
        # Check if specific areas return different results than All Areas
        if (all_areas_data['total_potholes'] == ilocos_data['total_potholes'] and 
            all_areas_data['total_reports'] == ilocos_data['total_reports'] and
            all_areas_data['total_potholes'] > 0):
            print("   ⚠️  WARNING: Ilocos Norte returned same results as All Areas")
            print("       This might indicate the geographic filtering is still not working")
            success = False
        else:
            print("   ✅ Ilocos Norte returned different results than All Areas")
        
        if (ilocos_data['total_potholes'] == bataan_data['total_potholes'] and 
            ilocos_data['total_reports'] == bataan_data['total_reports'] and
            ilocos_data['total_potholes'] > 0):
            print("   ⚠️  WARNING: Ilocos Norte and Bataan returned identical results")
            print("       This might indicate the geographic filtering is still not working")
            success = False
        else:
            print("   ✅ Different provinces returned different results")
        
        if len(all_heatmap_points) == len(ilocos_heatmap_points) and len(all_heatmap_points) > 0:
            print("   ⚠️  WARNING: Heatmap points are identical for All Areas vs Ilocos Norte")
            success = False
        else:
            print("   ✅ Heatmap filtering appears to be working")
        
        # Performance check
        if all_areas_time > 5.0:
            print(f"   ⚠️  WARNING: All Areas response time ({all_areas_time:.3f}s) is slow")
        else:
            print(f"   ✅ All Areas response time is good ({all_areas_time:.3f}s)")
        
        if success:
            print("\n🎉 Geographic filtering fix appears to be working correctly!")
            print("   • Different areas return different results")
            print("   • API endpoints are responding without 502/503 errors")
            print("   • Performance is acceptable")
        else:
            print("\n❌ Geographic filtering may still have issues")
            print("   • Check the console logs for any error messages")
            print("   • Verify that GeoJSON files exist in static/data/")
            print("   • Test manually in the browser analytics page")
        
        return success
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the application")
        print("   Make sure your Flask app is running on http://localhost:5000")
        print("   Start it with: python app.py")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_geojson_files():
    """Test if the required GeoJSON files exist."""
    
    print("\n📁 Checking GeoJSON Files")
    print("-" * 30)
    
    import os
    
    geojson_files = [
        'static/data/provinces.json',
        'static/data/municipalities.json', 
        'static/data/regions.json'
    ]
    
    all_exist = True
    for file_path in geojson_files:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"   ✅ {file_path} ({file_size:,} bytes)")
        else:
            print(f"   ❌ {file_path} - MISSING")
            all_exist = False
    
    return all_exist

if __name__ == '__main__':
    print("🚀 Geographic Filtering Fix Test Suite")
    print("=" * 60)
    
    # Check GeoJSON files first
    geojson_ok = test_geojson_files()
    
    if not geojson_ok:
        print("\n❌ Missing GeoJSON files - geographic filtering will not work")
        print("   Please ensure the required data files are in static/data/")
    else:
        print("\n✅ All required GeoJSON files are present")
    
    # Test the API endpoints
    print("\n" + "="*60)
    api_ok = test_geographic_filtering_fix()
    
    print("\n" + "="*60)
    if geojson_ok and api_ok:
        print("🎉 ALL TESTS PASSED - Geographic filtering fix is working!")
    else:
        print("❌ Some tests failed - please check the issues above")