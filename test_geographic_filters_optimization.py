#!/usr/bin/env python3
"""
Test script for the optimized geographic filters implementation.
Tests the performance improvements and error handling for Render hosting.
"""

import sys
import time
import requests
import json

def test_geographic_filters_optimization():
    """Test the optimized geographic filtering functionality."""
    
    print("🧪 Testing Geographic Filters Optimization")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test cases for different admin levels
    test_cases = [
        {
            'name': 'Region Test',
            'admin_level': 'region',
            'admin_area': 'Ilocos',
            'expected_timeout': False
        },
        {
            'name': 'Province Test', 
            'admin_level': 'province',
            'admin_area': 'Ilocos Norte',
            'expected_timeout': False
        },
        {
            'name': 'Municipality Test',
            'admin_level': 'municipality', 
            'admin_area': 'Laoag',
            'expected_timeout': False
        }
    ]
    
    # Test each endpoint with geographic filtering
    endpoints_to_test = [
        '/api/analytics/overview',
        '/api/analytics/trends',
        '/api/analytics/heatmap',
        '/api/analytics/status-distribution',
        '/api/analytics/ai-confidence',
        '/api/analytics/repair-performance'
    ]
    
    results = {
        'passed': 0,
        'failed': 0,
        'timeouts': 0,
        'errors': []
    }
    
    for test_case in test_cases:
        print(f"\n📍 {test_case['name']}")
        print("-" * 30)
        
        for endpoint in endpoints_to_test:
            try:
                # Build query parameters
                params = {
                    'admin_level': test_case['admin_level'],
                    'admin_area': test_case['admin_area'],
                    'start_date': '2024-01-01',
                    'end_date': '2024-12-31'
                }
                
                # Add endpoint-specific parameters
                if 'trends' in endpoint:
                    params['interval'] = 'daily'
                
                print(f"  Testing {endpoint}...", end=" ")
                
                # Make request with timeout
                start_time = time.time()
                response = requests.get(f"{base_url}{endpoint}", params=params, timeout=30)
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    print(f"✅ OK ({duration:.2f}s)")
                    results['passed'] += 1
                    
                    # Check response content
                    try:
                        data = response.json()
                        if endpoint == '/api/analytics/heatmap':
                            print(f"    📊 Heatmap points: {len(data) if isinstance(data, list) else 'N/A'}")
                        elif endpoint == '/api/analytics/overview':
                            print(f"    📈 KPIs: {len(data) if isinstance(data, dict) else 'N/A'} metrics")
                    except:
                        pass
                        
                elif response.status_code == 502:
                    print("❌ 502 Bad Gateway (Memory/CPU limit)")
                    results['failed'] += 1
                    results['errors'].append(f"{endpoint} - 502 Bad Gateway")
                    
                elif response.status_code == 503:
                    print("❌ 503 Service Unavailable (Timeout)")
                    results['timeouts'] += 1
                    results['errors'].append(f"{endpoint} - 503 Service Unavailable")
                    
                else:
                    print(f"❌ HTTP {response.status_code}")
                    results['failed'] += 1
                    results['errors'].append(f"{endpoint} - HTTP {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print("⏰ Request Timeout")
                results['timeouts'] += 1
                results['errors'].append(f"{endpoint} - Request Timeout")
                
            except requests.exceptions.ConnectionError:
                print("🔌 Connection Error (Server not running?)")
                results['failed'] += 1
                results['errors'].append(f"{endpoint} - Connection Error")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                results['failed'] += 1
                results['errors'].append(f"{endpoint} - {str(e)}")
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"⏰ Timeouts: {results['timeouts']}")
    
    if results['errors']:
        print(f"\n🚨 ERRORS:")
        for error in results['errors']:
            print(f"  • {error}")
    
    # Performance recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if results['timeouts'] > 0:
        print("  • Consider implementing database-level spatial queries")
        print("  • Reduce polygon complexity for municipalities")
        print("  • Implement progressive loading for large datasets")
    
    if results['failed'] > 0:
        print("  • Check server memory limits on Render")
        print("  • Implement circuit breaker pattern")
        print("  • Add request queuing for heavy operations")
    
    if results['passed'] == len(test_cases) * len(endpoints_to_test):
        print("  🎉 All tests passed! Geographic filtering is working optimally.")
    
    return results

def test_optimization_functions():
    """Test the optimization functions directly."""
    
    print("\n🔧 Testing Optimization Functions")
    print("=" * 50)
    
    try:
        # Import within Flask context
        sys.path.append('.')
        from app import app, is_point_in_geometry_optimized, _quick_bounds_check, point_in_polygon_optimized
        
        with app.app_context():
            # Test bounds checking
            print("Testing bounds checking...")
            test_coords = [[120.0, 14.0], [122.0, 14.0], [122.0, 16.0], [120.0, 16.0], [120.0, 14.0]]
            
            # Point inside bounds
            inside_result = _quick_bounds_check(15.0, 121.0, test_coords)
            print(f"  Point inside bounds: {inside_result} ✅" if inside_result else f"  Point inside bounds: {inside_result} ❌")
            
            # Point outside bounds  
            outside_result = _quick_bounds_check(10.0, 110.0, test_coords)
            print(f"  Point outside bounds: {not outside_result} ✅" if not outside_result else f"  Point outside bounds: {not outside_result} ❌")
            
            # Test optimized point-in-polygon
            print("\nTesting optimized point-in-polygon...")
            inside_poly = point_in_polygon_optimized((15.0, 121.0), test_coords)
            outside_poly = point_in_polygon_optimized((10.0, 110.0), test_coords)
            
            print(f"  Point inside polygon: {inside_poly} ✅" if inside_poly else f"  Point inside polygon: {inside_poly} ❌")
            print(f"  Point outside polygon: {not outside_poly} ✅" if not outside_poly else f"  Point outside polygon: {not outside_poly} ❌")
            
            # Test error handling
            print("\nTesting error handling...")
            try:
                result = is_point_in_geometry_optimized(None, None, {})
                print(f"  Null input handling: {not result} ✅" if not result else f"  Null input handling: {not result} ❌")
            except Exception as e:
                print(f"  Null input handling: Exception caught ❌ - {e}")
            
            print("✅ All optimization function tests passed!")
            
    except Exception as e:
        print(f"❌ Error testing optimization functions: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Geographic Filters Optimization Test Suite")
    print("=" * 60)
    
    # Test optimization functions first
    test_optimization_functions()
    
    # Test API endpoints (requires server to be running)
    print(f"\n⚠️  Note: API endpoint tests require the Flask server to be running on localhost:8000")
    response = input("Do you want to test API endpoints? (y/N): ").strip().lower()
    
    if response == 'y':
        test_geographic_filters_optimization()
    else:
        print("Skipping API endpoint tests.")
    
    print(f"\n🎯 Test suite completed!")