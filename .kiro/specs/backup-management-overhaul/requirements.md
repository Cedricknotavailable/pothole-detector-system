# Requirements Document

## Introduction

This feature is a comprehensive overhaul of the Backup Management system in Surveyor.AI, a Flask/SQLite web application. The overhaul addresses a broken Backblaze B2 connection, introduces recurring automated backups driven by GitHub Actions (daily incremental and monthly full) so backups run even when the Flask server is offline, adds a manual backup trigger, improves the restore workflow with audit logging, redesigns the backup history table with type columns and filtering, fixes the Download button, and restructures the UI so the Export and Restore sections sit side-by-side in a single horizontal container above the history table.

## Glossary

- **Backup_System**: The combined backend and frontend responsible for creating, storing, and restoring database backups.
- **B2_Client**: The Backblaze B2 SDK integration (`b2sdk.v2`) used to authenticate and transfer files to/from the B2 bucket.
- **GitHub_Actions_Scheduler**: A GitHub Actions workflow that triggers recurring backup jobs via scheduled cron expressions, ensuring backups run even when the Flask server is offline.
- **Backup_Endpoint**: A Flask route (`/api/backups/scheduled`) that accepts authenticated requests from GitHub Actions to trigger daily or monthly backup operations.
- **Incremental_Backup**: A backup that captures only database rows created or modified since the last successful daily backup, identified by comparing row timestamps against the `last_daily_backup_ts` setting.
- **Full_Backup**: A complete copy of the SQLite `users.db` file produced using SQLite's online backup API.
- **Backup_Log**: The `backup_history.log` JSON-lines file appended to by `_backup_log_append()` and read by `_backup_log_read()`.
- **Backup_Type**: A classification tag attached to every log entry — one of `daily`, `monthly`, `manual`, or `restore`.
- **Admin**: An authenticated user with the `admin` role, as enforced by `_require_admin()`.
- **Settings_Table**: The SQLAlchemy `Settings` model storing key/value pairs, including B2 credentials and scheduler state.
- **BACKUP_DIR**: The `backups/` directory at the application root where local backup files are stored.
- **BACKUP_API_KEY**: A secret token stored in GitHub Secrets and the Settings_Table, used to authenticate scheduled backup requests from GitHub Actions.

---

## Requirements

### Requirement 1: Fix Backblaze B2 Connection

**User Story:** As an Admin, I want the Backblaze B2 connection status to reflect the actual credential state, so that I can trust the "Connected / Not Connected" indicator in Settings.

#### Acceptance Criteria

1. WHEN the Admin submits valid B2 credentials via `/settings/b2/connect`, THE B2_Client SHALL authenticate against the Backblaze production endpoint and store `b2_key_id`, `b2_app_key`, and `b2_bucket_name` in the Settings_Table before returning a success response.
2. WHEN the Admin loads the Settings page and valid credentials exist in the Settings_Table, THE B2_Client SHALL perform a live authorization check and THE Settings page SHALL display "Connected" status.
3. IF the B2_Client authorization check fails for any reason (invalid key, network error, bucket not found), THEN THE Settings page SHALL display "Not Connected" status without throwing an unhandled exception.
4. WHEN the Admin disconnects B2 via `/settings/b2/disconnect`, THE Backup_System SHALL remove all three credential keys from the Settings_Table and THE Settings page SHALL display "Not Connected" status.

---

### Requirement 2: Daily Incremental Backup via GitHub Actions

**User Story:** As an Admin, I want the system to automatically run a daily incremental backup triggered by GitHub Actions, so that only new data since the last backup is uploaded to Backblaze B2 — even when the Flask server is offline.

#### Acceptance Criteria

1. A GitHub Actions workflow file (`.github/workflows/daily_backup.yml`) SHALL be created with a `schedule` trigger using cron `0 2 * * *` (daily at 02:00 UTC) and a `workflow_dispatch` trigger for manual runs.
2. WHEN the GitHub Actions daily workflow runs, it SHALL send an authenticated HTTP POST request to the deployed app's `/api/backups/scheduled` endpoint with `{"type": "daily"}` in the request body and a `X-Backup-Api-Key` header containing the `BACKUP_API_KEY` secret.
3. WHEN the `/api/backups/scheduled` endpoint receives a valid `daily` request, THE Backup_System SHALL query the following tables for rows newer than `last_daily_backup_ts` — `report`, `detection`, `reaction`, `report_flag`, `notification`, `user` (using `created_at`), and `audit_log` (using `created_at`) — all of which will have a `created_at` column after the migration in Requirement 11.
4. WHEN the daily incremental backup completes successfully, THE Backup_System SHALL upload the incremental backup file to the B2 bucket with a filename matching the pattern `incremental_YYYYMMDD_HHMMSS.db` and SHALL update the `last_daily_backup_ts` Settings_Table key to the current UTC timestamp.
5. WHEN the daily incremental backup completes (success or failure), THE Backup_System SHALL append an entry to the Backup_Log with `backup_type` set to `"daily"`, `operation` set to `"export"`, `status` set to `"success"` or `"failure"`, and the current timestamp.
6. IF B2 credentials are not configured when the daily job runs, THE Backup_System SHALL log a `"failure"` entry with `backup_type` `"daily"` and a descriptive `error` field and SHALL return HTTP 503.
7. IF no rows have been created or modified since `last_daily_backup_ts`, THE Backup_System SHALL log a `"success"` entry with `backup_type` set to `"daily"`, `status` set to `"success"`, and a `note` field set to `"no_new_data"` — and SHALL skip the B2 upload. This entry SHALL be visible in the history table with a "No New Data" label in the Status column.
8. IF the `X-Backup-Api-Key` header is missing or does not match the stored `BACKUP_API_KEY`, THE Backup_System SHALL return HTTP 401 and SHALL NOT perform any backup operation.

---

### Requirement 3: Monthly Full Backup via GitHub Actions

**User Story:** As an Admin, I want the system to automatically run a monthly full backup triggered by GitHub Actions, so that a complete snapshot of the database is stored in Backblaze B2 each month — even when the Flask server is offline.

#### Acceptance Criteria

1. A GitHub Actions workflow file (`.github/workflows/monthly_backup.yml`) SHALL be created with a `schedule` trigger using cron `0 3 1 * *` (1st of each month at 03:00 UTC) and a `workflow_dispatch` trigger for manual runs.
2. WHEN the GitHub Actions monthly workflow runs, it SHALL send an authenticated HTTP POST request to the deployed app's `/api/backups/scheduled` endpoint with `{"type": "monthly"}` in the request body and a `X-Backup-Api-Key` header.
3. WHEN the `/api/backups/scheduled` endpoint receives a valid `monthly` request, THE Backup_System SHALL create a full copy of `instance/users.db` using the SQLite online backup API.
4. WHEN the monthly full backup completes successfully, THE Backup_System SHALL upload the file to the B2 bucket with a filename matching the pattern `full_YYYYMMDD_HHMMSS.db` and SHALL update the `last_monthly_backup_ts` Settings_Table key to the current UTC timestamp.
5. WHEN the monthly full backup completes (success or failure), THE Backup_System SHALL append an entry to the Backup_Log with `backup_type` set to `"monthly"`, `operation` set to `"export"`, and the appropriate `status`.
6. IF B2 credentials are not configured when the monthly job runs, THE Backup_System SHALL log a `"failure"` entry with `backup_type` `"monthly"` and a descriptive `error` field and SHALL return HTTP 503.

---

### Requirement 4: Manual Backup

**User Story:** As an Admin, I want to trigger a manual backup on demand, so that I can create an immediate full backup before making significant changes.

#### Acceptance Criteria

1. WHEN the Admin clicks the "Manual Backup" button on the Backup Management page, THE Backup_System SHALL create a full copy of `instance/users.db` using the SQLite online backup API and SHALL save it to both the local `BACKUP_DIR` directory and upload it to the B2 bucket with a filename matching the pattern `manual_YYYYMMDD_HHMMSS.db`.
2. WHEN the manual backup completes successfully, THE Backup_System SHALL append an entry to the Backup_Log with `backup_type` set to `"manual"`, `operation` set to `"export"`, `status` set to `"success"`, and the `filename` field set to the local backup filename.
3. IF the manual backup fails for any reason, THEN THE Backup_System SHALL append a `"failure"` log entry with `backup_type` `"manual"` and SHALL return a JSON error response with HTTP 500.
4. IF B2 credentials are not configured when the Admin triggers a manual backup, THEN THE Backup_System SHALL return a JSON error response indicating B2 is not configured and SHALL NOT create a local backup file.
5. WHILE a backup operation is already in progress (BACKUP_LOCK is held), THE Backup_System SHALL return a JSON error response with HTTP 409 and SHALL NOT start a second concurrent backup.

---

### Requirement 5: Restore from Backup

**User Story:** As an Admin, I want to restore the database from a backup file, so that I can recover from data loss or corruption.

#### Acceptance Criteria

1. WHEN the Admin submits a restore request via the Restore section, THE Backup_System SHALL validate the uploaded file is a valid SQLite database containing the required tables (`user`, `report`, `detection`) before overwriting `instance/users.db`.
2. WHEN a restore operation completes successfully, THE Backup_System SHALL append an entry to the Backup_Log with `backup_type` set to `"restore"`, `operation` set to `"import"`, `status` set to `"success"`, and the `user` field set to the Admin's username.
3. WHEN a restore operation completes successfully, THE Backup_System SHALL write an audit log entry via `write_audit_log('BACKUP_RESTORED', ...)` including the filename and the Admin's user ID.
4. IF the uploaded file fails validation (not a valid SQLite file or missing required tables), THEN THE Backup_System SHALL return a JSON error response and SHALL NOT overwrite the current database.
5. IF a restore operation fails after the database has been partially overwritten, THEN THE Backup_System SHALL preserve the pre-restore database file at `instance/users.db.before_restore_<timestamp>` and SHALL log a `"failure"` entry with `backup_type` `"restore"`.

---

### Requirement 6: Backup History Table with Type Columns and Filtering

**User Story:** As an Admin, I want the backup history table to show the backup type and status for each entry and allow filtering by type, so that I can quickly find specific backup events.

#### Acceptance Criteria

1. THE Backup_System SHALL render the backup history table with the following columns: Timestamp, Type, Filename, User, Status, and Actions.
2. THE Backup_System SHALL display the `backup_type` field from each Backup_Log entry in the Type column, using one of the labels: `Daily`, `Monthly`, `Manual`, or `Restore`.
3. WHEN a Backup_Log entry has no `backup_type` field (legacy entries), THE Backup_System SHALL derive the type from the `operation` field: `"export"` maps to `"Manual"` and `"import"` maps to `"Restore"`.
4. THE Backup_Management page SHALL render filter buttons labeled `All`, `Daily`, `Monthly`, `Manual`, and `Restore` above the history table.
5. WHEN the Admin clicks a filter button, THE Backup_Management page SHALL show only history rows whose `backup_type` matches the selected filter without a full page reload (client-side filtering).
6. WHEN the `All` filter is active, THE Backup_Management page SHALL display all history rows regardless of type.
7. WHEN a Backup_Log entry has `status` set to `"success"` and `note` set to `"no_new_data"`, THE Backup_Management page SHALL display a distinct "No New Data" badge in the Status column (styled differently from the standard "Success" badge) to clearly indicate the backup ran but found nothing to upload.
8. THE history table SHALL always show an entry for every scheduled run — including "No New Data" runs — so the Admin has a complete audit trail of when each backup job executed.

---

### Requirement 7: Fix Download Button

**User Story:** As an Admin, I want the Download button in the history table to correctly download the associated backup file, so that I can retrieve local backups.

#### Acceptance Criteria

1. WHEN the Admin clicks the Download button for a history entry, THE Backup_System SHALL serve the file from BACKUP_DIR via the `/admin/backups/download/<filename>` route using `send_file` with `as_attachment=True`.
2. THE Backup_Management page SHALL render the Download button only for history entries where `can_download` is `True` (the file exists in BACKUP_DIR).
3. IF the requested file does not exist in BACKUP_DIR, THEN THE Backup_System SHALL return HTTP 404.
4. THE `/admin/backups/download/<filename>` route SHALL use `secure_filename()` to sanitize the path parameter before constructing the file path, preventing directory traversal.

---

### Requirement 9: GitHub Actions Secrets and Scheduled Backup Endpoint

**User Story:** As an Admin, I want the GitHub Actions workflows to securely authenticate with the deployed app, so that scheduled backups cannot be triggered by unauthorized parties.

#### Acceptance Criteria

1. THE Backup_System SHALL expose a `/api/backups/scheduled` POST endpoint that accepts a JSON body with a `type` field (`"daily"` or `"monthly"`) and validates the `X-Backup-Api-Key` request header against the `backup_api_key` value stored in the Settings_Table.
2. THE `backup_api_key` SHALL be seeded into the Settings_Table on first app startup using a value read from the `BACKUP_API_KEY` environment variable; if the environment variable is absent, a random 32-byte hex token SHALL be generated and stored.
3. THE GitHub Actions workflow files SHALL reference the following GitHub Secrets: `APP_BASE_URL` (the deployed app's base URL, e.g. `https://myapp.onrender.com`) and `BACKUP_API_KEY` (the same token stored in the Settings_Table).
4. THE GitHub Actions workflows SHALL fail the workflow run (non-zero exit) if the HTTP response from `/api/backups/scheduled` is not HTTP 200, so that failures are visible in the GitHub Actions dashboard.
5. THE `/api/backups/scheduled` endpoint SHALL be exempt from the `_block_writes_during_restore` middleware so that it can always respond to GitHub Actions health checks.

---

### Requirement 10: UI Layout — Side-by-Side Export and Restore, History Below

**User Story:** As an Admin, I want the Export and Restore sections to appear side by side in a single horizontal container, with the backup history table below, so that the page does not require excessive scrolling.

#### Acceptance Criteria

1. THE Backup_Management page SHALL render the Export section and the Restore section inside a single horizontal flex container, each occupying 50% of the available width on viewports wider than 768 px.
2. WHEN the viewport width is 768 px or less, THE Backup_Management page SHALL stack the Export section and the Restore section vertically (full width each).
3. THE Backup_Management page SHALL render the backup history table in a separate section below the horizontal Export/Restore container.
4. THE Backup_Management page SHALL constrain the history table to a maximum height of 400 px with vertical scrolling, so that the page body does not grow unboundedly with many log entries.
5. THE Backup_Management page SHALL include a "Manual Backup" button in the Export section that triggers the manual backup endpoint via an AJAX POST request.

---

### Requirement 11: Add `created_at` to User and AuditLog Models

**User Story:** As a Developer, I want the `user` and `audit_log` tables to have a `created_at` column, so that new user registrations and audit events are included in daily incremental backups and can be tracked chronologically.

#### Acceptance Criteria

1. THE `User` SQLAlchemy model SHALL have a `created_at` column of type `Integer`, non-nullable, with a default of `lambda: int(time.time())`.
2. THE `AuditLog` SQLAlchemy model SHALL have a `created_at` column of type `Integer`, non-nullable, with a default of `lambda: int(time.time())`. This is a dedicated creation timestamp separate from the existing `timestamp` column (which records when the audited action occurred).
3. WHEN the app starts, THE Backup_System SHALL run a safe migration that executes `ALTER TABLE user ADD COLUMN created_at INTEGER` if the column does not already exist, backfilling existing rows with the value `0` as a sentinel for "unknown creation time".
4. WHEN the app starts, THE Backup_System SHALL run a safe migration that executes `ALTER TABLE audit_log ADD COLUMN created_at INTEGER` if the column does not already exist, backfilling existing rows with the value of the existing `timestamp` column so legacy entries retain their original time.
5. WHEN a new `User` record is created, THE `created_at` field SHALL be set to the current Unix timestamp automatically via the model default.
6. WHEN a new `AuditLog` record is created, THE `created_at` field SHALL be set to the current Unix timestamp automatically via the model default.
7. THE daily incremental backup SHALL include `user` rows where `created_at > last_daily_backup_ts` and `audit_log` rows where `created_at > last_daily_backup_ts`, in addition to the other tables listed in Requirement 2.
