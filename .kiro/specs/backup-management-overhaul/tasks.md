# Implementation Plan: Backup Management Overhaul

## Overview

This plan implements a comprehensive overhaul of the Backup Management system in Surveyor.AI. The implementation adds database schema migrations, creates a secure scheduled backup API endpoint, implements GitHub Actions workflows for automated backups, enhances the manual backup flow, improves the restore process with pre-restore preservation, and redesigns the UI with side-by-side Export/Restore sections and an enhanced history table with type filtering.

## Tasks

- [x] 1. Add created_at columns to User and AuditLog models with startup migrations
  - Add `created_at` column to `User` model with default `lambda: int(time.time())`
  - Add `created_at` column to `AuditLog` model with default `lambda: int(time.time())`
  - Implement `_run_startup_migrations()` function with safe ALTER TABLE statements
  - Backfill existing `user` rows with `created_at = 0`
  - Backfill existing `audit_log` rows with `created_at = timestamp`
  - Call `_run_startup_migrations()` in app startup context
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [ ]* 1.1 Write property test for startup migrations idempotency
  - **Property 19: Startup migrations are idempotent with correct backfill**
  - **Validates: Requirements 11.3, 11.4**

- [ ]* 1.2 Write property test for new model instance timestamps
  - **Property 20: New model instances get current Unix timestamp for created_at**
  - **Validates: Requirements 11.5, 11.6**

- [x] 2. Implement backup API key seeding and authentication
  - Implement `_seed_backup_api_key()` function to read `BACKUP_API_KEY` env var or generate `secrets.token_hex(32)`
  - Upsert `backup_api_key` into Settings table if not present
  - Call `_seed_backup_api_key()` at app startup
  - Add Settings keys: `last_daily_backup_ts`, `last_monthly_backup_ts` (initialized to 0)
  - _Requirements: 9.2, 2.4, 3.4_

- [ ]* 2.1 Write property test for API key seeding
  - **Property 18: API key seeding**
  - **Validates: Requirements 9.2**

- [x] 3. Create /api/backups/scheduled endpoint with authentication
  - Create POST route `/api/backups/scheduled` (no `_require_admin()`)
  - Validate `X-Backup-Api-Key` header against `backup_api_key` in Settings
  - Return HTTP 401 if key missing or incorrect
  - Parse JSON body for `type` field (`"daily"` or `"monthly"`)
  - Return HTTP 400 if `type` invalid
  - Exempt endpoint from `_block_writes_during_restore` middleware
  - Acquire `BACKUP_LOCK` non-blocking; return HTTP 409 if locked
  - _Requirements: 9.1, 9.5, 2.8_

- [ ]* 3.1 Write property test for API key auth rejection
  - **Property 1: API key auth rejection**
  - **Validates: Requirements 2.8, 9.1**

- [x] 4. Implement daily incremental backup logic
  - Read `last_daily_backup_ts` from Settings (default 0)
  - Query 7 tables (`report`, `detection`, `reaction`, `report_flag`, `notification`, `user`, `audit_log`) for rows where `created_at > last_daily_backup_ts`
  - If no rows found: log `{backup_type: "daily", status: "success", note: "no_new_data"}`, return HTTP 200
  - Create temp SQLite file with schema and filtered rows
  - Upload to B2 as `incremental_YYYYMMDD_HHMMSS.db`
  - Update `last_daily_backup_ts` in Settings to current timestamp
  - Log `{backup_type: "daily", operation: "export", status: "success", filename: "..."}`
  - Handle B2 not configured: return HTTP 503 with error log
  - _Requirements: 2.3, 2.4, 2.5, 2.6, 2.7_

- [ ]* 4.1 Write property test for incremental backup row filtering
  - **Property 2: Incremental backup row filtering**
  - **Validates: Requirements 2.3, 11.7**

- [ ]* 4.2 Write property test for scheduled backup logging
  - **Property 3: Scheduled backup always logs with correct type**
  - **Validates: Requirements 2.5, 3.5**

- [ ]* 4.3 Write property test for successful scheduled backup updates
  - **Property 4: Successful scheduled backup updates filename and timestamp**
  - **Validates: Requirements 2.4, 3.4**

- [x] 5. Implement monthly full backup logic
  - Create full SQLite online backup to temp file
  - Upload to B2 as `full_YYYYMMDD_HHMMSS.db`
  - Update `last_monthly_backup_ts` in Settings
  - Log `{backup_type: "monthly", operation: "export", status: "success", filename: "..."}`
  - Handle B2 not configured: return HTTP 503 with error log
  - _Requirements: 3.3, 3.4, 3.5, 3.6_

- [ ]* 5.1 Write property test for monthly backup validity
  - **Property 5: Monthly backup produces valid full SQLite copy**
  - **Validates: Requirements 3.3**

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Create /admin/backups/manual endpoint
  - Create POST route `/admin/backups/manual` with `_require_admin()` and CSRF validation
  - Acquire `BACKUP_LOCK` non-blocking; return HTTP 409 if locked
  - Check B2 credentials exist; return HTTP 400 if not configured
  - Create full SQLite online backup as `manual_YYYYMMDD_HHMMSS.db`
  - Save to `BACKUP_DIR` locally
  - Upload to B2
  - Log `{backup_type: "manual", operation: "export", status: "success/failure", filename: "..."}`
  - Return JSON response
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ]* 7.1 Write property test for manual backup dual save
  - **Property 6: Manual backup saves to both BACKUP_DIR and B2**
  - **Validates: Requirements 4.1**

- [ ]* 7.2 Write property test for manual backup logging
  - **Property 7: Manual backup always logs**
  - **Validates: Requirements 4.2, 4.3**

- [ ]* 7.3 Write property test for concurrent backup lock
  - **Property 8: Concurrent backup lock returns 409**
  - **Validates: Requirements 4.5**

- [x] 8. Update /admin/backups/import (restore) endpoint
  - Preserve pre-restore DB as `instance/users.db.before_restore_<ts>` before overwriting
  - Update log call to include `backup_type="restore"`
  - Call `write_audit_log('BACKUP_RESTORED', ...)` with filename and actor user ID
  - Ensure validation gates overwrite (existing `_validate_backup_db` check)
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [ ]* 8.1 Write property test for restore validation
  - **Property 9: Restore validation gates overwrite**
  - **Validates: Requirements 5.1, 5.4**

- [ ]* 8.2 Write property test for restore logging
  - **Property 10: Restore always logs with backup_type "restore"**
  - **Validates: Requirements 5.2**

- [ ]* 8.3 Write property test for restore audit log
  - **Property 11: Restore always writes audit log entry**
  - **Validates: Requirements 5.3**

- [ ]* 8.4 Write property test for pre-restore DB preservation
  - **Property 12: Pre-restore DB is preserved before overwrite**
  - **Validates: Requirements 5.5**

- [x] 9. Fix settings_page B2 connection check
  - Ensure all B2 SDK calls wrapped in try/except
  - Set `b2_connected = False` on any exception (including BucketNotFound, network errors)
  - Do not re-raise exceptions to user
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ]* 9.1 Write property test for B2 credentials storage
  - **Property 21: B2 credentials stored on connect**
  - **Validates: Requirements 1.1**

- [ ]* 9.2 Write property test for B2 disconnect
  - **Property 22: B2 disconnect removes all credential keys**
  - **Validates: Requirements 1.4**

- [x] 10. Update admin_backups_page to derive backup_type for history
  - Read history via `_backup_log_read(50)`
  - For each entry: if `backup_type` missing, derive from `operation` (`"export"` → `"manual"`, `"import"` → `"restore"`)
  - Pass `backup_type` to template for each history item
  - _Requirements: 6.2, 6.3_

- [ ]* 10.1 Write property test for type label derivation
  - **Property 13: Type label derivation is correct**
  - **Validates: Requirements 6.2, 6.3**

- [ ] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Update backup_management.html UI layout
  - Wrap Export and Restore sections in `<div class="backup-panels">` flex container
  - Add "Manual Backup" button in Export section (AJAX POST to `/admin/backups/manual`)
  - Add filter buttons row above history table (`All`, `Daily`, `Monthly`, `Manual`, `Restore`)
  - Add `Type` column to history table
  - Add "No New Data" badge logic in Status column (when `status == "success"` and `note == "no_new_data"`)
  - Wrap history table in `<div class="history-container">` (already exists, verify max-height: 400px)
  - _Requirements: 10.1, 10.3, 10.4, 10.5, 6.1, 6.4, 6.5, 6.6, 6.7, 6.8_

- [ ]* 12.1 Write unit test for No New Data badge rendering
  - **Property 14: No New Data badge rendering**
  - **Validates: Requirements 6.7**

- [x] 13. Update backups.css for side-by-side layout
  - Add `.backup-panels` with `display: flex; gap: 24px;`
  - Each `.backup-section` inside panels: `flex: 1 1 50%`
  - Add `@media (max-width: 768px)` with `.backup-panels { flex-direction: column; }`
  - Add `.type-badge` pill badge styles for Daily/Monthly/Manual/Restore
  - Add `.badge-no-new-data` distinct style
  - Add `.filter-btn` and `.filter-btn.active` styles
  - _Requirements: 10.1, 10.2_

- [x] 14. Fix download route and button visibility
  - Verify `/admin/backups/download/<filename>` uses `secure_filename()` before path construction
  - Verify `send_file` with `as_attachment=True`
  - Verify template renders Download button only when `can_download == True`
  - Return HTTP 404 if file does not exist
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ]* 14.1 Write property test for download route attachment
  - **Property 15: Download route serves file as attachment**
  - **Validates: Requirements 7.1**

- [ ]* 14.2 Write property test for download button visibility
  - **Property 16: Download button only shown when can_download is True**
  - **Validates: Requirements 7.2**

- [ ]* 14.3 Write property test for secure_filename sanitization
  - **Property 17: secure_filename sanitizes path traversal**
  - **Validates: Requirements 7.4**

- [x] 15. Create GitHub Actions daily backup workflow
  - Create `.github/workflows/daily_backup.yml`
  - Add `schedule` trigger with cron `0 2 * * *`
  - Add `workflow_dispatch` trigger
  - Add curl step: POST to `${{ secrets.APP_BASE_URL }}/api/backups/scheduled` with `X-Backup-Api-Key: ${{ secrets.BACKUP_API_KEY }}` and body `{"type":"daily"}`
  - Use `--fail` flag so curl exits non-zero on non-2xx
  - _Requirements: 2.1, 2.2, 9.3, 9.4_

- [x] 16. Create GitHub Actions monthly backup workflow
  - Create `.github/workflows/monthly_backup.yml`
  - Add `schedule` trigger with cron `0 3 1 * *`
  - Add `workflow_dispatch` trigger
  - Add curl step: POST to `${{ secrets.APP_BASE_URL }}/api/backups/scheduled` with `X-Backup-Api-Key: ${{ secrets.BACKUP_API_KEY }}` and body `{"type":"monthly"}`
  - Use `--fail` flag
  - _Requirements: 3.1, 3.2, 9.3, 9.4_

- [ ] 17. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The design uses Python (Flask), so all implementation is in Python
- GitHub Actions workflows use curl to trigger the scheduled backup endpoint
- The `/api/backups/scheduled` endpoint is authenticated via `X-Backup-Api-Key` header (not session-based auth)
- All backup operations are guarded by `BACKUP_LOCK` to prevent concurrent runs
