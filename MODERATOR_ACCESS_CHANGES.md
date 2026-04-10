# Moderator Access Changes Implementation

## Overview

Implemented two key changes to moderator access:
1. **Moderators now have access to the "mark as fixed" brush tool** (previously admin-only)
2. **Admins and moderators can no longer submit their own reports** (prevents conflicts of interest)

## Changes Made

### 1. Mark as Fixed Brush Tool Access

**File: `templates/map.html`**

**Changed:**
```html
<!-- Before: Admin only -->
{% if is_admin %}
<button id="markFixedBtn" class="btn primary" type="button" title="Toggle brush to mark fixed">
  <img id="markFixedIcon" alt="Mark fixed brush" style="width: 32px; height: 32px; display: block;" />
</button>
{% endif %}

<!-- After: Admin and Moderator -->
{% if is_admin_or_moderator %}
<button id="markFixedBtn" class="btn primary" type="button" title="Toggle brush to mark fixed">
  <img id="markFixedIcon" alt="Mark fixed brush" style="width: 32px; height: 32px; display: block;" />
</button>
{% endif %}
```

**Impact:**
- Moderators can now see and use the brush tool on the map page
- Allows moderators to mark multiple defects as fixed by clicking and dragging
- No changes to the JavaScript logic were needed - it's controlled by button visibility

### 2. Report Submission Restriction

**File: `app.py`**

**Function: `reports_page()`**
```python
def reports_page():
    current_user = _login_required()
    if not isinstance(current_user, User):
        return current_user
    
    # NEW: Prevent admins and moderators from submitting reports
    if _is_admin_or_moderator(current_user):
        abort(403)
    
    # ... rest of function
```

**Function: `my_reports_page()`**
```python
def my_reports_page():
    current_user = _require_role('user')
    if not isinstance(current_user, User):
        return current_user
    
    # NEW: Prevent admins and moderators from accessing my reports
    if _is_admin_or_moderator(current_user):
        abort(403)
    
    # ... rest of function
```

**Impact:**
- Admins and moderators get a 403 Forbidden error when trying to access `/reports` or `/my-reports`
- Prevents conflicts of interest where moderators could submit reports and then approve them
- Maintains separation of duties between report submission (users) and moderation (moderators/admins)

## User Role Permissions Summary

### Regular Users
- ✅ Can submit reports via `/reports`
- ✅ Can view their reports via `/my-reports`
- ✅ Can access map and basic navigation
- ❌ Cannot mark defects as fixed
- ❌ Cannot access defects management

### Moderators
- ✅ Can access map page
- ✅ Can access defects management page
- ✅ **NEW:** Can use mark as fixed brush tool
- ✅ Can review AI detections (confirm/reject)
- ❌ **NEW:** Cannot submit reports
- ❌ **NEW:** Cannot access my reports page
- ❌ Cannot access admin-only features (user management, backups, etc.)

### Admins
- ✅ Full access to all features
- ✅ Can use mark as fixed brush tool
- ❌ **NEW:** Cannot submit reports
- ❌ **NEW:** Cannot access my reports page

## Security Considerations

1. **Separation of Duties**: Moderators and admins can no longer create reports they could then moderate
2. **Role Clarity**: Clear distinction between users (report submitters) and moderators (report reviewers)
3. **Audit Trail**: All mark-as-fixed actions are still logged and traceable
4. **Access Control**: Proper 403 errors prevent unauthorized access attempts

## Testing

Created `test_moderator_access_changes.py` to verify:
- ✅ Map template shows brush tool for moderators
- ✅ Reports route blocks admins and moderators  
- ✅ Navigation is properly configured for moderators

All tests pass successfully.

## Backward Compatibility

- No breaking changes for existing users
- Existing moderator accounts will immediately gain brush tool access
- Existing admin/moderator accounts will be blocked from report submission (as intended)
- All existing functionality for regular users remains unchanged