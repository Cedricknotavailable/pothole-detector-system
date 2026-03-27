# Bugfix Requirements Document

## Introduction

This document addresses notification routing and functionality issues in the mobile responsive version of the application. The bug manifests in three distinct ways:

1. **My Reports Page**: Clicking the notification bell triggers a navigation to `/notifications` route, which attempts to render a non-existent `notifications.html` template, resulting in a "template not found" error
2. **Analytics Page**: Notification bell is present but completely non-functional - missing both the popup HTML structure and JavaScript implementation
3. **Settings Page**: Notifications are fully functional (reference implementation)

The root cause is inconsistent notification implementation across pages. Some pages use a popup-based approach (correct), while My Reports uses a direct link to a missing template (incorrect), and Analytics has incomplete implementation.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user clicks the notification bell on the My Reports page THEN the system navigates to `/notifications` route which attempts to render the non-existent `notifications.html` template, causing a template not found error

1.2 WHEN a user clicks the notification bell on the Analytics page THEN the system does nothing because the notification popup HTML and JavaScript implementation are missing

1.3 WHEN the `/notifications` route is accessed directly THEN the system attempts to render `notifications.html` which does not exist, causing a template not found error

### Expected Behavior (Correct)

2.1 WHEN a user clicks the notification bell on the My Reports page THEN the system SHALL display a notification popup overlay (not navigate to a different page) showing unread notifications

2.2 WHEN a user clicks the notification bell on the Analytics page THEN the system SHALL display a notification popup overlay showing unread notifications with full interactive functionality (mark as read, mark all as read)

2.3 WHEN the notification popup is displayed on any page THEN the system SHALL fetch unread notifications via `/notifications/unread` API endpoint and render them in the popup

2.4 WHEN a user clicks on a notification item in the popup THEN the system SHALL mark that notification as read via `/notifications/mark-read/<id>` API endpoint and navigate to the notification's link if present

2.5 WHEN a user clicks "Mark all read" button in the notification popup THEN the system SHALL mark all notifications as read via `/notifications/mark-all-read` API endpoint

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user clicks the notification bell on the Settings page THEN the system SHALL CONTINUE TO display the notification popup with full functionality as currently implemented

3.2 WHEN a user clicks the notification bell on the Users page THEN the system SHALL CONTINUE TO display the notification popup with full functionality as currently implemented

3.3 WHEN the notification badge shows unread count THEN the system SHALL CONTINUE TO display the red badge indicator on pages where notifications are properly implemented

3.4 WHEN notifications are polled every 30 seconds THEN the system SHALL CONTINUE TO automatically refresh the notification count and list on pages where notifications are properly implemented

3.5 WHEN the `/notifications/unread`, `/notifications/mark-read/<id>`, and `/notifications/mark-all-read` API endpoints are called THEN the system SHALL CONTINUE TO function correctly as they currently do
