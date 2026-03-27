# Moderator Unsure Detection Access Implementation

## Summary
Moderators now have full access to the "unsure" detection filter and can verify/review unsure detections, just like admins.

## Changes Made

### Backend (app.py)

1. **defects_page route** (Line ~2620)
   - Added `is_admin_or_moderator` variable
   - Passed `is_admin_or_moderator` to template

2. **map_page route** (Line ~2122)
   - Added `is_admin_or_moderator` variable
   - Passed `is_admin_or_moderator` to template

3. **review_detection route** (Line ~2928)
   - Changed from `_require_admin()` to `_require_admin_or_moderator()`
   - Moderators can now review detections (confirm/reject)

4. **detections_api route** (Line ~2844)
   - Added `is_admin_or_moderator` check
   - Changed `allow_pending` logic to use `is_admin_or_moderator`
   - Moderators can now fetch pending detections

### Frontend Templates

#### templates/defects.html
1. **Category filter dropdown**
   - Changed `{% if is_admin %}` to `{% if is_admin_or_moderator %}`
   - Unsure option now visible to moderators

2. **Unsure status sub-filter**
   - Wrapped in `{% if is_admin_or_moderator %}` block
   - Moderators can filter by validated/unvalidated/rejected status

#### templates/map.html
1. **JavaScript constants**
   - Added `IS_ADMIN_OR_MODERATOR` constant
   - Set based on backend `is_admin_or_moderator` variable

2. **Type filter buttons**
   - Changed condition from `is_admin` to `is_admin_or_moderator`
   - Unsure button now visible to moderators

3. **Mobile type filter dropdown**
   - Changed condition from `is_admin` to `is_admin_or_moderator`
   - Unsure option now available on mobile

4. **Active filters initialization**
   - Changed `if (IS_ADMIN)` to `if (IS_ADMIN_OR_MODERATOR)`
   - Unsure type added to default filters for moderators

5. **Mobile filter event handler**
   - Changed `if (IS_ADMIN)` to `if (IS_ADMIN_OR_MODERATOR)`
   - Unsure type included when "All Types" selected

6. **Detection popup actions**
   - Changed `(IS_ADMIN && pending)` to `(IS_ADMIN_OR_MODERATOR && pending)`
   - Review buttons (confirm/reject) now shown to moderators

7. **reviewDetection function**
   - Changed `if (!IS_ADMIN)` to `if (!IS_ADMIN_OR_MODERATOR)`
   - Moderators can execute review actions

8. **fetchDetections function**
   - Changed `IS_ADMIN ? '/detections?include_pending=1'` to `IS_ADMIN_OR_MODERATOR ? '/detections?include_pending=1'`
   - Moderators can fetch pending detections

## Functionality Enabled for Moderators

1. **View unsure detections** - Can filter by "Unsure (AI)" category in both map and defects pages
2. **Filter unsure status** - Can filter by validated/unvalidated/rejected status
3. **Review detections** - Can confirm detections as pothole or road crack
4. **Reject detections** - Can reject false positive detections
5. **Access pending detections** - Can view detections awaiting review

## Testing

Created `test_moderator_unsure_access.py` with comprehensive tests:
- ✓ Moderator can access unsure filter in defects page
- ✓ Moderator can access unsure filter in map page
- ✓ Moderator can review detections
- ✓ Moderator can fetch pending detections

All tests passed successfully.

## User Impact

Moderators can now:
- Help verify AI-detected road defects
- Reduce admin workload by sharing review responsibilities
- Improve data quality by validating or rejecting uncertain detections
- Access the same unsure detection tools as admins
