# Auto-Reopen Threshold Implementation

## Overview
The "Automatic Fix Threshold" setting has been repurposed as "Auto-Reopen Threshold" to automatically reopen fixed reports when the community indicates the issue persists.

## Changes Made

### 1. Settings Page (templates/settings.html)
**Updated Setting Display:**
- Title: "Automatic Fix Threshold" → "Auto-Reopen Threshold (Community Validation)"
- Description: Updated to reflect new purpose
- Unit label: "thumbs up" → "❌ reactions"

**New Description:**
> The number of "Still Broken" (❌) reactions required to automatically reopen a fixed report. This helps identify false fixes or recurring issues.

### 2. Backend Logic (app.py)
**Route: `/reports/<int:report_id>/react`**

Added auto-reopen logic that triggers when:
1. Report is currently marked as fixed (`is_fixed = True`)
2. "Still Broken" (thumbs down) count reaches threshold
3. Threshold is configurable via settings (default: 3)

**Actions Performed on Auto-Reopen:**
```python
report.is_fixed = False
report.fixed_at = None
report.status_updated_at = now_ts  # Reset to prevent expiration
report.thumbs_up_count = 0
report.thumbs_down_count = 0
# Delete all reactions for fresh start
```

### 3. Notification System
**Notification Sent to Report Owner:**
- Title: "Report Reopened - Issue Persists"
- Message: "Your report '[title]' has been automatically reopened due to community feedback indicating the issue persists."
- Link: Directs to My Reports page

## Key Features

### 1. Expiration Protection
When a report is reopened:
- `status_updated_at` is set to current timestamp
- This resets the expiration timer
- Report will NOT be hidden by auto-expire feature
- Gets full expiration period as if newly created

### 2. Fresh Start for Reactions
When reopening:
- All reaction counts reset to 0
- All existing reactions are deleted
- Allows community to provide fresh feedback
- Prevents stale reactions from affecting new status

### 3. Configurable Threshold
Admins can adjust sensitivity:
- Low threshold (e.g., 2): More responsive to community feedback
- High threshold (e.g., 5): Requires stronger consensus before reopening
- Default: 3 reactions

## User Flow

### Scenario: False Fix Detection
1. User marks pothole as fixed
2. Report appears on map with "Fixed" status
3. Community members visit location
4. Multiple users click ❌ "Still Broken"
5. When threshold reached (e.g., 3 reactions):
   - Report automatically reopens
   - Status changes to "Open"
   - Owner receives notification
   - All reactions reset
   - Expiration timer resets

### Scenario: Recurring Issue
1. Pothole was genuinely fixed
2. After some time, issue recurs (new pothole in same spot)
3. Community reports via ❌ reactions
4. Auto-reopen triggers
5. Report becomes active again without creating duplicate

## Benefits

### 1. Quality Control
- Identifies false fixes quickly
- Prevents premature closure of reports
- Community-driven validation

### 2. Reduced Duplicates
- Recurring issues reopen existing report
- No need to create new report for same location
- Maintains historical context

### 3. User Engagement
- Empowers community to correct mistakes
- Provides feedback mechanism for fix quality
- Increases trust in system accuracy

### 4. Automatic Management
- No admin intervention needed
- Self-correcting system
- Scales with community size

## Technical Details

### Database Changes
**No schema changes required**
- Uses existing `thumbs_down_count` field
- Uses existing `is_fixed`, `fixed_at` fields
- Uses existing `status_updated_at` field
- Uses existing `auto_fix_threshold` setting (repurposed)

### Expiration Logic
**Before Reopen:**
```python
# Fixed report expires after X days from fixed_at
if r.is_fixed and r.fixed_at:
    if (time.time() - r.fixed_at) > (expiration_days * 24 * 3600):
        # Hide from map
```

**After Reopen:**
```python
# status_updated_at is reset to current time
# Report gets full expiration period again
# Will not expire until marked fixed again
```

### Reaction Reset Logic
```python
# Clear all reactions when reopening
report.thumbs_up_count = 0
report.thumbs_down_count = 0
Reaction.query.filter_by(report_id=report.id).delete()
```

**Rationale:**
- Fresh start for community feedback
- Previous reactions were for "fixed" status
- New reactions will be for "open" status
- Prevents confusion and stale data

## Testing Checklist

### Settings Page
- [ ] Setting displays as "Auto-Reopen Threshold"
- [ ] Description mentions "Still Broken" reactions
- [ ] Unit label shows "❌ reactions"
- [ ] Can update threshold value
- [ ] Changes save correctly

### Auto-Reopen Functionality
- [ ] Fixed report with 3 ❌ reactions reopens automatically
- [ ] Report status changes to "Open"
- [ ] `is_fixed` becomes False
- [ ] `fixed_at` becomes None
- [ ] `status_updated_at` updates to current time
- [ ] Reaction counts reset to 0
- [ ] All reactions deleted from database

### Notification
- [ ] Report owner receives notification
- [ ] Notification title: "Report Reopened - Issue Persists"
- [ ] Notification includes report title
- [ ] Link directs to My Reports page
- [ ] Notification appears in bell icon

### Expiration Protection
- [ ] Reopened report does NOT expire immediately
- [ ] Gets full expiration period (e.g., 30 days)
- [ ] Expiration timer based on status_updated_at
- [ ] Report visible on map after reopening

### Map Display
- [ ] Reopened report shows as "Open" (not "Fixed")
- [ ] Icon changes to open status
- [ ] Reactions no longer available (only on fixed reports)
- [ ] Flag button available again

### Edge Cases
- [ ] Cannot reopen already-open report
- [ ] Threshold respects custom settings value
- [ ] Works with threshold = 1
- [ ] Works with high threshold (e.g., 10)
- [ ] Multiple simultaneous reactions handled correctly

## Configuration Examples

### Conservative (High Threshold)
```
Auto-Reopen Threshold: 5
```
- Requires strong community consensus
- Reduces false reopenings
- Good for areas with active community

### Responsive (Low Threshold)
```
Auto-Reopen Threshold: 2
```
- Quick response to issues
- More sensitive to feedback
- Good for areas with sparse community

### Balanced (Default)
```
Auto-Reopen Threshold: 3
```
- Moderate consensus required
- Balance between responsiveness and stability
- Recommended for most deployments

## Future Enhancements

### Potential Features
1. **Reopen History**: Track how many times a report has been reopened
2. **Cooldown Period**: Prevent immediate re-fixing after reopen
3. **Location Flagging**: Mark locations with frequent reopen cycles
4. **Admin Override**: Allow admins to prevent auto-reopen on specific reports
5. **Notification to Reactors**: Notify users who marked "Still Broken" when reopened
6. **Analytics**: Track reopen rates and patterns

### Metrics to Monitor
- Average time between fix and reopen
- Percentage of reports that get reopened
- Locations with highest reopen rates
- User engagement with verification system

## Rollback Plan

To revert to old behavior:

1. **Settings Page**: Change labels back to "Automatic Fix Threshold" and "thumbs up"
2. **Backend**: Remove auto-reopen logic from `react_to_report()`
3. **Restore Auto-Fix**: Add back the auto-fix logic that was removed earlier

All data remains intact during rollback.

## Related Documentation
- See `REACTIONS_FIXED_REPORTS_ONLY.md` for reaction system changes
- See settings page for threshold configuration
- See notification system for alert details
