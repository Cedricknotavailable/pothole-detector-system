# Requirements Document

## Introduction

This document specifies six UI/UX improvements to the Surveyor.AI application. These enhancements focus on improving user experience, preventing accidental actions, providing clearer feedback, and enabling community-driven content moderation. The improvements maintain consistency with existing design patterns while adding new functionality that aligns with industry standards.

## Glossary

- **System**: The Surveyor.AI web application
- **User**: Any authenticated person using the application (admin or regular user)
- **Admin**: A user with administrative privileges
- **Report**: A user-submitted defect report containing location, type, description, and optional photo
- **Detection**: An AI-identified defect from automated survey
- **Defect**: Either a Report or Detection representing a road obstruction
- **False_Report**: A report flagged by the community or admin as inaccurate or fraudulent
- **Flag**: A community action marking a report as false
- **Reaction**: A thumbs up or thumbs down response to a report
- **Audit_Log**: A chronological record of system actions and changes
- **Filter**: A UI control that narrows displayed data based on criteria
- **Logout**: The action of ending an authenticated session
- **Photo_Attachment**: An image file uploaded with a report submission
- **Confirmation_Dialog**: A modal UI element requiring explicit user confirmation before proceeding

## Requirements

### Requirement 1: Community False Report Flagging

**User Story:** As a user, I want to flag reports as false, so that inaccurate or fraudulent reports can be identified and removed by the community.

#### Acceptance Criteria

1. WHEN a user views a report, THE System SHALL display a "Flag as False Report" action alongside existing reactions
2. WHEN a user clicks "Flag as False Report", THE System SHALL record the flag action with the user ID and timestamp
3. WHEN the number of flags on a report reaches the configured threshold, THE System SHALL automatically mark the report as false
4. WHERE the false report auto-flag feature is enabled, THE System SHALL increment the report author's false_reports_count
5. WHEN a report is auto-flagged as false, THE System SHALL create a notification for the report author
6. THE System SHALL prevent duplicate flags from the same user on the same report
7. WHEN a report is marked as false, THE System SHALL hide it from the map view
8. THE System SHALL write an audit log entry when a report is flagged or auto-marked as false

### Requirement 2: Configurable False Report Threshold

**User Story:** As an admin, I want to configure how many flags trigger auto-flagging, so that I can adjust community moderation sensitivity.

#### Acceptance Criteria

1. THE System SHALL store a setting named "community_false_report_threshold" with a default value of 3
2. WHEN an admin accesses the settings page, THE System SHALL display the threshold configuration in the General Configuration section
3. THE System SHALL validate that the threshold value is a positive integer greater than or equal to 1
4. WHEN an admin saves the threshold setting, THE System SHALL update the database and write an audit log entry
5. WHEN evaluating flags on a report, THE System SHALL compare the flag count against the current threshold value

### Requirement 3: Logout Confirmation Dialog

**User Story:** As a user, I want to confirm before logging out, so that I don't accidentally end my session.

#### Acceptance Criteria

1. WHEN a user clicks the logout link on any page, THE System SHALL display a confirmation dialog before proceeding
2. THE Confirmation_Dialog SHALL contain the message "Are you sure you want to log out?"
3. THE Confirmation_Dialog SHALL provide "Cancel" and "Log Out" action buttons
4. WHEN the user clicks "Cancel", THE System SHALL close the dialog and remain on the current page
5. WHEN the user clicks "Log Out", THE System SHALL proceed with the logout action
6. THE System SHALL apply this confirmation to both admin and regular user dashboards

### Requirement 4: Audit Log Relocation

**User Story:** As an admin, I want to view audit logs on the analytics page, so that activity monitoring is grouped with other analytical data.

#### Acceptance Criteria

1. THE System SHALL remove the audit log section from the settings page
2. THE System SHALL add an audit log section to the analytics page
3. THE Audit_Log section SHALL maintain all existing functionality including filters, pagination, and export
4. THE System SHALL preserve the audit log table layout and styling
5. THE System SHALL ensure the audit log section fits within the analytics page layout without overflow
6. WHEN an admin accesses the analytics page, THE System SHALL load audit log data using the existing API endpoint

### Requirement 5: Specific Login and Registration Error Messages

**User Story:** As a user, I want to see which field has an error during login or registration, so that I can correct the specific problem.

#### Acceptance Criteria

1. WHEN login fails due to incorrect username or email, THE System SHALL display "Username or email not found" below the username field
2. WHEN login fails due to incorrect password, THE System SHALL display "Incorrect password" below the password field
3. WHEN registration fails due to duplicate username, THE System SHALL display "Username already exists" below the username field
4. WHEN registration fails due to duplicate email, THE System SHALL display "Email already registered" below the email field
5. WHEN registration fails due to invalid email format, THE System SHALL display "Invalid email format" below the email field
6. WHEN registration fails due to weak password, THE System SHALL display the specific password requirement that was not met below the password field
7. THE System SHALL clear previous error messages when the user modifies any input field
8. THE System SHALL display field-specific errors without showing generic error messages

### Requirement 6: Rename Reset to Clear Filters

**User Story:** As a user, I want filter buttons to say "Clear Filters" instead of "Reset", so that the button purpose is immediately clear.

#### Acceptance Criteria

1. THE System SHALL change the filter reset button text from "Reset" to "Clear Filters" on the users page
2. THE System SHALL change the filter reset button text from "Reset" to "Clear Filters" on the defects page
3. THE System SHALL change the filter reset button text from "Reset" to "Clear Filters" on the my reports page
4. THE System SHALL change the filter reset button text from "Reset" to "Clear Filters" on the map page
5. THE System SHALL maintain the existing button functionality and styling
6. THE System SHALL ensure button text remains visible and properly aligned after the change

### Requirement 7: Required Photo Attachment

**User Story:** As an admin, I want photo attachments to be required when submitting reports, so that all reports have visual evidence.

#### Acceptance Criteria

1. WHEN a user accesses the report submission form, THE System SHALL mark the photo upload field as required
2. WHEN a user attempts to submit a report without a photo, THE System SHALL prevent submission and display "Photo is required" error message
3. THE System SHALL validate photo presence on the client side before form submission
4. THE System SHALL validate photo presence on the server side and return an error if missing
5. THE System SHALL accept only JPG and PNG image formats
6. WHEN a user selects a valid photo, THE System SHALL display a preview of the image
7. THE System SHALL update the form label from "Evidence Photo (Optional)" to "Evidence Photo"

