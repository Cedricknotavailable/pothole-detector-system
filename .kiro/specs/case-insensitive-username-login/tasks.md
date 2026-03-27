# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Case-Insensitive Username Authentication
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: For deterministic bugs, scope the property to the concrete failing case(s) to ensure reproducibility
  - Test that username lookups with different casing fail on unfixed code (e.g., register "TestUser", login with "testuser" fails)
  - Test that for any username with case variations, the system fails to find the user account when using different casing
  - The test assertions should match the Expected Behavior Properties from design: successful authentication regardless of username casing
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause (e.g., "Login with 'testuser' when registered as 'TestUser' returns 'Username or email not found'")
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.3, 2.1, 2.2_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing Authentication Behavior
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Property-based testing generates many test cases for stronger guarantees
  - Test email-based login with case variations (should pass on unfixed code - already case-insensitive)
  - Test incorrect password scenarios (should fail with "Incorrect password" on unfixed code)
  - Test non-existent username/email (should fail with "Username or email not found" on unfixed code)
  - Test locked account handling (should fail with lock message on unfixed code)
  - Test suspended account handling (should fail with suspension message on unfixed code)
  - Test empty field validation (should fail with field-specific errors on unfixed code)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 3. Fix for case-insensitive username login

  - [x] 3.1 Implement the fix
    - Change line 979 in app.py from `User.query.filter_by(username=identifier).first()` to `User.query.filter(func.lower(User.username) == identifier.lower()).first()`
    - Verify `func` is imported from SQLAlchemy (should already be imported for email lookup)
    - No other changes required - fix is minimal and surgical
    - _Bug_Condition: isBugCondition(input) where NOT isEmail(input.identifier) AND EXISTS user WHERE func.lower(user.username) == input.identifier.lower() AND NOT EXISTS user WHERE user.username == input.identifier_
    - _Expected_Behavior: For any login attempt where identifier is a username matching a registered username case-insensitively, the system successfully finds the user account and proceeds with password validation_
    - _Preservation: Email authentication continues case-insensitive matching, password validation unchanged, account status checks unchanged, error messages unchanged, empty field validation unchanged, session management unchanged_
    - _Requirements: 1.1, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Case-Insensitive Username Authentication
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Authentication Behavior
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
