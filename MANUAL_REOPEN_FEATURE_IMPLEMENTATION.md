# Manual Reopen Feature Implementation

## Overview
Users can now manually reopen their own fixed reports by uploading new photo evidence. This complements the automatic community-driven reopen feature and provides a direct way for report owners to indicate recurring or persistent issues.

## Features

### 1. User Interface
**My Reports Page - Desktop Table View:**
- Fixed reports show: `[Fixed Badge] [Reopen Button]`
- Open reports show: `[Mark Fixed Button]`

**My Reports Page - Mobile Card View:**
- Fixed reports show badge and reopen button in actions row
- Open reports show mark fixed button

### 2. Reopen Modal
**Photo Upload Required:**
- Modal prompts user to upload new photo
- Explains purpose: verify issue persists/recurred
- Shows live preview of selected photo
- Validates file type (JPG, PNG only)
- Validates file size (max 10MB)
- Responsive design with proper styling

### 3. Backend Processing
**Route: `/reports/<int:report_id>/reopen`**

**Validations:**
- User must be authenticated
- User must be report owner
- Report must be currently fixed
- Photo upload is required
- File type must be JPG or PNG
- File size must be under 10MB

**Actions Performed:**
1. Save new photo with unique filename
2. Delete old photo from filesystem
3. Update report:
   - `is_fixed = False`
   - `fixed_at = None`
   - `status_updated_at = current_time` (resets expiration)
   - `photo_path = new_photo_path`
4. Reset reaction counts to 0
5. Delete all existing reactions
6. Notify all admins and moderators
7. Write audit log entry

### 4. Notifications
**Sent to: All Admins and Moderators**

**Notification Details:**
- Title: "Report Reopened by User"
- Message: "User [username] reopened their report '[title]' with new photo evidence. The issue may have recurred or persists."
- Link: Direct link to defect location on map (`/map?lat=X&lng=Y`)
- Call-to-action: Click to view on map

**Not Notified:**
- The user who reopened (no self-notification)
- Regular users without admin/moderator role

## User Flow

### Scenario: User Reopens Report
1. User navigates to My Reports page
2. Sees their fixed report with "Reopen" button
3. Clicks "Reopen" button
4. Modal opens requesting new photo
5. User selects photo from device
6. Preview shows selected image
7. User clicks "Reopen Report"
8. Photo uploads and report reopens
9. Page reloads showing report as "Open"
10. Admins/moderators receive notification

### Scenario: Admin Receives Notification
1. Admin sees notification bell badge
2. Clicks bell to view notifications
3. Sees "Report Reopened by User" notification
4. Clicks notification
5. Redirected to map at exact defect location
6. Can verify issue and take action

## Technical Details

### Photo Management
**Old Photo Deletion:**
```python
if report.photo_path:
    old_photo_full_path = os.path.join(app.root_path, 'static', report.photo_path)
    if os.path.exists(old_photo_full_path):
        os.remove(old_photo_full_path)
```

**New Photo Storage:**
```python
unique_filename = f"{uuid4().hex}.{ext}"
photo_path = os.path.join(UPLOAD_FOLDER, unique_filename)
photo_file.save(photo_path)
report.photo_path = f"uploads/reports/{unique_filename}"
```

### Expiration Reset
When reopened:
- `status_updated_at` set to current timestamp
- Report gets full expiration period (e.g., 30 days)
- Will not be hidden by auto-expire feature
- Same behavior as newly created report

### Reaction Reset
**Why Reset Reactions:**
- Previous reactions were for "fixed" status
- New status is "open" - different context
- Allows fresh community feedback
- Prevents confusion from stale data

**Implementation:**
```python
report.thumbs_up_count = 0
report.thumbs_down_count = 0
Reaction.query.filter_by(report_id=report.id).delete()
```

### Map Link Generation
```python
map_link = url_for('map_page', lat=report.latitude, lng=report.longitude, _external=False)
```
- Generates link with lat/lng parameters
- Map will center on defect location
- Allows immediate verification

## Files Modified

### 1. templates/my_reports.html
- Added "Reopen" button for fixed reports (desktop)
- Added "Reopen" button for fixed reports (mobile cards)
- Updated dynamically created cards to include reopen button
- Included reopen modal template

### 2. templates/reopen_report_modal.html (NEW)
- Modal UI with photo upload
- Live photo preview
- Form validation
- Error handling
- Loading states
- Responsive design

### 3. app.py
- Added `/reports/<int:report_id>/reopen` endpoint
- Photo upload handling
- Old photo deletion
- Report status update
- Reaction reset logic
- Admin/moderator notifications
- Audit logging

## Security Considerations

### 1. Authorization
- Only report owner can reopen
- Verified via `report.user_id == current_user.id`
- Returns 403 if unauthorized

### 2. File Upload Security
- Filename sanitized with `secure_filename()`
- Extension whitelist (JPG, PNG only)
- File size limit (10MB)
- Unique filename prevents collisions
- Stored in designated upload folder

### 3. State Validation
- Can only reopen fixed reports
- Returns 400 if report not fixed
- Prevents invalid state transitions

## Testing Checklist

### UI Testing
- [ ] "Reopen" button appears for fixed reports (desktop)
- [ ] "Reopen" button appears for fixed reports (mobile)
- [ ] "Mark Fixed" button appears for open reports
- [ ] Both buttons visible on same row for fixed reports
- [ ] Modal opens when clicking "Reopen"
- [ ] Modal closes on Cancel or X button
- [ ] Modal closes on Escape key

### Photo Upload
- [ ] Can select JPG file
- [ ] Can select PNG file
- [ ] Preview shows selected image
- [ ] Rejects non-image files
- [ ] Rejects files over 10MB
- [ ] Shows appropriate error messages
- [ ] Upload button disabled during upload
- [ ] Shows loading state during upload

### Backend Processing
- [ ] Report status changes to "Open"
- [ ] `is_fixed` becomes False
- [ ] `fixed_at` becomes None
- [ ] `status_updated_at` updates to current time
- [ ] New photo saved to filesystem
- [ ] Old photo deleted from filesystem
- [ ] `photo_path` updated in database
- [ ] Reaction counts reset to 0
- [ ] All reactions deleted

### Notifications
- [ ] All admins receive notification
- [ ] All moderators receive notification
- [ ] Report owner does NOT receive notification
- [ ] Regular users do NOT receive notification
- [ ] Notification title correct
- [ ] Notification message includes username and report title
- [ ] Notification link goes to map location
- [ ] Map centers on defect when link clicked

### Expiration
- [ ] Reopened report does NOT expire immediately
- [ ] Gets full expiration period
- [ ] Visible on map after reopening
- [ ] Expiration based on status_updated_at

### Audit Log
- [ ] Audit log entry created
- [ ] Action: "REPORT_REOPENED"
- [ ] Includes report title
- [ ] Includes username
- [ ] Includes new photo path

### Edge Cases
- [ ] Cannot reopen already-open report
- [ ] Cannot reopen someone else's report
- [ ] Handles missing photo gracefully
- [ ] Handles invalid file types
- [ ] Handles oversized files
- [ ] Handles filesystem errors
- [ ] Handles database errors

## Comparison: Manual vs Automatic Reopen

### Manual Reopen (This Feature)
- **Trigger**: User clicks "Reopen" button
- **Requirement**: New photo upload
- **Who**: Report owner only
- **Notification**: Admins and moderators
- **Photo**: Replaces old photo
- **Use Case**: User revisits location, sees issue persists

### Automatic Reopen (Community-Driven)
- **Trigger**: Threshold of ❌ reactions reached
- **Requirement**: Community feedback
- **Who**: Any user can react
- **Notification**: Report owner only
- **Photo**: Unchanged
- **Use Case**: Community identifies false fix

Both features work together to ensure report accuracy.

## Benefits

### 1. User Empowerment
- Users can directly report recurring issues
- No need to create duplicate reports
- Maintains historical context
- Provides evidence with new photo

### 2. Admin Awareness
- Admins immediately notified of reopened reports
- Direct link to location for quick verification
- Can prioritize recurring issues
- Reduces duplicate report creation

### 3. Data Quality
- Fresh photo evidence for current status
- Accurate representation of issue state
- Community can provide fresh feedback
- Prevents stale data confusion

### 4. Workflow Efficiency
- Single report tracks issue lifecycle
- No duplicate reports for same location
- Clear audit trail of status changes
- Easy to identify problematic locations

## Future Enhancements

### Potential Features
1. **Reopen History**: Track number of times report reopened
2. **Reopen Reason**: Optional text field explaining why
3. **Photo Comparison**: Show before/after photos side-by-side
4. **Reopen Cooldown**: Prevent immediate re-fixing after reopen
5. **Location Flagging**: Mark locations with frequent reopens
6. **Notification Preferences**: Allow admins to opt-out of reopen notifications
7. **Bulk Reopen**: Allow reopening multiple reports at once
8. **Mobile App Integration**: Support photo upload from mobile app

### Metrics to Monitor
- Reopen rate (% of fixed reports that get reopened)
- Average time between fix and reopen
- Locations with highest reopen rates
- User engagement with reopen feature
- Admin response time to reopen notifications

## Related Features
- See `AUTO_REOPEN_THRESHOLD_IMPLEMENTATION.md` for automatic community-driven reopen
- See `REACTIONS_FIXED_REPORTS_ONLY.md` for reaction system on fixed reports
- See notification system documentation for alert details
