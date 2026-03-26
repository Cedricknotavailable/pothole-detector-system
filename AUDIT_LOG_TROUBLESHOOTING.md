# Audit Log Troubleshooting Guide

## Current Status

The audit log feature has been implemented and the code is correct. The database contains 13 audit log entries with 3 action types (REPORT_SUBMITTED, USER_LOGIN, USER_LOGOUT).

## Changes Made

1. **Fixed accordion click handler** - Removed duplicate event listener that was causing race conditions
2. **Added debug logging** - Console will now show detailed information about API requests and responses
3. **Improved error handling** - Better error messages for failed API calls

## Troubleshooting Steps

### Step 1: Restart Flask App (CRITICAL)

The Flask app MUST be restarted to pick up the code changes:

1. Stop the current Flask app (Ctrl+C in the terminal where it's running)
2. Start it again: `python app.py`

### Step 2: Clear Browser Cache (CRITICAL)

The browser may be serving cached JavaScript:

1. Open the Settings page in your browser
2. Press **Ctrl + Shift + R** (Windows) or **Cmd + Shift + R** (Mac) to hard refresh
3. Or open DevTools (F12), right-click the refresh button, and select "Empty Cache and Hard Reload"

### Step 3: Check Browser Console

1. Open the Settings page
2. Press **F12** to open Developer Tools
3. Click on the "Console" tab
4. Click on the "Activity & Audit Log" accordion
5. You should see console messages like:
   ```
   Fetching audit log: /api/audit-log?page=1
   Response status: 200 OK
   Audit log data: {items: Array(13), total: 13, ...}
   Populated action types: ['REPORT_SUBMITTED', 'USER_LOGIN', 'USER_LOGOUT']
   ```

### Step 4: Check for Errors

If you see errors in the console:

- **403 Forbidden**: You're not logged in as an admin
- **404 Not Found**: Flask app not running or wrong URL
- **500 Internal Server Error**: Check Flask console for Python errors
- **Network Error**: Flask app not running

### Step 5: Test the API Directly

Run the test script to verify the endpoint works:

```bash
python test_audit_endpoint.py
```

This will test the `/api/audit-log` endpoint directly and show you the response.

## Expected Behavior

When you click on "Activity & Audit Log":

1. The accordion should expand
2. The table should show "Loading..." briefly
3. The action filter dropdown should populate with:
   - All Actions
   - REPORT SUBMITTED
   - USER LOGIN
   - USER LOGOUT
4. The table should show 13 audit log entries
5. You should see login/logout entries for testuser1

## Database Verification

The database has been verified to contain correct data:

```
ID: 13 - USER_LOGIN by testuser1 at 2026-03-26 02:10:27
ID: 12 - USER_LOGIN by testuser1 at 2026-03-26 02:09:36
ID: 11 - USER_LOGOUT by testuser1 at 2026-03-26 02:09:34
... (10 more entries)
```

## Common Issues

### Issue: "Loading..." never goes away

**Cause**: Flask app not restarted or browser cache not cleared

**Solution**: 
1. Restart Flask app
2. Hard refresh browser (Ctrl+Shift+R)
3. Check browser console for errors

### Issue: Action filter only shows "All Actions"

**Cause**: API request failing or returning empty action_types array

**Solution**:
1. Check browser console for API errors
2. Verify Flask app is running
3. Check Flask console for Python errors
4. Run `python test_audit_endpoint.py` to test the endpoint

### Issue: 403 Forbidden error

**Cause**: Not logged in as admin

**Solution**: Log in with an admin account

## Files Modified

- `templates/settings.html` - Fixed accordion handler, added debug logging
- `app.py` - No changes needed (already correct)

## Next Steps

1. **RESTART FLASK APP** (most important!)
2. **HARD REFRESH BROWSER** (Ctrl+Shift+R)
3. Open Settings page
4. Open browser console (F12)
5. Click "Activity & Audit Log"
6. Check console for debug messages
7. Report any errors you see in the console
