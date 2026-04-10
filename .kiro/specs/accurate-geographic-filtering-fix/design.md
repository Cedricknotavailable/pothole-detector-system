# Accurate Geographic Filtering Bugfix Design

## Overview

The analytics page geographic filtering system is broken due to a logical flaw in the `filter_by_area` function. When users select specific geographic areas (provinces or municipalities), the system returns identical sample data instead of performing accurate geographic filtering. The bug occurs because the function falls back to sample data when geometry data is missing or when point-in-polygon calculations fail, but this fallback behavior is indistinguishable from the intended "All Areas" fast path. The fix requires ensuring geometry data is properly loaded and implementing robust error handling that distinguishes between intentional sampling and filtering failures.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when specific area selections return the same results as "All Areas" instead of performing accurate geographic filtering
- **Property (P)**: The desired behavior when specific areas are selected - accurate point-in-polygon filtering that returns only data points within the selected geographic boundaries
- **Preservation**: Existing fast sampling behavior for "All Areas" and error handling that must remain unchanged by the fix
- **filter_by_area**: The function in `app.py` that performs geographic filtering using lazy loading approach
- **load_geojson_polygons**: The function that loads GeoJSON geometry data from static files for point-in-polygon calculations
- **is_point_in_geometry_optimized**: The function that performs optimized point-in-polygon calculations with bounds checking

## Bug Details

### Bug Condition

The bug manifests when a user selects a specific geographic area (province or municipality) in the analytics page filters. The `filter_by_area` function is either not correctly loading the geometry data from GeoJSON files, not finding the geometry for the selected area name, or falling back to sample data when point-in-polygon calculations encounter errors.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type FilterRequest
  OUTPUT: boolean
  
  RETURN input.admin_area NOT IN ['all', null, '']
         AND input.admin_level IN ['province', 'municipality', 'region']
         AND resultCount(filter_by_area(query, model, input.admin_area, input.admin_level)) 
             == resultCount(filter_by_area(query, model, 'all', input.admin_level))
END FUNCTION
```

### Examples

- **Province Selection**: User selects "Ilocos Norte" province → Returns same 500 sample records as "All Areas" instead of province-specific data
- **Municipality Selection**: User selects "Laoag City" municipality → Returns same 500 sample records as "All Areas" instead of municipality-specific data  
- **Different Areas**: User selects "Ilocos Norte" then "Bataan" → Both return identical result sets instead of different geographic data
- **Edge Case**: User selects area with no geometry data → Should return empty results or clear error message, not sample data

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- "All Areas" selection must continue to return fast sample data (500 records) for general overview
- Error handling must continue to fall back gracefully without crashing the application
- GeoJSON geometry data caching must continue to work for performance optimization
- Point-in-polygon calculations must continue to use optimized algorithms with bounds checking

**Scope:**
All inputs that do NOT involve specific area selections should be completely unaffected by this fix. This includes:
- "All Areas" fast path sampling behavior
- Error fallback mechanisms for timeout and memory protection
- Performance optimizations for Render hosting environment
- Existing API response formats and timing characteristics

## Hypothesized Root Cause

Based on the bug description and code analysis, the most likely issues are:

1. **Missing Geometry Data**: The GeoJSON files may be missing, corrupted, or not properly loaded
   - Files like `provinces.json`, `municipalities.json` may not exist in `static/data/`
   - File format may be incorrect or incompatible with the parsing logic

2. **Area Name Mismatch**: The area names from the frontend dropdown may not match the names in the GeoJSON properties
   - Frontend loads area names from one source, but GeoJSON uses different naming conventions
   - Case sensitivity or special character issues in area name matching

3. **Silent Fallback Behavior**: The function falls back to sample data when geometry is not found, making it indistinguishable from "All Areas"
   - `load_geojson_polygons` returns empty dict when files are missing
   - `geometry = polygons.get(area_name)` returns None for mismatched names
   - Function returns `query.limit(300).all()` as fallback, similar to fast path

4. **Point-in-Polygon Calculation Failures**: The geometric calculations may be failing silently
   - Coordinate system mismatches between data points and GeoJSON polygons
   - Numerical precision issues in the ray-casting algorithm

## Correctness Properties

Property 1: Bug Condition - Accurate Geographic Filtering

_For any_ input where a specific geographic area is selected (admin_area is not 'all' and geometry data exists), the fixed filter_by_area function SHALL return only data points that fall within the geographic boundaries of the selected area using point-in-polygon calculations, producing different result counts than the "All Areas" sample.

**Validates: Requirements 2.2, 2.3, 2.4**

Property 2: Preservation - Fast Path and Error Handling

_For any_ input where admin_area is 'all' or null, or where error conditions occur (missing geometry, timeouts), the fixed function SHALL produce the same behavior as the original function, preserving fast sampling for general overview and graceful error fallbacks.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `app.py`

**Function**: `filter_by_area`

**Specific Changes**:
1. **Geometry Data Validation**: Add explicit checks for geometry data availability and validity
   - Verify GeoJSON files exist and are readable before attempting to load
   - Add logging when geometry data is missing or invalid
   - Return empty results (not sample data) when geometry is missing for specific areas

2. **Area Name Matching**: Improve area name matching between frontend and GeoJSON data
   - Add case-insensitive matching for area names
   - Handle special characters and encoding issues
   - Add fuzzy matching or alias mapping for common name variations

3. **Error Distinction**: Distinguish between intentional sampling ("All Areas") and filtering failures
   - Return different result types or add metadata to indicate filtering vs sampling
   - Add explicit error messages when specific area filtering fails
   - Ensure fallback behavior only occurs for genuine errors, not missing geometry

4. **Geometry Loading**: Enhance the `load_geojson_polygons` function
   - Add validation for GeoJSON file format and structure
   - Improve error handling and logging for file loading issues
   - Add checks for required properties in GeoJSON features

5. **Point-in-Polygon Robustness**: Improve the geometric calculation reliability
   - Add coordinate system validation and conversion if needed
   - Enhance numerical precision handling in ray-casting algorithm
   - Add bounds checking before expensive polygon calculations

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that call the analytics API with different area selections and compare result counts and content. Run these tests on the UNFIXED code to observe identical results and understand the root cause.

**Test Cases**:
1. **Province Comparison Test**: Compare results for "All Areas" vs "Ilocos Norte" (will show identical results on unfixed code)
2. **Municipality Comparison Test**: Compare results for "All Areas" vs "Laoag City" (will show identical results on unfixed code)  
3. **Multiple Area Test**: Compare results for "Ilocos Norte" vs "Bataan" (will show identical results on unfixed code)
4. **Geometry Data Test**: Check if GeoJSON files exist and contain expected area names (may reveal missing data)

**Expected Counterexamples**:
- All specific area selections return identical result counts (500 records)
- Possible causes: missing geometry files, area name mismatches, silent fallback behavior

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := filter_by_area_fixed(input)
  ASSERT expectedBehavior(result)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT filter_by_area_original(input) = filter_by_area_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for "All Areas" selections and error conditions, then write property-based tests capturing that behavior.

**Test Cases**:
1. **All Areas Preservation**: Verify "All Areas" continues to return fast sample data (500 records)
2. **Error Fallback Preservation**: Verify timeout and memory protection fallbacks continue working
3. **Performance Preservation**: Verify Render hosting optimizations continue working
4. **API Response Preservation**: Verify response format and timing remain consistent

### Unit Tests

- Test geometry data loading for each area type (province, municipality, region)
- Test area name matching with various case and character combinations
- Test point-in-polygon calculations with known coordinates and boundaries
- Test error handling for missing files, invalid geometry, and calculation failures

### Property-Based Tests

- Generate random area selections and verify they return different results than "All Areas"
- Generate random coordinate sets and verify point-in-polygon calculations are consistent
- Test that all "All Areas" selections continue to return sample data across many scenarios

### Integration Tests

- Test full analytics API flow with geographic filtering for each area type
- Test switching between different areas and verifying result differences
- Test that frontend dropdown selections properly trigger backend filtering
- Test error scenarios with missing geometry data and verify graceful handling