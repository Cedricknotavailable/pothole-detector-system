"""
Preservation Property Tests - Accurate Geographic Filtering

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

These tests capture the EXISTING behavior on UNFIXED code for non-buggy inputs.
They ensure that the fix does NOT introduce regressions.

IMPORTANT: Follow observation-first methodology
- These tests are written AFTER observing behavior on UNFIXED code
- They capture the baseline behavior that must be preserved
- EXPECTED OUTCOME ON UNFIXED CODE: PASS (confirms baseline behavior)
- EXPECTED OUTCOME ON FIXED CODE: PASS (confirms no regressions)

Property 2: Preservation - Fast Path and Error Handling
For any input where admin_area is 'all' or null, or where error conditions occur,
the system should continue to behave exactly as before.
"""

import pytest
import os
import sys
import json
import time
from hypothesis import given, strategies as st, settings, Phase, HealthCheck

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app, db, Detection, Report, filter_by_area, load_geojson_polygons


@pytest.fixture
def client():
    """Create test client with isolated database"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


@pytest.fixture
def sample_detections():
    """Create sample detection data for testing"""
    with app.app_context():
        # Clear existing data
        Detection.query.delete()
        
        # Create sample detections with coordinates
        detections = [
            Detection(
                latitude=18.1967, longitude=120.5937,  # Ilocos Norte coordinates
                label='pothole', detected_class='pothole',
                confidence=0.85, is_fixed=False,
                created_at=int(time.time())
            ),
            Detection(
                latitude=14.5995, longitude=120.9842,  # Manila coordinates
                label='crack', detected_class='crack',
                confidence=0.75, is_fixed=False,
                created_at=int(time.time())
            ),
            Detection(
                latitude=16.4023, longitude=120.5960,  # Baguio coordinates
                label='pothole', detected_class='pothole',
                confidence=0.90, is_fixed=True,
                created_at=int(time.time())
            ),
        ]
        
        for detection in detections:
            db.session.add(detection)
        
        db.session.commit()
        return detections


# ============================================================================
# Property 2.1: "All Areas" Fast Path Preservation (Requirement 3.1)
# ============================================================================

def test_preservation_all_areas_fast_path(client, sample_detections):
    """
    Property 2.1: "All Areas" selection continues to return fast sample data (500 records)
    
    **Validates: Requirement 3.1**
    
    When admin_area is 'all' or None, the system should continue to use
    the fast path and return sample data for general overview.
    """
    
    with app.app_context():
        query = Detection.query
        
        # Test with admin_area = 'all'
        result_all = filter_by_area(query, Detection, 'all', 'province')
        
        # Test with admin_area = None
        result_none = filter_by_area(query, Detection, None, 'province')
        
        # Test with empty string
        result_empty = filter_by_area(query, Detection, '', 'province')
        
        # All should return the same fast path behavior
        assert len(result_all) == len(sample_detections), \
            "All areas selection should return sample data"
        assert len(result_none) == len(sample_detections), \
            "None area selection should return sample data"
        assert len(result_empty) == len(sample_detections), \
            "Empty area selection should return sample data"
        
        # Verify they return the same records (fast path behavior)
        result_all_ids = {d.id for d in result_all}
        result_none_ids = {d.id for d in result_none}
        result_empty_ids = {d.id for d in result_empty}
        
        assert result_all_ids == result_none_ids == result_empty_ids, \
            "All fast path variations should return identical results"


@given(
    area_name=st.sampled_from(['all', None, '', 'ALL', 'All']),
    area_type=st.sampled_from(['province', 'municipality', 'region'])
)
@settings(max_examples=10, phases=[Phase.generate], suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_preservation_fast_path_property_based(client, sample_detections, area_name, area_type):
    """
    Property-based test: Fast path behavior is consistent across variations
    
    **Validates: Requirement 3.1**
    
    For any variation of "all areas" input, the system should return
    the same fast path sample data.
    """
    
    with app.app_context():
        query = Detection.query
        result = filter_by_area(query, Detection, area_name, area_type)
        
        # Should return sample data (not empty, not error)
        assert isinstance(result, list), \
            f"Fast path should return list for area_name='{area_name}', area_type='{area_type}'"
        
        # Should return all available records (fast path behavior)
        assert len(result) == len(sample_detections), \
            f"Fast path should return sample data for area_name='{area_name}', area_type='{area_type}'"


# ============================================================================
# Property 2.2: Error Handling Preservation (Requirement 3.2)
# ============================================================================

def test_preservation_graceful_error_fallback(client, sample_detections):
    """
    Property 2.2: Error handling continues to fall back gracefully without crashing
    
    **Validates: Requirement 3.2**
    
    When errors occur (missing geometry, invalid data), the system should
    continue to fall back to sample data without crashing.
    """
    
    with app.app_context():
        query = Detection.query
        
        # Test with non-existent area (should fallback gracefully)
        result_invalid = filter_by_area(query, Detection, 'NonExistentArea', 'province')
        
        # Should not crash and should return some data (fallback behavior)
        assert isinstance(result_invalid, list), \
            "Invalid area should return list (graceful fallback)"
        
        # Should return fallback sample data (current behavior on unfixed code)
        # This captures the current fallback behavior that should be preserved
        assert len(result_invalid) > 0, \
            "Invalid area should return fallback sample data"


def test_preservation_missing_geometry_fallback(client, sample_detections):
    """
    Property 2.2b: Missing geometry data falls back gracefully
    
    **Validates: Requirement 3.2**
    
    When geometry data is missing or invalid, the system should
    fall back gracefully without crashing.
    """
    
    with app.app_context():
        query = Detection.query
        
        # Test with area type that might have missing geometry
        result = filter_by_area(query, Detection, 'TestArea', 'invalid_type')
        
        # Should not crash
        assert isinstance(result, list), \
            "Missing geometry should return list (graceful fallback)"


# ============================================================================
# Property 2.3: GeoJSON Caching Preservation (Requirement 3.3)
# ============================================================================

def test_preservation_geojson_caching(client):
    """
    Property 2.3: GeoJSON geometry data caching continues to work for performance
    
    **Validates: Requirement 3.3**
    
    The GeoJSON loading and caching mechanism should continue to work
    for performance optimization.
    """
    
    with app.app_context():
        # First call should load and cache
        polygons1 = load_geojson_polygons('province')
        
        # Second call should use cache
        polygons2 = load_geojson_polygons('province')
        
        # Should return the same data (caching working)
        assert polygons1 is polygons2, \
            "GeoJSON caching should return same object reference"
        
        # Should contain expected data structure
        assert isinstance(polygons1, dict), \
            "GeoJSON loader should return dictionary"
        
        # Test different area types
        municipalities = load_geojson_polygons('municipality')
        regions = load_geojson_polygons('region')
        
        assert isinstance(municipalities, dict), \
            "Municipality GeoJSON should load as dictionary"
        assert isinstance(regions, dict), \
            "Region GeoJSON should load as dictionary"


# ============================================================================
# Property 2.4: Optimized Algorithm Preservation (Requirement 3.4)
# ============================================================================

def test_preservation_optimized_algorithms(client, sample_detections):
    """
    Property 2.4: Point-in-polygon calculations continue to use optimized algorithms
    
    **Validates: Requirement 3.4**
    
    The optimized point-in-polygon calculations with bounds checking and
    numerical stability improvements should continue to work.
    """
    
    with app.app_context():
        query = Detection.query
        
        # Test with a real province name to trigger optimized calculations
        # This will test the current behavior (even if buggy)
        result = filter_by_area(query, Detection, 'Ilocos Norte', 'province')
        
        # Should not crash (optimized algorithms handle edge cases)
        assert isinstance(result, list), \
            "Optimized algorithms should return list without crashing"
        
        # Should complete in reasonable time (performance optimization)
        import time
        start_time = time.time()
        result2 = filter_by_area(query, Detection, 'Bataan', 'province')
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < 30, \
            f"Optimized algorithms should complete within 30 seconds, took {elapsed_time:.2f}s"
        
        assert isinstance(result2, list), \
            "Optimized algorithms should return list for different provinces"


# ============================================================================
# Property 2.5: Performance and Stability Preservation
# ============================================================================

def test_preservation_performance_stability(client, sample_detections):
    """
    Property 2.5: Performance and stability are maintained
    
    **Validates: Performance preservation**
    
    The geographic filtering should continue to perform well and not crash
    under normal operating conditions.
    """
    
    with app.app_context():
        query = Detection.query
        
        # Test multiple calls to ensure stability
        for i in range(3):
            result = filter_by_area(query, Detection, 'all', 'province')
            assert isinstance(result, list), \
                f"Call {i+1}: Should return list without crashing"
            assert len(result) == len(sample_detections), \
                f"Call {i+1}: Should return consistent results"
        
        # Test different area types for stability
        area_types = ['province', 'municipality', 'region']
        for area_type in area_types:
            result = filter_by_area(query, Detection, 'all', area_type)
            assert isinstance(result, list), \
                f"Area type '{area_type}' should return list without crashing"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])