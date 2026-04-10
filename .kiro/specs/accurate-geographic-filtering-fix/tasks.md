# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Accurate Geographic Filtering
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: For deterministic bugs, scope the property to the concrete failing case(s) to ensure reproducibility
  - Test that when specific geographic areas are selected (admin_area not 'all' and admin_level in ['province', 'municipality', 'region']), the filter_by_area function returns different result counts than "All Areas" selection
  - The test assertions should match the Expected Behavior Properties from design: accurate point-in-polygon filtering that returns only data points within selected geographic boundaries
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause (identical result counts for different areas)
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 2.2, 2.3, 2.4_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Fast Path and Error Handling
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for "All Areas" selections and error conditions
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Property-based testing generates many test cases for stronger guarantees
  - Test that "All Areas" selection continues to return fast sample data (500 records)
  - Test that error handling continues to fall back gracefully without crashing
  - Test that GeoJSON geometry data caching continues to work for performance
  - Test that point-in-polygon calculations continue to use optimized algorithms
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for accurate geographic filtering bug

  - [x] 3.1 Implement the fix
    - Add geometry data validation to verify GeoJSON files exist and are readable
    - Improve area name matching between frontend and GeoJSON data (case-insensitive, special characters)
    - Distinguish between intentional sampling ("All Areas") and filtering failures
    - Enhance load_geojson_polygons function with validation and error handling
    - Improve point-in-polygon calculation robustness with coordinate system validation
    - Return empty results (not sample data) when geometry is missing for specific areas
    - Add logging when geometry data is missing or invalid
    - _Bug_Condition: isBugCondition(input) where input.admin_area NOT IN ['all', null, ''] AND input.admin_level IN ['province', 'municipality', 'region'] AND resultCount matches "All Areas"_
    - _Expected_Behavior: expectedBehavior(result) - accurate point-in-polygon filtering returning only data points within selected geographic boundaries_
    - _Preservation: Fast sampling for "All Areas", graceful error fallbacks, geometry caching, optimized calculations_
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Accurate Geographic Filtering
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: Expected Behavior Properties from design - accurate geographic filtering_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Fast Path and Error Handling
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.