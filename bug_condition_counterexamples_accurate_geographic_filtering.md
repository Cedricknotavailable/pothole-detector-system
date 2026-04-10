# Bug Condition Counterexamples - Accurate Geographic Filtering

## Bug Confirmation

The bug condition exploration test has **SUCCESSFULLY FAILED** on unfixed code, confirming the bug exists as described in the specification.

## Root Cause Identified

**Area Name Mismatch Between Frontend and GeoJSON Data**

- **Frontend Format**: Sends area names with spaces (e.g., "Ilocos Norte", "Laoag City")
- **GeoJSON Format**: Stores area names without spaces (e.g., "IlocosNorte", "LaoagCity")
- **Result**: Geometry lookup fails, causing fallback to sample data

## Counterexamples Found

### 1. Province Filtering Bug
- **Input**: `filter_by_area(query, Detection, 'Ilocos Norte', 'province')`
- **Expected**: Different result count than "All Areas" (accurate geographic filtering)
- **Actual**: Same result count as "All Areas" (75 records)
- **Cause**: No geometry found for "Ilocos Norte" → fallback to sample data
- **Evidence**: Console output shows "Warning: No geometry found for Ilocos Norte in province"

### 2. Municipality Filtering Bug  
- **Input**: `filter_by_area(query, Report, 'Laoag City', 'municipality')`
- **Expected**: Different result count than "All Areas" (accurate geographic filtering)
- **Actual**: Same result count as "All Areas" (29 records)
- **Cause**: No geometry found for "Laoag City" → fallback to sample data
- **Evidence**: Console output shows "Warning: No geometry found for Laoag City in municipality"

### 3. Verification of Correct Names
- **Test**: `filter_by_area(query, Detection, 'IlocosNorte', 'province')` (no spaces)
- **Result**: Geographic filtering works correctly (finds geometry, performs point-in-polygon calculations)
- **Test**: `filter_by_area(query, Report, 'LaoagCity', 'municipality')` (no spaces)  
- **Result**: Geographic filtering works correctly (finds geometry, performs point-in-polygon calculations)

## Technical Analysis

### Current Behavior (Buggy)
1. Frontend sends area name with spaces (e.g., "Ilocos Norte")
2. `load_geojson_polygons()` loads GeoJSON data with names without spaces
3. `polygons.get(area_name)` returns `None` due to key mismatch
4. Function logs warning and falls back to `query.limit(300).all()`
5. Result is indistinguishable from "All Areas" fast path

### Expected Behavior (Fixed)
1. Frontend sends area name with spaces (e.g., "Ilocos Norte")
2. System normalizes area name to match GeoJSON format (e.g., "IlocosNorte")
3. `polygons.get(normalized_name)` finds correct geometry
4. Point-in-polygon calculations filter data accurately
5. Result differs from "All Areas" and reflects actual geographic boundaries

## Available GeoJSON Area Names

### Provinces (sample)
- IlocosNorte, IlocosSur
- AgusandelNorte, AgusandelSur  
- CamarinesNorte, CamarinesSur
- Bataan, Batanes, Batangas
- (All names without spaces)

### Municipalities (sample)  
- LaoagCity, BaguioCity
- QuezonCity, MandaluyongCity
- (All names without spaces)

## Fix Requirements

The fix must implement area name normalization to bridge the gap between:
1. **Frontend format**: "Ilocos Norte", "Laoag City" (with spaces)
2. **GeoJSON format**: "IlocosNorte", "LaoagCity" (without spaces)

This can be achieved by:
- Removing spaces from area names before geometry lookup
- Implementing fuzzy matching for common variations
- Adding alias mapping for known mismatches
- Improving error handling to distinguish between missing geometry and name mismatches