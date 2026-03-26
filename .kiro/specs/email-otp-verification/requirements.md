# Requirements Document

## Introduction

This document specifies requirements for an OTP (One-Time Password) email verification system that secures account registration and password reset flows. The system generates secure 6-digit codes, sends them via EmailJS, and verifies them before allowing sensitive operations to complete.

## Glossary

- **OTP_System**: The one-time password verification subsystem
- **OTP_Generator**: Component responsible for generating secure random 6-digit codes
- **OTP_Store**: Temporary storage mechanism for OTP codes with expiration metadata
- **Email_Service**: EmailJS integration for sending OTP codes to user email addresses
- **Registration_Flow**: Account creation process requiring email verification before account activation
- **Password_Reset_Flow**: Password recovery process requiring identity verification before password change
- **Rate_Limiter**: Component that prevents abuse by limiting request frequency
- **Verification_Attempt**: A single attempt to verify an OTP code
- **User**: Person attempting to register or reset password

## Requirements

### Requirement 1: Generate Secure OTP Codes

**User Story:** As a system administrator, I want OTP codes to be cryptographically secure, so that attackers cannot predict or guess valid codes.

#### Acceptance Criteria

1. WHEN an OTP is requested, THE OTP_Generator SHALL generate a 6-digit numeric code using a cryptographically secure random number generator
2. THE OTP_Generator SHALL ensure each generated code is exactly 6 digits with leading zeros preserved
3. FOR ALL generated OTP codes, the code SHALL be unpredictable from previous codes (no sequential or pattern-based generation)

### Requirement 2: Store OTP Codes Temporarily

**User Story:** As a security engineer, I want OTP codes to expire after a time limit, so that old codes cannot be reused.

#### Acceptance Criteria

1. WHEN an OTP is generated, THE OTP_Store SHALL store the code with the associated email address and creation timestamp
2. THE OTP_Store SHALL set an expiration time of 10 minutes for each OTP code
3. WHEN an OTP verification is requested, THE OTP_Store SHALL reject codes that exceed the 10-minute expiration time
4. WHEN an OTP is successfully verified, THE OTP_Store SHALL invalidate the code to prevent reuse
5. THE OTP_Store SHALL associate each OTP with its purpose (registration or password reset)

### Requirement 3: Send OTP via Email

**User Story:** As a user, I want to receive OTP codes via email, so that I can verify my email address.

#### Acceptance Criteria

1. WHEN an OTP is generated for registration, THE Email_Service SHALL send the code to the provided email address using EmailJS service ID "service_cs9uath"
2. WHEN an OTP is generated for password reset, THE Email_Service SHALL send the code to the user's registered email address using EmailJS service ID "service_cs9uath"
3. THE Email_Service SHALL use template ID "template_ai1brni" for all OTP emails
4. THE Email_Service SHALL use public key "dXcaIv5LGMTpybpw2" for EmailJS authentication
5. THE Email_Service SHALL include the 6-digit OTP code and expiration time in the email content
6. IF email sending fails, THEN THE OTP_System SHALL return an error to the user without creating the OTP record

### Requirement 4: Verify OTP for Registration

**User Story:** As a new user, I want to verify my email before my account is created, so that only valid email addresses can register.

#### Acceptance Criteria

1. WHEN a user submits registration information, THE Registration_Flow SHALL generate and send an OTP before creating the user account
2. THE Registration_Flow SHALL display an OTP input form after the initial registration submission
3. WHEN a user submits an OTP code, THE Registration_Flow SHALL verify the code matches the stored OTP for that email address
4. IF the OTP is valid and not expired, THEN THE Registration_Flow SHALL create the user account with the originally submitted credentials
5. IF the OTP is invalid or expired, THEN THE Registration_Flow SHALL display an error message and allow retry
6. THE Registration_Flow SHALL store registration data temporarily until OTP verification completes

### Requirement 5: Verify OTP for Password Reset

**User Story:** As a user who forgot my password, I want to verify my identity with an OTP, so that I can securely reset my password.

#### Acceptance Criteria

1. WHEN a user requests password recovery, THE Password_Reset_Flow SHALL look up the user by username or email
2. IF the user exists, THEN THE Password_Reset_Flow SHALL generate and send an OTP to the user's registered email address
3. THE Password_Reset_Flow SHALL display an OTP input form after the recovery request
4. WHEN a user submits an OTP code, THE Password_Reset_Flow SHALL verify the code matches the stored OTP for that user
5. IF the OTP is valid and not expired, THEN THE Password_Reset_Flow SHALL display a password reset form
6. WHEN a new password is submitted with a valid OTP session, THE Password_Reset_Flow SHALL update the user's password
7. IF the OTP is invalid or expired, THEN THE Password_Reset_Flow SHALL display an error message and allow retry

### Requirement 6: Limit Verification Attempts

**User Story:** As a security engineer, I want to limit OTP verification attempts, so that brute force attacks are prevented.

#### Acceptance Criteria

1. THE OTP_System SHALL allow a maximum of 3 verification attempts per OTP code
2. WHEN 3 failed verification attempts occur, THE OTP_System SHALL invalidate the OTP code
3. WHEN an OTP is invalidated due to failed attempts, THE OTP_System SHALL require the user to request a new OTP
4. THE OTP_System SHALL track verification attempts per OTP code in the OTP_Store

### Requirement 7: Rate Limit OTP Generation

**User Story:** As a system administrator, I want to prevent users from requesting too many OTP codes, so that email service abuse is prevented.

#### Acceptance Criteria

1. THE Rate_Limiter SHALL allow a maximum of 3 OTP generation requests per email address within a 15-minute window
2. WHEN the rate limit is exceeded, THE Rate_Limiter SHALL reject the OTP generation request with an error message
3. THE Rate_Limiter SHALL track OTP generation requests per email address with timestamps
4. WHEN 15 minutes have elapsed since the first request, THE Rate_Limiter SHALL reset the counter for that email address

### Requirement 8: Provide OTP Resend Functionality

**User Story:** As a user, I want to request a new OTP if I didn't receive the first one, so that I can complete verification.

#### Acceptance Criteria

1. THE OTP_System SHALL provide a resend function that generates a new OTP code
2. WHEN a resend is requested, THE OTP_System SHALL invalidate any previous OTP for that email and purpose
3. WHEN a resend is requested, THE OTP_System SHALL enforce the rate limiting rules from Requirement 7
4. THE OTP_System SHALL implement a 30-second cooldown between resend requests for the same email address
5. WHEN the cooldown period is active, THE OTP_System SHALL disable the resend button and display remaining time

### Requirement 9: Secure OTP Storage

**User Story:** As a security engineer, I want OTP codes to be stored securely, so that they cannot be compromised if the database is accessed.

#### Acceptance Criteria

1. WHEN an OTP is stored, THE OTP_Store SHALL hash the OTP code using a secure one-way hash function
2. WHEN verifying an OTP, THE OTP_Store SHALL hash the submitted code and compare it to the stored hash
3. THE OTP_Store SHALL never store or log OTP codes in plaintext
4. THE OTP_Store SHALL automatically purge expired OTP records older than 1 hour

### Requirement 10: Handle Email Service Failures

**User Story:** As a user, I want clear feedback when email delivery fails, so that I know to try again or contact support.

#### Acceptance Criteria

1. IF EmailJS returns an error during OTP sending, THEN THE OTP_System SHALL display a user-friendly error message
2. WHEN email sending fails, THE OTP_System SHALL log the error details for administrator review
3. WHEN email sending fails, THE OTP_System SHALL not create or store the OTP code
4. THE OTP_System SHALL provide a retry mechanism for failed email deliveries within rate limit constraints

### Requirement 11: Maintain Session State During Verification

**User Story:** As a user, I want my registration or password reset data to be preserved during OTP verification, so that I don't have to re-enter information.

#### Acceptance Criteria

1. WHEN OTP verification is in progress, THE OTP_System SHALL maintain the user's session data
2. THE Registration_Flow SHALL store username, email, and password hash in session during OTP verification
3. THE Password_Reset_Flow SHALL store the user identifier in session during OTP verification
4. THE OTP_System SHALL clear session data after successful verification and account operation completion
5. THE OTP_System SHALL expire session data after 15 minutes of inactivity

### Requirement 12: Provide Clear User Feedback

**User Story:** As a user, I want clear messages about OTP status, so that I understand what to do next.

#### Acceptance Criteria

1. WHEN an OTP is sent, THE OTP_System SHALL display a message indicating the code was sent to the user's email
2. WHEN an OTP verification fails, THE OTP_System SHALL display the specific reason (invalid code, expired, or too many attempts)
3. WHEN an OTP verification succeeds, THE OTP_System SHALL display a success message before proceeding
4. THE OTP_System SHALL display the number of remaining verification attempts after each failed attempt
5. THE OTP_System SHALL display the OTP expiration time when showing the verification form

