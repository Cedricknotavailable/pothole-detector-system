# Bugfix Requirements Document

## Introduction

Users are experiencing login failures when entering correct credentials with different casing than their registered username. The authentication system currently treats username lookups as case-sensitive while email lookups are case-insensitive, creating an inconsistent and frustrating user experience. This bug affects users who may not remember the exact casing they used during registration.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user attempts to login with a username that matches their registered username but with different casing (e.g., registered as "JohnDoe", login attempt with "johndoe") THEN the system fails to find the user and returns "Username or email not found" error

1.2 WHEN a user attempts to login with an email address THEN the system performs case-insensitive matching using func.lower()

1.3 WHEN a user attempts to login with a username THEN the system performs case-sensitive matching using filter_by(), creating inconsistent behavior between username and email authentication

### Expected Behavior (Correct)

2.1 WHEN a user attempts to login with a username that matches their registered username regardless of casing THEN the system SHALL successfully find the user account using case-insensitive matching

2.2 WHEN a user attempts to login with a username THEN the system SHALL use func.lower() for case-insensitive comparison, consistent with email authentication behavior

2.3 WHEN a user attempts to login with either username or email THEN the system SHALL provide consistent case-insensitive matching for both authentication methods

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user attempts to login with an email address THEN the system SHALL CONTINUE TO perform case-insensitive matching as it currently does

3.2 WHEN a user provides incorrect credentials (wrong password, non-existent username/email) THEN the system SHALL CONTINUE TO return appropriate error messages

3.3 WHEN a user's account is locked or suspended THEN the system SHALL CONTINUE TO enforce account status restrictions and display appropriate messages

3.4 WHEN a user provides empty username/email or password fields THEN the system SHALL CONTINUE TO validate and return field-specific error messages

3.5 WHEN a user successfully authenticates with valid credentials THEN the system SHALL CONTINUE TO proceed with the login flow as expected
