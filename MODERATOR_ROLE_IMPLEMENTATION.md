# Moderator Role Implementation

## Overview
Added a new "moderator" role to the system - a subordinate role to admin that focuses on defect management without access to user management or analytics.

## Role Name
**moderator** - Industry-standard name for content/data management roles with limited administrative privileges.

## Permissions

### Moderator Can Access:
- ✅ Defects Management page (`/defects`)
  - Mark defects as fixed
  - Remove false reports
  - Verify unsure reports
  - View all user reports and system detections
  - Apply filters and search
- ✅ Map page (`/map`)
- ✅ Settings page (`/settings`) - for their own account settings
- ✅ Notifications

### Moderator Cannot Access:
- ❌ User Management page (`/users`) - Cannot modify user accounts or roles
- ❌ Analytics page (`/analytics`) - No access to analytics data
- ❌ Survey/Index page (`/index`) - Admin-only survey management
- ❌ Backup Management (`/admin/backups`) - Admin-only database operations

## Implementation Details

### 1. Database Changes
- Added "moderator" to `ALLOWED_ROLES` constant in `app.py`
- Existing `role` column in User table supports this (VARCHAR(20))

### 2. Helper Functions Added
```python
def _is_moderator(user) -> bool
def _is_admin_or_moderator(user) -> bool
def _require_admin_or_moderator()
```

### 3. Route Updates
- `/defects` - Changed from `_require_admin()` to `_require_admin_or_moderator()`
- Login redirect - Moderators redirect to `/defects` page after login

### 4. UI Updates
- **templates/defects.html**: Conditional sidebar navigation based on role
  - Admins see all links (Survey, Map, Users, Defects, Settings, Backups, Analytics)
  - Moderators see limited links (Map, Defects, Settings)
- **templates/users.html**: Added "moderator" option to role dropdowns
  - Filter dropdown includes moderator option
  - User edit dropdown includes moderator option

## Role Hierarchy
1. **admin** - Full system access
2. **moderator** - Defect management only (NEW)
3. **user** - Regular user access

## Usage

### Creating a Moderator Account
Admins can promote existing users to moderator role via the User Management page:
1. Go to `/users`
2. Find the user
3. Change their role dropdown from "user" to "moderator"
4. Click Save

### Moderator Login Experience
1. Moderator logs in
2. Automatically redirected to `/defects` page
3. Sidebar shows only: Map, Defects Management, Settings, Log Out
4. Attempting to access restricted pages (users, analytics, backups) returns 403 Forbidden

## Testing Recommendations
1. Create a test moderator account
2. Verify moderator can access `/defects` and perform all defect operations
3. Verify moderator cannot access `/users`, `/analytics`, `/admin/backups`, `/index`
4. Verify moderator sees correct navigation menu
5. Verify role filter and edit dropdowns show moderator option

## Files Modified
- `app.py` - Role constants, helper functions, route permissions, login redirect
- `templates/defects.html` - Conditional navigation
- `templates/users.html` - Role dropdown options
