"""
Bug Condition Exploration Test for Accurate Geographic Filtering

**Validates: Requirements 2.2, 2.3, 2.4**

This test MUST FAIL on unfixed code - failure confirms the bug exists.
The test encodes the expected behavior and will validate the fix when it passes after implementation.

CRITICAL: This test is EXPECTED TO FAIL on unfixed code (this is the SUCCESS case for exploration tests).
DO NOT attempt to fix the test or the code when it fails.
"""

import pytest
import time
import json
import os
from hypothesis import given, strategies as st, settings, example
from app import app, db, Detection, Report, filter_by_area


class TestBugConditionAccurateGeographicFiltering:
    """
    Property 1: Bug Condition - Accurate Geographic Filtering
    
    Test that when specific geographic areas are selected (admin_area not 'all' and 
    admin_level in ['province', 'municipality', 'region']), the filter_by_area function 
    returns different result counts than "All Areas" selection.
    """
    
    @pytest.fixture(autouse=True)
    def setup_app_context(self):
        """Setup Flask app context for each test"""
        with app.app_context():
            yield
    
    def test_province_filtering_returns_different_results_than_all_areas(self):
        """
        **Validates: Requirements 2.2**
        
        Test that selecting a specific province returns different results than "All Areas".
        This test MUST FAIL on unfixed code to confirm the bug exists.
        
        BUG: Frontend sends area names with spaces (e.g., "Ilocos Norte") but GeoJSON 
        files use names without spaces (e.g., "IlocosNorte"), causing geometry lookup 
        to fail and fall back to sample data.
        """
        with app.app_context():
            # Create test data with known coordinates
            # IlocosNorte province coordinates (approximate bounds)
            ilocos_norte_coords = [
                (18.2, 120.5),  # Within IlocosNorte
                (18.1, 120.6),  # Within IlocosNorte  
                (18.0, 120.7),  # Within IlocosNorte
            ]
            
            # Other province coordinates (outside IlocosNorte)
            other_coords = [
                (14.6, 121.0),  # Manila area
                (10.3, 123.9),  # Cebu area
                (7.1, 125.6),   # Davao area
            ]
            
            # Create test detections
            test_detections = []
            now = int(time.time())
            
            # Add detections in IlocosNorte
            for i, (lat, lng) in enumerate(ilocos_norte_coords):
                detection = Detection(
                    label='pothole',
                    confidence=0.9,
                    latitude=lat,
                    longitude=lng,
                    created_at=now - i
                )
                db.session.add(detection)
                test_detections.append(detection)
            
            # Add detections outside IlocosNorte
            for i, (lat, lng) in enumerate(other_coords):
                detection = Detection(
                    label='pothole',
                    confidence=0.8,
                    latitude=lat,
                    longitude=lng,
                    created_at=now - i - 10
                )
                db.session.add(detection)
                test_detections.append(detection)
            
            db.session.commit()
            
            try:
                # Test "All Areas" filtering
                all_areas_query = Detection.query
                all_areas_results = filter_by_area(all_areas_query, Detection, 'all', 'province')
                all_areas_count = len(all_areas_results)
                
                # Test specific province filtering using FRONTEND FORMAT (with spaces)
                # This is what the frontend would actually send
                ilocos_norte_query = Detection.query
                ilocos_norte_results = filter_by_area(ilocos_norte_query, Detection, 'Ilocos Norte', 'province')
                ilocos_norte_count = len(ilocos_norte_results)
                
                print(f"All Areas count: {all_areas_count}")
                print(f"Ilocos Norte (frontend format) count: {ilocos_norte_count}")
                
                # BUG CONDITION: On unfixed code, these counts will be identical due to area name mismatch
                # EXPECTED BEHAVIOR: They should be different (Ilocos Norte should have fewer results)
                assert ilocos_norte_count != all_areas_count, (
                    f"Bug detected: 'Ilocos Norte' filtering returned same count ({ilocos_norte_count}) "
                    f"as All Areas ({all_areas_count}). This indicates area name mismatch between "
                    f"frontend (with spaces) and GeoJSON data (without spaces), causing fallback to sample data."
                )
                
                # Additional validation: Ilocos Norte should have fewer results than All Areas
                assert ilocos_norte_count < all_areas_count, (
                    f"Expected 'Ilocos Norte' count ({ilocos_norte_count}) to be less than "
                    f"All Areas count ({all_areas_count})"
                )
                
                # Validate that Ilocos Norte results only contain points within the province
                for result in ilocos_norte_results:
                    lat, lng = result.latitude, result.longitude
                    # Check if coordinates are within IlocosNorte bounds (approximate)
                    assert 17.5 <= lat <= 18.5, f"Latitude {lat} outside IlocosNorte bounds"
                    assert 120.0 <= lng <= 121.0, f"Longitude {lng} outside IlocosNorte bounds"
                
            finally:
                # Clean up test data
                for detection in test_detections:
                    db.session.delete(detection)
                db.session.commit()
    
    def test_municipality_filtering_returns_different_results_than_all_areas(self):
        """
        **Validates: Requirements 2.3**
        
        Test that selecting a specific municipality returns different results than "All Areas".
        This test MUST FAIL on unfixed code to confirm the bug exists.
        
        BUG: Frontend sends area names with spaces (e.g., "Laoag City") but GeoJSON 
        files use names without spaces (e.g., "LaoagCity"), causing geometry lookup 
        to fail and fall back to sample data.
        """
        with app.app_context():
            # Create test data with known coordinates
            # LaoagCity coordinates (approximate bounds)
            laoag_coords = [
                (18.2, 120.59),  # Within LaoagCity
                (18.19, 120.58), # Within LaoagCity
            ]
            
            # Other municipality coordinates
            other_coords = [
                (14.6, 121.0),  # Manila area
                (16.4, 120.6),  # Baguio area
                (18.1, 120.3),  # Other part of Ilocos Norte
            ]
            
            # Create test reports
            test_reports = []
            now = int(time.time())
            
            # Add reports in LaoagCity
            for i, (lat, lng) in enumerate(laoag_coords):
                report = Report(
                    user_id=1,  # Assuming user ID 1 exists
                    title='Pothole report',
                    body='Test pothole',
                    latitude=lat,
                    longitude=lng,
                    obstruction_type='Pothole',
                    created_at=now - i
                )
                db.session.add(report)
                test_reports.append(report)
            
            # Add reports outside LaoagCity
            for i, (lat, lng) in enumerate(other_coords):
                report = Report(
                    user_id=1,
                    title='Road crack report',
                    body='Test crack',
                    latitude=lat,
                    longitude=lng,
                    obstruction_type='Road Crack',
                    created_at=now - i - 10
                )
                db.session.add(report)
                test_reports.append(report)
            
            db.session.commit()
            
            try:
                # Test "All Areas" filtering
                all_areas_query = Report.query.filter(Report.is_false_report == False)
                all_areas_results = filter_by_area(all_areas_query, Report, 'all', 'municipality')
                all_areas_count = len(all_areas_results)
                
                # Test specific municipality filtering using FRONTEND FORMAT (with spaces)
                # This is what the frontend would actually send
                laoag_query = Report.query.filter(Report.is_false_report == False)
                laoag_results = filter_by_area(laoag_query, Report, 'Laoag City', 'municipality')
                laoag_count = len(laoag_results)
                
                print(f"All Areas count: {all_areas_count}")
                print(f"Laoag City (frontend format) count: {laoag_count}")
                
                # BUG CONDITION: On unfixed code, these counts will be identical due to area name mismatch
                # EXPECTED BEHAVIOR: They should be different (Laoag City should have fewer results)
                assert laoag_count != all_areas_count, (
                    f"Bug detected: 'Laoag City' filtering returned same count ({laoag_count}) "
                    f"as All Areas ({all_areas_count}). This indicates area name mismatch between "
                    f"frontend (with spaces) and GeoJSON data (without spaces), causing fallback to sample data."
                )
                
                # Additional validation: Laoag City should have fewer results than All Areas
                assert laoag_count < all_areas_count, (
                    f"Expected 'Laoag City' count ({laoag_count}) to be less than "
                    f"All Areas count ({all_areas_count})"
                )
                
            finally:
                # Clean up test data
                for report in test_reports:
                    db.session.delete(report)
                db.session.commit()
    
    def test_different_areas_return_different_results(self):
        """
        **Validates: Requirements 2.4**
        
        Test that selecting different specific areas consecutively returns different results
        instead of identical results. This test MUST FAIL on unfixed code to confirm the bug exists.
        
        BUG: Frontend sends area names with spaces but GeoJSON files use names without spaces,
        causing all specific area selections to fall back to sample data and return identical results.
        """
        with app.app_context():
            # Create test data in different provinces
            test_detections = []
            now = int(time.time())
            
            # IlocosNorte coordinates
            ilocos_coords = [(18.2, 120.5), (18.1, 120.6)]
            
            # Bataan coordinates (different province)
            bataan_coords = [(14.7, 120.4), (14.6, 120.5)]
            
            # Add detections in IlocosNorte
            for i, (lat, lng) in enumerate(ilocos_coords):
                detection = Detection(
                    label='pothole',
                    confidence=0.9,
                    latitude=lat,
                    longitude=lng,
                    created_at=now - i
                )
                db.session.add(detection)
                test_detections.append(detection)
            
            # Add detections in Bataan
            for i, (lat, lng) in enumerate(bataan_coords):
                detection = Detection(
                    label='roadcrack',
                    confidence=0.8,
                    latitude=lat,
                    longitude=lng,
                    created_at=now - i - 10
                )
                db.session.add(detection)
                test_detections.append(detection)
            
            db.session.commit()
            
            try:
                # Test Ilocos Norte filtering using FRONTEND FORMAT (with spaces)
                ilocos_query = Detection.query
                ilocos_results = filter_by_area(ilocos_query, Detection, 'Ilocos Norte', 'province')
                ilocos_count = len(ilocos_results)
                
                # Test Bataan filtering using FRONTEND FORMAT (with spaces)
                bataan_query = Detection.query
                bataan_results = filter_by_area(bataan_query, Detection, 'Bataan', 'province')
                bataan_count = len(bataan_results)
                
                print(f"Ilocos Norte (frontend format) count: {ilocos_count}")
                print(f"Bataan (frontend format) count: {bataan_count}")
                
                # BUG CONDITION: On unfixed code, these counts will be identical due to area name mismatch
                # Both will fall back to sample data and return the same count
                # EXPECTED BEHAVIOR: They should be different (each province should have different results)
                assert ilocos_count != bataan_count, (
                    f"Bug detected: Different provinces returned identical counts "
                    f"(Ilocos Norte: {ilocos_count}, Bataan: {bataan_count}). "
                    f"This indicates area name mismatch causing both to fall back to sample data."
                )
                
            finally:
                # Clean up test data
                for detection in test_detections:
                    db.session.delete(detection)
                db.session.commit()
    
    @given(
        area_name=st.sampled_from(['Ilocos Norte', 'Bataan', 'Cebu', 'Laoag City', 'Baguio City']),
        area_type=st.sampled_from(['province', 'municipality', 'region'])
    )
    @example(area_name='Ilocos Norte', area_type='province')
    @example(area_name='Laoag City', area_type='municipality')
    @settings(max_examples=10, deadline=30000)  # Limit examples for faster execution
    def test_property_specific_areas_differ_from_all_areas(self, area_name, area_type):
        """
        **Validates: Requirements 2.2, 2.3, 2.4**
        
        Property-based test: For any specific geographic area selection, the result count
        should differ from "All Areas" selection when appropriate geometry data exists.
        
        This test MUST FAIL on unfixed code to confirm the bug exists across multiple areas.
        """
        with app.app_context():
            # Skip invalid combinations
            if area_type == 'province' and area_name in ['Laoag City', 'Baguio City']:
                return
            if area_type == 'municipality' and area_name in ['Ilocos Norte', 'Bataan', 'Cebu']:
                return
            
            # Create minimal test data
            test_detection = Detection(
                label='pothole',
                confidence=0.9,
                latitude=14.6,  # Manila area coordinates
                longitude=121.0,
                created_at=int(time.time())
            )
            db.session.add(test_detection)
            db.session.commit()
            
            try:
                # Test "All Areas" filtering
                all_areas_query = Detection.query
                all_areas_results = filter_by_area(all_areas_query, Detection, 'all', area_type)
                all_areas_count = len(all_areas_results)
                
                # Test specific area filtering
                specific_query = Detection.query
                specific_results = filter_by_area(specific_query, Detection, area_name, area_type)
                specific_count = len(specific_results)
                
                print(f"All Areas ({area_type}) count: {all_areas_count}")
                print(f"{area_name} ({area_type}) count: {specific_count}")
                
                # BUG CONDITION: On unfixed code, these counts will often be identical
                # EXPECTED BEHAVIOR: They should be different when geometry exists and filtering works
                
                # Check if geometry data exists for this area
                from app import load_geojson_polygons
                polygons = load_geojson_polygons(area_type)
                has_geometry = area_name in polygons
                
                if has_geometry and all_areas_count > 0:
                    # If geometry exists and there's data, specific area should potentially differ
                    # This assertion will fail on unfixed code, confirming the bug
                    assert specific_count != all_areas_count or specific_count == 0, (
                        f"Bug detected: {area_name} ({area_type}) filtering returned same count "
                        f"({specific_count}) as All Areas ({all_areas_count}) despite having geometry data. "
                        f"Geographic filtering is not working correctly."
                    )
                
            finally:
                # Clean up test data
                db.session.delete(test_detection)
                db.session.commit()


if __name__ == '__main__':
    # Run the test to demonstrate the bug
    pytest.main([__file__, '-v', '-s'])