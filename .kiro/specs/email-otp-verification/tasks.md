# Implementation Plan: Email OTP Verification

## Overview

This implementation plan breaks down the email OTP verification feature into incremental coding tasks. The feature adds secure email verification to registration and password reset flows using 6-digit OTP codes sent via EmailJS. Implementation follows the existing Flask/SQLAlchemy patterns in app.py and integrates with the current User model and authentication system.

The plan progresses from database setup through backend API implementation to frontend integration, with property-based tests and unit tests included as optional sub-tasks for faster MVP delivery.

## Tasks

- [x] 1. Set up OTP database model and helper functions
  - [x] 1.1 Create OTP model class in app.py
    - Add OTP model with fields: id, email, otp_hash, purpose, created_at, expires_at, attempts, verified
    - Add indexes on email, (email, purpose, verified), and expires_at
    - Implement is_expired(), is_valid(), increment_attempts(), and mark_verified() methods
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 6.4_
  
  - [ ]* 1.2 Write property test for OTP expiration calculation
    - **Property 3: OTP Expiration Calculation**
    - **Validates: Requirements 2.2**
  
  - [x] 1.3 Implement generate_otp() helper function
    - Use secrets.randbelow(1000000) for cryptographically secure generation
    - Return 6-digit string with leading zeros preserved using f"{code:06d}"
    - _Requirements: 1.1, 1.2_
  
  - [ ]* 1.4 Write property test for OTP format and randomness
    - **Property 1: OTP Format and Randomness**
    - **Property 30: No Sequential Patterns**
    - **Validates: Requirements 1.1, 1.2, 1.3_
  
  - [x] 1.5 Implement cleanup_expired_otps() helper function
    - Delete OTP records where created_at < (current_time - 3600)
    - Return count of deleted records
    - _Requirements: 9.4_
  
  - [ ]* 1.6 Write property test for OTP cleanup
    - **Property 27: OTP Cleanup**
    - **Validates: Requirements 9.4**

- [x] 2. Modify registration endpoint for OTP flow
  - [x] 2.1 Update /register route to generate OTP instead of creating user
    - Keep existing validation logic for username, email, password
    - Generate OTP using generate_otp() after validation passes
    - Hash OTP using generate_password_hash() before storing
    - Create OTP record with purpose='registration', expires_at=now+600
    - Store registration data in session['pending_registration']
    - Return JSON response with success=True and otp_code for client
    - _Requirements: 4.1, 4.6, 11.2_
  
  - [ ]* 2.2 Write property test for registration session storage
    - **Property 20: Registration Session Storage**
    - **Validates: Requirements 4.6, 11.2**
  
  - [ ]* 2.3 Write property test for OTP storage completeness
    - **Property 2: OTP Storage Completeness**
    - **Validates: Requirements 2.1, 2.5**
  
  - [ ]* 2.4 Write unit tests for registration validation errors
    - Test missing username, email, password return appropriate errors
    - Test duplicate username/email return field-specific errors
    - Test invalid password format returns validation errors
    - _Requirements: 4.1_

- [ ] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement OTP verification endpoint
  - [x] 4.1 Create /verify-otp route
    - Accept otp_code from POST request
    - Validate format (6 digits, numeric)
    - Retrieve email and purpose from session
    - Look up active OTP record (email, purpose, verified=False)
    - Check OTP validity using is_valid() method
    - Verify OTP hash using check_password_hash()
    - Increment attempts on failure, mark verified on success
    - Return JSON with success, message, attempts_remaining, next_step
    - _Requirements: 4.3, 4.5, 5.4, 5.7, 6.1, 6.2, 6.3, 6.4, 9.2, 12.2, 12.4_
  
  - [x] 4.2 Add user creation logic for registration purpose
    - When purpose='registration' and OTP valid, create User from session data
    - Use pending_registration data: username, email, password_hash
    - Clear session data after user creation
    - Return redirect URL to login page
    - _Requirements: 4.4, 11.4_
  
  - [x] 4.3 Add password reset authorization for password_reset purpose
    - When purpose='password_reset' and OTP valid, set session['otp_verified']=True
    - Return next_step='reset_password' to show password form
    - _Requirements: 5.5_
  
  - [ ]* 4.4 Write property test for OTP verification logic
    - **Property 8: OTP Verification Logic**
    - **Validates: Requirements 4.3, 5.4, 9.2**
  
  - [ ]* 4.5 Write property test for attempt limiting
    - **Property 11: Attempt Limiting**
    - **Property 12: Attempt Counter Increment**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
  
  - [ ]* 4.6 Write property test for OTP invalidation after success
    - **Property 25: OTP Invalidation After Success**
    - **Validates: Requirements 2.4**
  
  - [ ]* 4.7 Write property test for expired OTP rejection
    - **Property 26: Expired OTP Rejection**
    - **Validates: Requirements 2.3**
  
  - [ ]* 4.8 Write unit tests for verification error cases
    - Test invalid format returns 400
    - Test missing session returns 400
    - Test no active OTP returns 404
    - Test wrong code increments attempts
    - _Requirements: 4.5, 5.7_

- [x] 5. Implement OTP resend endpoint
  - [x] 5.1 Create /resend-otp route
    - Retrieve email and purpose from session
    - Check 30-second cooldown using session['last_otp_resend']
    - Check rate limit (3 per 15 minutes) using session rate tracking
    - Invalidate previous OTP records (set verified=True)
    - Generate new OTP and create new OTP record
    - Update rate limit counters in session
    - Return JSON with success, otp_code, message, cooldown_remaining
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4_
  
  - [ ]* 5.2 Write property test for rate limiting window
    - **Property 13: Rate Limiting Window**
    - **Property 14: Rate Limit Tracking**
    - **Property 15: Rate Limit Window Reset**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
  
  - [ ]* 5.3 Write property test for resend invalidation
    - **Property 16: Resend Invalidates Previous OTP**
    - **Validates: Requirements 8.2**
  
  - [ ]* 5.4 Write property test for resend cooldown
    - **Property 17: Resend Cooldown**
    - **Validates: Requirements 8.4**
  
  - [ ]* 5.5 Write unit tests for resend error cases
    - Test no active session returns 400
    - Test cooldown period returns 429
    - Test rate limit exceeded returns 429
    - _Requirements: 8.3, 8.4_

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Modify password recovery endpoint for OTP flow
  - [x] 7.1 Update /recover route to generate OTP
    - Keep existing identifier validation (username or email)
    - Look up user by identifier (case-insensitive for email)
    - Always return success message for security (timing attack prevention)
    - If user exists, generate OTP and store with purpose='password_reset'
    - Store user_id in session['reset_user_id']
    - Store email in session['otp_email'] and purpose in session['otp_purpose']
    - Return JSON with success=True and otp_code (or None if user not found)
    - _Requirements: 5.1, 5.2, 11.3_
  
  - [ ]* 7.2 Write property test for user lookup
    - **Property 24: User Lookup by Username or Email**
    - **Validates: Requirements 5.1**
  
  - [ ]* 7.3 Write property test for password reset session storage
    - **Property 21: Password Reset Session Storage**
    - **Validates: Requirements 11.3**
  
  - [ ]* 7.4 Write unit tests for recovery validation
    - Test empty identifier returns error
    - Test invalid email format returns error
    - Test non-existent user returns success (security)
    - _Requirements: 5.1_

- [x] 8. Implement password reset completion endpoint
  - [x] 8.1 Create /reset-password route
    - Check session['otp_verified'] is True, return 403 if not
    - Retrieve user_id from session['reset_user_id']
    - Validate new_password using same rules as registration
    - Update user.password_hash using set_password() or generate_password_hash()
    - Clear all OTP session data
    - Return JSON with success, message, redirect to login
    - _Requirements: 5.6, 11.4_
  
  - [ ]* 8.2 Write property test for password update
    - **Property 23: Password Update After Valid Reset**
    - **Validates: Requirements 5.6**
  
  - [ ]* 8.3 Write property test for session cleanup
    - **Property 22: Session Cleanup After Completion**
    - **Validates: Requirements 11.4**
  
  - [ ]* 8.4 Write unit tests for password reset errors
    - Test missing otp_verified returns 403
    - Test missing reset_user_id returns 400
    - Test invalid password format returns 400
    - _Requirements: 5.6_

- [x] 9. Add OTP hashing security measures
  - [x] 9.1 Verify OTP codes are hashed before storage
    - Review all OTP creation code to ensure generate_password_hash() is used
    - Ensure no plaintext OTP codes are logged or stored
    - _Requirements: 9.1, 9.3_
  
  - [ ]* 9.2 Write property test for OTP hashing
    - **Property 18: OTP Hashing**
    - **Property 19: OTP Hash Round Trip**
    - **Validates: Requirements 9.1, 9.2, 9.3**

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Update register.html for OTP flow
  - [x] 11.1 Add EmailJS SDK script tags to register.html
    - Add EmailJS CDN script: https://cdn.jsdelivr.net/npm/@emailjs/browser@3/dist/email.min.js
    - Initialize emailjs with public key: dXcaIv5LGMTpybpw2
    - _Requirements: 3.4_
  
  - [x] 11.2 Add OTP input form section to register.html
    - Add hidden div with id="otpSection" containing OTP input field
    - Add 6-digit numeric input with maxlength=6, pattern="[0-9]{6}"
    - Add "Verify Code" button (initially disabled)
    - Add "Resend code" button with cooldown timer
    - Add status message div for feedback
    - _Requirements: 4.2, 8.5, 12.1, 12.5_
  
  - [x] 11.3 Add JavaScript for registration form submission
    - Prevent default form submission
    - Send POST to /register with FormData
    - On success with otp_code, send email via EmailJS
    - Use service_cs9uath, template_ai1brni with to_email, otp_code, expiration_minutes=10
    - Show OTP input section after email sent
    - Display error messages for validation failures
    - _Requirements: 3.1, 3.3, 3.5, 4.2, 12.1_
  
  - [x] 11.4 Add JavaScript for OTP verification
    - Enable verify button when 6 digits entered
    - Send POST to /verify-otp with otp_code
    - On success, show success message and redirect to login
    - On failure, show error message with attempts remaining
    - Update attempts remaining display after each failure
    - _Requirements: 4.3, 4.5, 12.2, 12.3, 12.4_
  
  - [x] 11.5 Add JavaScript for OTP resend
    - Send POST to /resend-otp on button click
    - On success with otp_code, send new email via EmailJS
    - Start 30-second cooldown timer, disable button
    - Update button text with countdown
    - Show success/error messages
    - _Requirements: 8.1, 8.4, 8.5_

- [x] 12. Update recover.html for OTP flow
  - [x] 12.1 Add EmailJS SDK script tags to recover.html
    - Add EmailJS CDN script and initialization (same as register.html)
    - _Requirements: 3.4_
  
  - [x] 12.2 Update existing OTP section in recover.html
    - Modify show_otp conditional to display OTP input
    - Ensure 6-digit numeric input exists with proper attributes
    - Update verify button to call /verify-otp endpoint
    - Update resend button to call /resend-otp endpoint
    - _Requirements: 5.3, 8.5_
  
  - [x] 12.3 Add JavaScript for password recovery submission
    - Prevent default form submission
    - Send POST to /recover with identifier
    - On success with otp_code, send email via EmailJS
    - Show OTP input section
    - Always show success message (security)
    - _Requirements: 5.2, 12.1_
  
  - [x] 12.4 Add JavaScript for password reset OTP verification
    - Send POST to /verify-otp with otp_code
    - On success with next_step='reset_password', show password reset form
    - On failure, show error message with attempts remaining
    - _Requirements: 5.4, 5.5, 12.2, 12.4_
  
  - [x] 12.5 Add password reset form section to recover.html
    - Add hidden div with id="resetPasswordSection"
    - Add new_password input field with validation
    - Add "Reset Password" button
    - Show after successful OTP verification
    - _Requirements: 5.5, 5.6_
  
  - [x] 12.6 Add JavaScript for password reset submission
    - Send POST to /reset-password with new_password
    - Validate password meets requirements client-side
    - On success, show success message and redirect to login
    - On failure, show validation errors
    - _Requirements: 5.6, 12.3_

- [ ] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Add database migration and cleanup
  - [x] 14.1 Create database migration for OTP table
    - Add code to create OTP table with all columns and indexes
    - Run migration to update database schema
    - Verify table created successfully
    - _Requirements: 2.1_
  
  - [x] 14.2 Add cleanup hook for expired OTPs
    - Add before_request hook to call cleanup_expired_otps() periodically
    - Implement simple throttling (e.g., only run every 100 requests)
    - Log cleanup results for monitoring
    - _Requirements: 9.4_

- [ ] 15. Integration testing and final validation
  - [ ]* 15.1 Write integration test for registration flow
    - Test complete flow: submit registration → receive OTP → verify → user created
    - Verify session data managed correctly
    - Verify user can log in after registration
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [ ]* 15.2 Write integration test for password reset flow
    - Test complete flow: submit recovery → receive OTP → verify → reset password
    - Verify session data managed correctly
    - Verify user can log in with new password
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  
  - [ ]* 15.3 Write integration test for error scenarios
    - Test expired OTP handling
    - Test rate limiting enforcement
    - Test attempt limiting enforcement
    - Test session timeout handling
    - _Requirements: 2.3, 6.1, 6.2, 7.1, 7.2, 11.5_

- [ ] 16. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows
- Checkpoints ensure incremental validation and provide opportunities for user feedback
- EmailJS integration is client-side only, no server-side SMTP configuration needed
- OTP codes are always hashed before storage, never stored in plaintext
- Rate limiting and cooldowns use session-based tracking for stateless implementation
