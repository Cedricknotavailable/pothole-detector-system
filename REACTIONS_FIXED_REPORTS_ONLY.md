# Reactions Relocated to Fixed Reports Only

## Overview
Reactions have been relocated from submitted (open) reports to fixed reports only. This changes the purpose of reactions from "this needs fixing" to "verification of fix status".

## Changes Made

### 1. Backend (app.py)
**Route: `/reports/<int:report_id>/react`**

- Added validation: `if not report.is_fixed: return error 403`
- Removed auto-fix logic (no longer needed since reactions only work on fixed reports)
- Kept all existing reaction toggle/change logic intact
- Database schema unchanged - all existing reaction data preserved

### 2. Map View (templates/map.html)
**Popup Display Logic**

- **Before**: Reactions shown on open reports, hidden on fixed reports
- **After**: Reactions shown ONLY on fixed reports, flag button shown on open reports

**New Reaction Meanings:**
- ✅ (Verified Fixed) - User confirms the pothole is actually fixed
- ❌ (Still Broken) - User reports the pothole is still broken despite being marked fixed

**Implementation:**
```javascript
const reactionsHtml = it.is_fixed ? `
  <button>✅ ${it.thumbs_up || 0}</button>
  <button>❌ ${it.thumbs_down || 0}</button>
` : `
  <button>🚩 Flag</button>
`;
```

### 3. My Reports Page (templates/my_reports.html)
**Desktop Table View:**
- Column renamed: "Reactions" → "Verification"
- Shows reaction counts only for fixed reports
- Shows "—" for open reports

**Mobile Card View:**
- "Reactions" row only appears if report is fixed
- Uses conditional rendering: `{% if r.is_fixed %}`
- Dynamically created cards also check `r.is_fixed`

**Icons Updated:**
- 👍/👎 → ✅/❌
- Titles: "Verified Fixed" / "Still Broken"

## New User Flow

### For Open Reports
1. User submits report → appears on map as open
2. Other users can only FLAG the report (not react)
3. Report owner or admin marks as fixed

### For Fixed Reports
1. Report is marked as fixed (by owner, admin, or moderator)
2. Reactions become available to all users (except report owner)
3. Users can verify:
   - ✅ "Verified Fixed" - Confirms the fix is real
   - ❌ "Still Broken" - Reports the issue persists
4. Reactions help validate fix accuracy

## Data Preservation

### Existing Reactions
- All existing reaction data in the database is preserved
- Reaction counts remain accurate
- Users can still toggle/change their reactions on fixed reports
- No data migration needed

### Database Tables
- `reaction` table: Unchanged
- `report` table: Unchanged (thumbs_up_count, thumbs_down_count preserved)
- All foreign keys and constraints intact

## Breaking Changes

### Removed Features
1. **Auto-fix threshold**: No longer applicable since reactions only work on already-fixed reports
2. **Auto-fix notification**: Removed since reports must be manually marked fixed first

### API Changes
- `/reports/<int:report_id>/react` now returns 403 error if report is not fixed
- Error message: "Reactions are only available for fixed reports"

## Benefits

### 1. Clearer Purpose
- Reactions now serve as verification mechanism
- Helps identify false fixes or recurring issues
- More meaningful community feedback

### 2. Reduced Confusion
- Users no longer confused about reaction purpose on open reports
- Clear distinction between flagging (open) and verifying (fixed)

### 3. Better Data Quality
- Reactions on fixed reports provide actionable feedback
- Helps identify reports that need re-opening
- Community validation of fix quality

## Testing Checklist

### Backend
- [ ] Cannot react to open reports (403 error)
- [ ] Can react to fixed reports
- [ ] Cannot react to own reports
- [ ] Reaction toggle works (add/remove)
- [ ] Reaction change works (up→down, down→up)
- [ ] Counts update correctly

### Map View
- [ ] Open reports show flag button only
- [ ] Fixed reports show reaction buttons (✅/❌)
- [ ] Reaction counts display correctly
- [ ] Clicking reactions updates counts in real-time
- [ ] Popup updates after reaction

### My Reports Page
- [ ] Desktop: "Verification" column shows counts for fixed reports
- [ ] Desktop: Open reports show "—" in verification column
- [ ] Mobile: Verification row only appears for fixed reports
- [ ] Mobile: Infinite scroll preserves reaction display logic
- [ ] Icons are ✅/❌ (not 👍/👎)

### Edge Cases
- [ ] Existing reactions on now-fixed reports still work
- [ ] Reaction counts preserved after marking as fixed
- [ ] Cannot react to archived/deleted reports
- [ ] Admin/moderator can see all reactions

## Migration Notes

### No Database Migration Required
- Existing schema supports new behavior
- No ALTER TABLE statements needed
- All existing data remains valid

### Settings Cleanup (Optional)
The `auto_fix_threshold` setting is no longer used but can remain in the database without causing issues. To remove it:

```sql
DELETE FROM settings WHERE key = 'auto_fix_threshold';
```

## Future Enhancements

### Potential Features
1. **Auto-reopen threshold**: If X users mark as "Still Broken", automatically reopen the report
2. **Verification badge**: Show "Community Verified" badge on reports with high ✅ count
3. **Fix quality score**: Calculate percentage of ✅ vs ❌ reactions
4. **Notification**: Alert report owner if multiple users mark as "Still Broken"

## Rollback Plan

If needed, to revert to old behavior:

1. Remove `if not report.is_fixed:` check in `react_to_report()`
2. Restore auto-fix logic in the same function
3. Change map.html: `const reactionsHtml = it.is_fixed ? '' : ...`
4. Revert my_reports.html to always show reactions
5. Change icons back to 👍/👎

All data will remain intact during rollback.
