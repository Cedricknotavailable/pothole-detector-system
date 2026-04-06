# Implementation Plan: False Report Warning Popup

## Overview

This implementation plan breaks down the false report warning popup feature into discrete coding tasks. The feature adds a modal warning dialog that appears before report submission, dynamically fetches the false report threshold from settings, and provides users with clear information about consequences of false reports.

## Tasks

- [x] 1. Create backend API endpoint for threshold retrieval
  - [x] 1.1 Implement `/api/false-report-threshold` GET endpoint in app.py
    - Add route with @login_required decorator
    - Query Settings table for 'false_report_threshold' key
    - Return JSON response with threshold value and success status
    - Handle missing setting with default value of 5
    - Include error handling for database exceptions
    - _Requirements: 2.1, 2.3_

  - [ ]* 1.2 Write property test for threshold API endpoint
    - **Property 3: Threshold API integration**
    - **Validates: Requirements 2.1**

  - [ ]* 1.3 Write unit tests for API endpoint
    - Test successful threshold retrieval
    - Test missing setting fallback to default
    - Test database error handling
    - Test authentication requirement
    - _Requirements: 2.1, 2.3_

- [x] 2. Create warning modal HTML template
  - [x] 2.1 Create false_report_warning_modal.html template
    - Design modal structure following existing logout modal pattern
    - Include warning icon and appropriate heading
    - Add dynamic threshold placeholder element
    - Include explanatory text about false report consequences
    - Add list of what constitutes false reports
    - Include Proceed and Cancel buttons
    - _Requirements: 1.1, 4.1, 4.2, 4.3, 5.1, 5.2, 5.4, 5.5_

  - [ ]* 2.2 Write property test for modal HTML structure
    - **Property 1: Warning popup appears before form submission**
    - **Validates: Requirements 1.1, 6.1, 6.2**

- [x] 3. Implement JavaScript integration with report form
  - [x] 3.1 Add form submission interceptor to reports.html
    - Intercept form submit event before processing
    - Prevent default submission when warning not shown
    - Store form reference for later submission
    - Integrate with existing form validation logic
    - _Requirements: 1.1, 6.1, 6.2, 6.3_

  - [x] 3.2 Implement warning popup display logic
    - Create showFalseReportWarning() function
    - Fetch threshold via AJAX call to API endpoint
    - Update modal content with dynamic threshold value
    - Display modal with proper z-index and positioning
    - Handle API errors with fallback to default threshold
    - _Requirements: 1.2, 2.1, 2.2, 2.4_

  - [x] 3.3 Implement user action handlers
    - Create proceedWithReport() function for Proceed button
    - Create closeFalseReportWarning() function for Cancel button
    - Handle overlay click as cancel action
    - Manage form submission state properly
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 3.4 Write property test for form interception
    - **Property 9: Form validation preservation**
    - **Validates: Requirements 6.3, 6.4, 6.5**

  - [ ]* 3.5 Write property test for button functionality
    - **Property 5: Button functionality**
    - **Validates: Requirements 3.3, 3.4**

- [x] 4. Checkpoint - Ensure core functionality works
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement CSS styling and responsive design
  - [x] 5.1 Add modal styling to existing CSS files
    - Reuse existing modal CSS classes for consistency
    - Add warning-specific color scheme (red for warning elements)
    - Style the false report list with proper spacing
    - Ensure proper button styling matches existing patterns
    - _Requirements: 4.1, 4.2_

  - [x] 5.2 Implement mobile responsive design
    - Add mobile-specific CSS media queries
    - Ensure modal scales properly on small screens
    - Test touch interaction compatibility
    - Verify readability on mobile devices
    - _Requirements: 4.4_

  - [ ]* 5.3 Write property test for mobile responsiveness
    - **Property 7: Mobile responsiveness**
    - **Validates: Requirements 4.4**

- [x] 6. Implement error handling and fallback mechanisms
  - [x] 6.1 Add API error handling in JavaScript
    - Implement try-catch blocks for fetch operations
    - Add 3-second timeout for API requests
    - Provide fallback to default threshold on errors
    - Log errors to console for debugging
    - _Requirements: 2.3, 2.4_

  - [x] 6.2 Add graceful degradation for JavaScript disabled
    - Ensure form still submits if JavaScript fails
    - Add fallback to browser confirm dialog if modal fails
    - Maintain progressive enhancement approach
    - _Requirements: 6.3, 6.4_

  - [ ]* 6.3 Write unit tests for error scenarios
    - Test API timeout handling
    - Test malformed JSON response handling
    - Test missing modal elements fallback
    - Test network failure scenarios
    - _Requirements: 2.3, 2.4_

- [x] 7. Implement accessibility features
  - [x] 7.1 Add ARIA attributes and keyboard navigation
    - Add proper ARIA labels for modal elements
    - Implement keyboard navigation (Tab, Escape, Enter)
    - Ensure screen reader compatibility
    - Add focus management for modal open/close
    - _Requirements: 4.5_

  - [ ]* 7.2 Write property test for accessibility compliance
    - **Property 8: Accessibility compliance**
    - **Validates: Requirements 4.5**

- [x] 8. Integration and testing
  - [x] 8.1 Integrate modal template with reports page
    - Include modal template in reports.html
    - Ensure proper template inheritance
    - Test modal display in actual report submission flow
    - Verify integration with existing form validation
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 8.2 Write property test for dynamic threshold display
    - **Property 2: Dynamic threshold display**
    - **Validates: Requirements 1.2, 2.2, 5.3**

  - [ ]* 8.3 Write property test for threshold updates
    - **Property 4: Threshold updates without restart**
    - **Validates: Requirements 2.4**

  - [ ]* 8.4 Write integration tests for complete flow
    - Test full user journey from form submission to warning to completion
    - Test both proceed and cancel user paths
    - Verify form validation continues to work properly
    - Test with various threshold values
    - _Requirements: 1.1, 3.3, 3.4, 6.3_

- [x] 9. Final checkpoint and validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The implementation reuses existing modal patterns for consistency
- Property tests validate universal correctness properties from the design
- Integration maintains existing form validation and error handling
- Mobile responsiveness follows existing application patterns