# Task 8.3 Manual Verification Guide

## Overview
This guide helps you manually verify that the audit log JavaScript functions have been successfully migrated to the analytics page and work correctly.

## Prerequisites
1. Flask app must be running (`python app.py`)
2. You must be logged in as an admin user
3. Browser developer tools should be open (F12)

## Test Steps

### 1. Access Analytics Page
1. Navigate to `/analytics` in your browser
2. **Expected**: Page loads without JavaScript errors
3. **Check**: Open browser console (F12 → Console tab)
4. **Expected**: No errors related to audit log functions

### 2. Verify Audit Log Section Visibility
1. Scroll down to the "System Activity Log" section
2. **Expected**: You should see:
   - Section title: "System Activity Log"
   - Description text
   - Filter controls (Action Type, Actor, Start Date, End Date)
   - Apply and Export buttons
   - A table with headers: Timestamp, Actor, Action, Resource, Detail, IP Address
   - Table should show audit log entries (or "Loading..." briefly)

### 3. Test Initial Load
1. Wait for the page to fully load (all charts should render)
2. **Expected**: After ~500ms, the audit log table should populate with entries
3. **Expected**: The "Action Type" dropdown should populate with available action types
4. **Check Console**: Look for any fetch requests to `/api/audit-log`
5. **Expected**: No errors in console

### 4. Test Action Type Filter
1. Click the "Action Type" dropdown
2. **Expected**: Should show options like:
   - All Actions
   - USER LOGIN
   - USER LOGOUT
   - REPORT SUBMITTED
   - etc.
3. Select "USER LOGIN"
4. Click "Apply" button
5. **Expected**: Table should refresh and show only USER_LOGIN entries
6. **Expected**: Each entry should have a colored badge showing the action type

### 5. Test Actor Filter
1. Type a username in the "Actor" field (e.g., "admin" or "testuser1")
2. Click "Apply" button
3. **Expected**: Table should refresh and show only entries for that user
4. **Expected**: The "Actor" column should show the filtered username

### 6. Test Date Range Filter
1. Set a "Start Date" (e.g., one week ago)
2. Set an "End Date" (e.g., today)
3. Click "Apply" button
4. **Expected**: Table should refresh and show only entries within that date range
5. **Expected**: All timestamps should fall within the selected range

### 7. Test Combined Filters
1. Set Action Type to "USER_LOGIN"
2. Enter an actor name
3. Set a date range
4. Click "Apply" button
5. **Expected**: Table should show entries matching ALL filter criteria

### 8. Test Pagination (if more than 20 entries)
1. If you have more than 20 audit log entries, pagination should appear
2. **Expected**: At the bottom of the table, you should see:
   - Entry count (e.g., "45 entries")
   - Page numbers (e.g., 1, 2, 3)
   - Previous/Next buttons
3. Click "Next" or a page number
4. **Expected**: Table should refresh with the next page of entries
5. **Expected**: Page number should be highlighted
6. **Expected**: URL parameters should NOT change (pagination is client-side)

### 9. Test Export Functionality
1. Set some filters (optional)
2. Click the "Export" button
3. **Expected**: A CSV file named "audit_log.csv" should download
4. Open the CSV file
5. **Expected**: Should contain columns: Timestamp, Actor, Action, Resource Type, Resource ID, Detail, IP Address
6. **Expected**: Should contain all entries matching the current filters (up to 10,000 entries)
7. **Expected**: Detail column should show JSON-formatted data

### 10. Test Badge Colors
1. Look at the "Action" column in the table
2. **Expected**: Different action types should have different colored badges:
   - Auth actions (LOGIN, LOGOUT) → Blue badge
   - User management → Yellow badge
   - Reports → Pink badge
   - Defects → Purple badge
   - Settings → Purple badge
   - Backup → Green badge

### 11. Test Responsive Behavior
1. Resize browser window to mobile size (< 768px)
2. **Expected**: Table should remain readable
3. **Expected**: Filters should stack vertically or wrap appropriately
4. **Expected**: No horizontal scrolling issues

### 12. Test Error Handling
1. Stop the Flask app
2. Click "Apply" button in the audit log filters
3. **Expected**: Table should show an error message
4. **Expected**: Console should show a network error
5. Restart Flask app
6. Click "Apply" again
7. **Expected**: Table should load successfully

### 13. Verify Settings Page
1. Navigate to `/settings`
2. **Expected**: The audit log section should NOT be present
3. **Expected**: Only "General Configuration" and "Backup and Recovery" sections should be visible
4. **Check Console**: No errors related to missing audit log functions

## Success Criteria

✅ All tests pass without errors
✅ Audit log loads automatically after charts
✅ All filters work correctly
✅ Pagination works (if applicable)
✅ Export generates valid CSV
✅ Badge colors display correctly
✅ No JavaScript errors in console
✅ Settings page does not have audit log
✅ Responsive design works on mobile

## Common Issues

### Issue: "Loading..." never goes away
**Solution**: 
- Check browser console for errors
- Verify Flask app is running
- Check that you're logged in as admin
- Hard refresh (Ctrl+Shift+R)

### Issue: Action Type dropdown is empty
**Solution**:
- Check that audit log entries exist in database
- Verify API endpoint `/api/audit-log` is working
- Check browser console for API errors

### Issue: Export button does nothing
**Solution**:
- Check browser console for errors
- Verify popup blocker is not blocking download
- Check that exportAuditLog() function exists

### Issue: Pagination doesn't appear
**Solution**:
- This is normal if you have 20 or fewer entries
- Add more audit log entries by performing actions (login, logout, etc.)

## Cleanup

After testing, you can:
1. Clear any test filters
2. Close browser developer tools
3. Continue using the application normally

## Notes

- The audit log auto-loads 500ms after the charts finish loading
- Pagination shows 20 entries per page
- Export can retrieve up to 10,000 entries
- Filters are applied on the server side (via API)
- The audit log uses the same API endpoint as before: `/api/audit-log`
