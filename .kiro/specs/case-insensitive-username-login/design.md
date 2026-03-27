# Case-Insensitive Username Login Bugfix Design

## Overview

This bugfix addresses an inconsistency in the login authentication system where username lookups are case-sensitive while email lookups are case-insensitive. Users who register with a specific username casing (e.g., "JohnDoe") cannot login if they enter a different casing (e.g., "johndoe"), even though the credentials are correct. The fix will make username lookups case-insensitive by using `func.lower()` for comparison, matching the existing behavior for email authentication.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when a user attempts to login with a username that matches their registered username but with different casing
- **Property (P)**: The desired behavior when the bug condition occurs - the system should successfully authenticate the user regardless of username casing
- **Preservation**: Existing authentication behaviors (email case-insensitivity, password validation, account status checks, error handling) that must remain unchanged by the fix
- **login()**: The Flask route function in `app.py` (lines 954-1020) that handles user authentication
- **identifier**: The user input that can be either a username or email address
- **func.lower()**: SQLAlchemy function used for case-insensitive database comparisons

## Bug Details

### Bug Condition

The bug manifests when a user attempts to login with a username that matches their registered username but uses different casing. The `login()` function uses `filter_by(username=identifier)` for username lookups, which performs case-sensitive matching, while email lookups use `func.lower(User.email) == identifier.lower()` for case-insensitive matching.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type LoginAttempt with fields {identifier: string, password: string}
  OUTPUT: boolean
  
  RETURN NOT isEmail(input.identifier)
         AND EXISTS user IN database WHERE func.lower(user.username) == input.identifier.lower()
         AND NOT EXISTS user IN database WHERE user.username == input.identifier
         AND user.password_hash matches input.password
END FUNCTION
```

### Examples

- User registers with username "JohnDoe", attempts to login with "johndoe" → Login fails with "Username or email not found" (should succeed)
- User registers with username "AdminUser", attempts to login with "adminuser" → Login fails with "Username or email not found" (should succeed)
- User registers with username "TestAccount", attempts to login with "TESTACCOUNT" → Login fails with "Username or email not found" (should succeed)
- User registers with email "user@example.com", attempts to login with "USER@EXAMPLE.COM" → Login succeeds (already works correctly)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Email authentication must continue to use case-insensitive matching with `func.lower()`
- Password validation must continue to work exactly as before
- Account status checks (locked, suspended) must continue to enforce restrictions
- Error messages for incorrect credentials must remain unchanged
- Empty field validation must continue to work as before
- Session management and login flow after successful authentication must remain unchanged

**Scope:**
All inputs that do NOT involve username-based authentication with different casing should be completely unaffected by this fix. This includes:
- Email-based login attempts (already case-insensitive)
- Login attempts with incorrect passwords
- Login attempts with non-existent usernames or emails
- Login attempts with locked or suspended accounts
- Login attempts with empty fields

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is clear:

1. **Inconsistent Query Methods**: The code uses two different query approaches:
   - Email lookup: `User.query.filter(func.lower(User.email) == identifier.lower()).first()` (case-insensitive)
   - Username lookup: `User.query.filter_by(username=identifier).first()` (case-sensitive)

2. **Historical Implementation**: The email lookup was likely implemented with case-insensitivity from the start (common practice for emails), but username lookup was implemented with the simpler `filter_by()` method without considering case variations

3. **SQLAlchemy filter_by() Behavior**: The `filter_by()` method performs exact matching, which is case-sensitive for string columns in most databases

4. **No Normalization at Registration**: Usernames are stored exactly as entered during registration without case normalization, so "JohnDoe" and "johndoe" are treated as different values during lookup

## Correctness Properties

Property 1: Bug Condition - Case-Insensitive Username Authentication

_For any_ login attempt where the identifier is a username (not an email) and matches a registered username when compared case-insensitively, the fixed login function SHALL successfully find the user account and proceed with password validation, regardless of the casing used in the login attempt.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation - Existing Authentication Behavior

_For any_ login attempt that does NOT involve username casing variations (email logins, incorrect credentials, account status restrictions, empty fields), the fixed login function SHALL produce exactly the same behavior as the original function, preserving all existing authentication logic, error messages, and security checks.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `app.py`

**Function**: `login()` (lines 954-1020)

**Specific Changes**:
1. **Replace Case-Sensitive Username Lookup**: Change line 979 from:
   ```python
   user = User.query.filter_by(username=identifier).first()
   ```
   To use case-insensitive matching:
   ```python
   user = User.query.filter(func.lower(User.username) == identifier.lower()).first()
   ```

2. **Import Verification**: Ensure `func` is imported from SQLAlchemy (should already be imported for email lookup):
   ```python
   from sqlalchemy import func
   ```

3. **No Other Changes Required**: The fix is minimal and surgical - only the username lookup query needs modification. All other logic (password validation, account status checks, error handling) remains unchanged.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that username lookups are case-sensitive while email lookups are case-insensitive.

**Test Plan**: Create test users with specific username casing, then attempt to login with different casing variations. Run these tests on the UNFIXED code to observe failures and confirm the root cause.

**Test Cases**:
1. **Username Case Variation Test**: Register user with "TestUser", attempt login with "testuser" (will fail on unfixed code)
2. **Username Uppercase Test**: Register user with "AdminAccount", attempt login with "ADMINACCOUNT" (will fail on unfixed code)
3. **Username Mixed Case Test**: Register user with "johnDOE", attempt login with "JohnDoe" (will fail on unfixed code)
4. **Email Case Variation Test**: Register user with email "test@example.com", attempt login with "TEST@EXAMPLE.COM" (should succeed on unfixed code, confirming email is already case-insensitive)

**Expected Counterexamples**:
- Username lookups with different casing return None (user not found)
- Error message: "Username or email not found"
- Root cause confirmed: `filter_by()` performs case-sensitive matching

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := login_fixed(input)
  ASSERT result successfully finds user account
  ASSERT password validation proceeds normally
  ASSERT login succeeds if password is correct
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT login_original(input) = login_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for email logins, incorrect credentials, and account status checks, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Email Login Preservation**: Verify email-based logins continue to work with case-insensitive matching
2. **Incorrect Password Preservation**: Verify wrong password errors remain unchanged
3. **Non-Existent User Preservation**: Verify "Username or email not found" errors for truly non-existent accounts
4. **Account Status Preservation**: Verify locked and suspended account handling remains unchanged
5. **Empty Field Preservation**: Verify empty field validation continues to work

### Unit Tests

- Test username login with exact casing match (should work before and after fix)
- Test username login with different casing (should fail before fix, succeed after fix)
- Test email login with different casing (should work before and after fix)
- Test incorrect password with username (should fail before and after fix)
- Test non-existent username (should fail before and after fix)
- Test locked account with username (should fail before and after fix)
- Test suspended account with username (should fail before and after fix)
- Test empty username field (should fail before and after fix)
- Test empty password field (should fail before and after fix)

### Property-Based Tests

- Generate random username casing variations and verify all succeed with correct password after fix
- Generate random email casing variations and verify all succeed with correct password (before and after fix)
- Generate random incorrect passwords and verify all fail with appropriate error (before and after fix)
- Generate random account statuses and verify status checks work correctly (before and after fix)

### Integration Tests

- Test full login flow with username case variations across different browsers
- Test session creation after successful login with case-insensitive username
- Test that user object returned is correct regardless of username casing used
- Test that subsequent authenticated requests work correctly after case-insensitive login
