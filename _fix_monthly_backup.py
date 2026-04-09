#!/usr/bin/env python3
"""One-shot script to fix the broken _run_monthly_full_backup() in app.py"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The broken section: from the function def up to (but not including) the @app.route line
OLD_FUNC_START = 'def _run_monthly_full_backup():'
ROUTE_MARKER = "@app.route('/api/backups/scheduled', methods=['POST'])"

start_idx = content.find(OLD_FUNC_START)
end_idx = content.find(ROUTE_MARKER)

if start_idx == -1:
    raise RuntimeError("Could not find _run_monthly_full_backup function")
if end_idx == -1:
    raise RuntimeError("Could not find @app.route('/api/backups/scheduled')")

NEW_FUNC = '''def _run_monthly_full_backup():
    now_ts = int(time.time())
    temp_path = None
    try:
        def _get_b2_setting(k):
            s = Settings.query.filter_by(key=k).first()
            return s.value if s and s.value else None

        key_id = _get_b2_setting('b2_key_id')
        app_key = _get_b2_setting('b2_app_key')
        bucket_name = _get_b2_setting('b2_bucket_name')

        if not key_id or not app_key or not bucket_name:
            _backup_log_append({
                'user': 'system', 'operation': 'export', 'backup_type': 'monthly',
                'filename': None, 'timestamp': now_ts, 'status': 'failure',
                'error': 'B2 not configured'
            })
            return {'success': False, 'message': 'B2 not configured', 'status_code': 503}

        backup_name = f'full_{time.strftime("%Y%m%d_%H%M%S")}.db'
        os.makedirs(BACKUP_DIR, exist_ok=True)
        temp_path = os.path.join(BACKUP_DIR, backup_name)

        src = sqlite3.connect(_get_db_path())
        dst = sqlite3.connect(temp_path)
        src.backup(dst)
        dst.close()
        src.close()

        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account('production', key_id, app_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)
        bucket.upload_local_file(
            local_file=temp_path,
            file_name=backup_name,
            file_infos={'author': 'system', 'backup_type': 'monthly'}
        )

        s = Settings.query.filter_by(key='last_monthly_backup_ts').first()
        if s:
            s.value = str(now_ts)
        else:
            db.session.add(Settings(key='last_monthly_backup_ts', value=str(now_ts)))
        db.session.commit()

        _backup_log_append({
            'user': 'system', 'operation': 'export', 'backup_type': 'monthly',
            'filename': backup_name, 'timestamp': now_ts, 'status': 'success'
        })

        return {'success': True, 'message': f'Monthly full backup completed: {backup_name}'}

    except Exception as e:
        _backup_log_append({
            'user': 'system', 'operation': 'export', 'backup_type': 'monthly',
            'filename': None, 'timestamp': now_ts, 'status': 'failure', 'error': str(e)
        })
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return {'success': False, 'message': str(e), 'status_code': 500}


'''

new_content = content[:start_idx] + NEW_FUNC + content[end_idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done. Replaced _run_monthly_full_backup() successfully.")
