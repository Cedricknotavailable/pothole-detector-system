# Implementation Plan: UI/UX Improvements

## Overview

This implementation plan covers six UI/UX improvements to the Surveyor.AI application:
1. Community False Report Flagging - Enable users to flag inaccurate reports
2. Configurable False Report Threshold - Admin control over auto-flagging sensitivity
3. Logout Confirmation Dialog - Prevent accidental session termination
4. Audit Log Relocation - Move audit logs to analytics page
5. Specific Login/Registration Error Messages - Field-level error feedback
6. Rename Reset to Clear Filters - Improve button clarity
7. Required Photo Attachment - Enforce visual evidence for reports

The implementation follows the existing Flask/SQLAlchemy architecture with progressive enhancement through JavaScript.

## Tasks

- [x] 1. Set up database schema for community flagging system
  - Create ReportFlag model with SQLAlchemy
  - Add migration script to create report_flag table with indexes
  - Add unique constraint on (report_id, user_id)
  - Add community_false_report_threshold setting with default value of 3
  - Test database migrations on development database
  - _Requirements: 1.1, 1.2, 1.6, 2.1_

- [x] 2. Implement community false report flagging backend
  - [x] 2.1 Create flag report API endpoint
    - Implement POST /api/reports/<report_id>/flag route
    - Add authentication check using @login_required_view decorator
    - Check for existing flag from same user
    - Create ReportFlag record with user_id and report_id
    - Count total flags on report
    - Retrieve threshold from Settings table
    - Implement auto-flagging logic when threshold reached
    - Increment author's false_reports_count when auto-flagged
    - Create notification for report author
    - Write audit log entry for flag action
    - Return JSON response with flag_count and auto_flagged status
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8_

  - [ ]* 2.2 Write property test for flag record creation
    - **Property 1: Flag Record Creation**
    - **Validates: Requirements 1.2**

  - [ ]* 2.3 Write property test for auto-flagging threshold enforcement
    - **Property 2: Auto-flagging Threshold Enforcement**
    - **Validates: Requirements 1.3**

  - [ ]* 2.4 Write property test for author false report count increment
    - **Property 3: Author False Report Count Increment**
    - **Validates: Requirements 1.4**

  - [ ]* 2.5 Write unit tests for flag API endpoint
    - Test successful flag creation
    - Test duplicate flag prevention (IntegrityError)
    - Test auto-flagging at threshold
    - Test notification creation
    - Test audit log entry creation
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 1.8_

- [x] 3. Implement community flagging frontend
  - [x] 3.1 Add flag button to map report popups
    - Add flag button HTML to map.html report popup template
    - Style flag button with red color scheme
    - Position button alongside existing reaction buttons
    - _Requirements: 1.1_

  - [x] 3.2 Implement flag button JavaScript handler
    - Create flagReport(reportId) function
    - Add confirmation dialog before flagging
    - Make POST request to /api/reports/<id>/flag
    - Handle success response (update button state, show flag count)
    - Handle auto-flag response (show alert, reload map)
    - Handle error responses (already flagged, network error)
    - Disable button after successful flag
    - _Requirements: 1.1, 1.2, 1.6_

  - [x] 3.3 Update map query to filter false reports
    - Modify map data API endpoint to exclude is_false_report=True
    - Test that flagged reports don't appear on map
    - _Requirements: 1.7_

  - [ ]* 3.4 Write property test for false report map filtering
    - **Property 6: False Report Map Filtering**
    - **Validates: Requirements 1.7**

- [x] 4. Checkpoint - Test community flagging system
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement configurable false report threshold
  - [x] 5.1 Add threshold setting to settings page
    - Add HTML form field in General Configuration section
    - Set input type to number with min=1, max=10
    - Display current value from Settings table
    - Add descriptive label and help text
    - _Requirements: 2.2_

  - [x] 5.2 Implement threshold update backend
    - Update settings_page route to handle community_false_report_threshold
    - Validate threshold is positive integer >= 1
    - Save to Settings table
    - Write audit log entry for threshold change
    - Return success/error response
    - _Requirements: 2.3, 2.4, 2.5_

  - [ ]* 5.3 Write property test for threshold validation
    - **Property 8: Threshold Validation**
    - **Validates: Requirements 2.3**

  - [ ]* 5.4 Write property test for threshold update persistence
    - **Property 9: Threshold Update Persistence**
    - **Validates: Requirements 2.4**

  - [ ]* 5.5 Write unit tests for threshold configuration
    - Test valid threshold values (1-10)
    - Test invalid threshold values (0, negative)
    - Test settings persistence
    - Test audit log creation
    - _Requirements: 2.3, 2.4_

- [x] 6. Implement logout confirmation dialog
  - [x] 6.1 Create logout modal HTML component
    - Add modal HTML structure to base template or each page
    - Include modal overlay, content, header, body, footer
    - Add "Cancel" and "Log Out" buttons
    - Style modal with CSS (centered, backdrop blur, animation)
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 6.2 Implement logout confirmation JavaScript
    - Intercept all logout link clicks with event listener
    - Show modal on logout click (prevent default navigation)
    - Implement closeLogoutModal() function
    - Implement confirmLogout() function (navigate to /logout)
    - Add Escape key handler to close modal
    - Add overlay click handler to close modal
    - _Requirements: 3.1, 3.4, 3.5_

  - [x] 6.3 Apply logout confirmation to all pages
    - Add modal HTML to admin dashboard pages
    - Add modal HTML to user dashboard pages
    - Test on index, map, users, settings, analytics, reports, my-reports
    - _Requirements: 3.6_

  - [ ]* 6.4 Write unit tests for logout confirmation
    - Test modal display on logout click
    - Test cancel button behavior
    - Test confirm button behavior
    - Test escape key handler
    - _Requirements: 3.1, 3.4, 3.5_

- [x] 7. Checkpoint - Test logout confirmation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Relocate audit log to analytics page
  - [x] 8.1 Remove audit log from settings page
    - Remove "Activity & Audit Log" accordion section from settings.html
    - Remove audit log JavaScript functions from settings.html
    - Remove audit log CSS specific to settings page
    - _Requirements: 4.1_

  - [x] 8.2 Add audit log to analytics page
    - Add audit log HTML section to analytics.html after charts
    - Include filters (action type, actor, start date, end date)
    - Include audit log table with columns (timestamp, actor, action, resource, detail, IP)
    - Include pagination controls
    - Add "Apply" and "Export" buttons
    - _Requirements: 4.2, 4.3_

  - [x] 8.3 Migrate audit log JavaScript to analytics page
    - Copy loadAuditLog(page) function to analytics.html
    - Copy renderAuditPagination() function
    - Copy exportAuditLog() function
    - Initialize audit log on page load (after charts)
    - Test all filters and pagination
    - _Requirements: 4.3, 4.6_

  - [x] 8.4 Add audit log CSS to analytics.css
    - Add .audit-filters styling
    - Add .audit-pagination styling
    - Add .audit-badge styling for action categories
    - Add .audit-detail-cell styling
    - Ensure responsive layout
    - _Requirements: 4.4, 4.5_

  - [ ]* 8.5 Write property test for audit log API functionality
    - **Property 10: Audit Log API Functionality**
    - **Validates: Requirements 4.3**

  - [ ]* 8.6 Write unit tests for audit log relocation
    - Test audit log API endpoint with filters
    - Test pagination
    - Test export functionality
    - _Requirements: 4.3_

- [x] 9. Implement specific login and registration error messages
  - [x] 9.1 Update login route with field-specific errors
    - Change error handling to use field_errors dictionary
    - Return "Username or email not found" for missing user
    - Return "Incorrect password" for wrong password
    - Return field-specific errors for empty fields
    - Pass field_errors and values to template
    - _Requirements: 5.1, 5.2_

  - [x] 9.2 Update login template with error display
    - Add .input-error class to inputs with errors
    - Display field errors below each input field
    - Add .field-error and .error-message styling
    - Preserve input values on error
    - _Requirements: 5.1, 5.2, 5.8_

  - [x] 9.3 Update registration route with field-specific errors
    - Validate username (required, length, uniqueness)
    - Validate email (required, format, uniqueness)
    - Validate password (required, length, uppercase, lowercase, digit)
    - Validate confirm_password (matches password)
    - Return field_errors dictionary with specific messages
    - Pass field_errors and values to template
    - _Requirements: 5.3, 5.4, 5.5, 5.6_

  - [x] 9.4 Update registration template with error display
    - Add .input-error class to inputs with errors
    - Display field errors below each input field
    - Show all password requirement errors
    - Preserve input values on error (except passwords)
    - _Requirements: 5.3, 5.4, 5.5, 5.6, 5.8_

  - [x] 9.5 Implement client-side error clearing
    - Add input event listeners to all form fields
    - Remove .input-error class on input
    - Remove .field-error div on input
    - Apply to both login and registration forms
    - _Requirements: 5.7_

  - [ ]* 9.6 Write property test for email format validation
    - **Property 11: Email Format Validation**
    - **Validates: Requirements 5.5**

  - [ ]* 9.7 Write property test for password requirement validation
    - **Property 12: Password Requirement Validation**
    - **Validates: Requirements 5.6**

  - [ ]* 9.8 Write property test for error clearing on input
    - **Property 13: Error Clearing on Input**
    - **Validates: Requirements 5.7**

  - [ ]* 9.9 Write unit tests for login error messages
    - Test username not found error
    - Test incorrect password error
    - Test empty field errors
    - Test error display in template
    - _Requirements: 5.1, 5.2_

  - [ ]* 9.10 Write unit tests for registration error messages
    - Test duplicate username error
    - Test duplicate email error
    - Test invalid email format error
    - Test password requirement errors
    - Test confirm password mismatch error
    - _Requirements: 5.3, 5.4, 5.5, 5.6_

- [x] 10. Checkpoint - Test error message improvements
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Rename Reset to Clear Filters
  - [x] 11.1 Update filter button text on users page
    - Change button text from "Reset" to "Clear Filters"
    - Verify button functionality unchanged
    - Test responsive layout
    - _Requirements: 6.1, 6.5_

  - [x] 11.2 Update filter button text on defects page
    - Change button text from "Reset" to "Clear Filters"
    - Verify button functionality unchanged
    - Test responsive layout
    - _Requirements: 6.2, 6.5_

  - [x] 11.3 Update filter button text on my reports page
    - Change button text from "Reset" to "Clear Filters"
    - Verify button functionality unchanged
    - Test responsive layout
    - _Requirements: 6.3, 6.5_

  - [x] 11.4 Update filter button text on map page
    - Change button text from "Reset" to "Clear Filters"
    - Verify button functionality unchanged
    - Test responsive layout
    - _Requirements: 6.4, 6.5_

  - [ ]* 11.5 Write unit tests for filter button text
    - Test button text on all pages
    - Test button alignment and visibility
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6_

- [x] 12. Implement required photo attachment
  - [x] 12.1 Update report form HTML
    - Add required attribute to photo input
    - Change label from "Evidence Photo (Optional)" to "Evidence Photo"
    - Add photo error message div
    - Update upload placeholder text to indicate required
    - _Requirements: 7.1, 7.6_

  - [x] 12.2 Implement client-side photo validation
    - Check for photo file presence on form submit
    - Validate file type (jpg, jpeg, png)
    - Validate file size (max 5MB)
    - Display error message if validation fails
    - Prevent form submission if photo missing
    - Clear error when photo selected
    - _Requirements: 7.2, 7.3, 7.5, 7.6_

  - [x] 12.3 Implement server-side photo validation
    - Check for photo file in request.files
    - Return error if photo missing
    - Validate file extension
    - Validate file size
    - Return specific error messages
    - Prevent report creation if photo missing
    - _Requirements: 7.4, 7.5_

  - [ ]* 12.4 Write property test for photo submission validation
    - **Property 14: Photo Submission Validation**
    - **Validates: Requirements 7.2**

  - [ ]* 12.5 Write property test for server-side photo validation
    - **Property 15: Server-side Photo Validation**
    - **Validates: Requirements 7.4**

  - [ ]* 12.6 Write property test for file type validation
    - **Property 16: File Type Validation**
    - **Validates: Requirements 7.5**

  - [ ]* 12.7 Write unit tests for photo requirement
    - Test submission without photo (client-side)
    - Test submission without photo (server-side)
    - Test invalid file type
    - Test file size validation
    - Test successful submission with photo
    - _Requirements: 7.2, 7.3, 7.4, 7.5_

- [x] 13. Final checkpoint - Integration testing
  - Test all six improvements together
  - Verify no regressions in existing functionality
  - Test cross-browser compatibility
  - Test mobile responsiveness
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- All database changes include migration scripts for safe deployment
- Client-side and server-side validations are implemented for security
- Existing functionality is preserved throughout implementation
