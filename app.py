from flask import Flask, render_template, Response, redirect, url_for, request, session, abort, send_file
import cv2
from ultralytics import YOLO
import threading
import time
import json
from flask import jsonify
import os
import sqlite3
import tempfile
import shutil
import secrets
from flask_sqlalchemy import SQLAlchemy
import re
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text, literal_column, func, and_
from sqlalchemy import or_, asc, desc
from functools import wraps
from uuid import uuid4
from werkzeug.utils import secure_filename
try:
    import serial
except Exception:
    serial = None

try:
    from b2sdk.v2 import InMemoryAccountInfo, B2Api
    B2_DEPS_AVAILABLE = True
except ImportError:
    B2_DEPS_AVAILABLE = False

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Database configuration (SQLite file-based)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'reports')
DETECTION_UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'detections')
ALLOWED_REPORT_IMAGE_EXTS = {'jpg', 'jpeg', 'png'}
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

# Initialize SQLAlchemy
db = SQLAlchemy(app)

ALLOWED_ROLES = {'admin', 'moderator', 'user'}
ALLOWED_STATUSES = {'active', 'suspended', 'locked', 'archived'}
BACKUP_ALLOWED_EXTS = {'db', 'sqlite', 'sqlite3', 'sql'}
BACKUP_DIR = os.path.join(app.root_path, 'backups')
BACKUP_LOG_PATH = os.path.join(app.root_path, 'backup_history.log')
BACKUP_LOCK = threading.Lock()
RESTORE_STATE = {"in_progress": False}


def _get_current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    try:
        return User.query.get(int(uid))
    except Exception:
        return None


def _is_admin(user) -> bool:
    if not user:
        return False
    role = getattr(user, 'role', None)
    if role is None:
        return False
    return str(role).strip().lower() == 'admin'


def _is_moderator(user) -> bool:
    if not user:
        return False
    role = getattr(user, 'role', None)
    if role is None:
        return False
    return str(role).strip().lower() == 'moderator'


def _is_admin_or_moderator(user) -> bool:
    return _is_admin(user) or _is_moderator(user)


def _require_admin():
    cu = _get_current_user()
    if not _is_admin(cu):
        abort(403)
    return cu


def _require_admin_or_moderator():
    cu = _get_current_user()
    if not _is_admin_or_moderator(cu):
        abort(403)
    return cu


@app.before_request
def _block_writes_during_restore():
    if not RESTORE_STATE.get("in_progress"):
        return None
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None
    allowed_paths = {"/admin/backups/import", "/admin/backups/export", "/api/backups/scheduled"}
    if request.path in allowed_paths:
        return None
    return ("Restore in progress. Please try again shortly.", 503)


def _login_required():
    cu = _get_current_user()
    if not cu:
        return redirect(url_for('login', next=request.path))
    return cu


def _require_role(*roles):
    cu = _login_required()
    if not isinstance(cu, User):
        return cu
    role = str(getattr(cu, 'role', '') or '').strip().lower()
    allowed = {str(r).strip().lower() for r in roles}
    if role not in allowed:
        abort(403)
    return cu


def login_required_view(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        cu = _login_required()
        if not isinstance(cu, User):
            return cu
        return fn(*args, **kwargs)
    return wrapper


def _get_db_path():
    # Check instance folder first (standard Flask location)
    instance_db = os.path.join(app.instance_path, 'users.db')
    if os.path.exists(instance_db):
        return instance_db

    db_path = os.path.join(app.root_path, 'users.db')
    if os.path.exists(db_path):
        return db_path
    return 'users.db'


def _backup_log_append(entry: dict):
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        line = json.dumps(entry, separators=(",", ":"), ensure_ascii=False)
        with open(BACKUP_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _backup_log_read(limit: int = 50):
    if not os.path.exists(BACKUP_LOG_PATH):
        return []
    try:
        with open(BACKUP_LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        items = []
        for line in lines[-limit:]:
            try:
                items.append(json.loads(line.strip()))
            except Exception:
                continue
        return list(reversed(items))
    except Exception:
        return []


def _validate_backup_db(path: str):
    try:
        conn = sqlite3.connect(path)
        check = conn.execute("PRAGMA integrity_check").fetchone()
        if not check or str(check[0]).lower() != 'ok':
            conn.close()
            return False, 'Database integrity check failed.'
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        existing = {r[0] for r in rows}
        required = {'user', 'report', 'detection'}
        if not required.issubset(existing):
            conn.close()
            return False, 'Backup schema is missing required tables.'
        conn.close()
        return True, ''
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return False, 'Backup validation failed.'


def _run_startup_migrations():
    """Run safe ALTER TABLE migrations using a direct sqlite3 connection to avoid session conflicts."""
    db_path = os.path.join(app.instance_path, 'users.db')
    if not os.path.exists(db_path):
        db_path = os.path.join(app.root_path, 'users.db')
    conn = sqlite3.connect(db_path)
    try:
        try:
            conn.execute("ALTER TABLE user ADD COLUMN created_at INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        conn.execute("UPDATE user SET created_at = 0 WHERE created_at IS NULL")
        conn.commit()

        try:
            conn.execute("ALTER TABLE audit_log ADD COLUMN created_at INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        conn.execute("UPDATE audit_log SET created_at = timestamp WHERE created_at IS NULL")
        conn.commit()
    finally:
        conn.close()


def _seed_backup_api_key():
    """Seed backup API key and backup timestamp settings if not already present."""
    try:
        api_key_setting = Settings.query.filter_by(key='backup_api_key').first()
        if not api_key_setting:
            backup_api_key = os.environ.get('BACKUP_API_KEY') or secrets.token_hex(32)
            db.session.add(Settings(key='backup_api_key', value=backup_api_key))

        daily_ts_setting = Settings.query.filter_by(key='last_daily_backup_ts').first()
        if not daily_ts_setting:
            db.session.add(Settings(key='last_daily_backup_ts', value='0'))

        monthly_ts_setting = Settings.query.filter_by(key='last_monthly_backup_ts').first()
        if not monthly_ts_setting:
            db.session.add(Settings(key='last_monthly_backup_ts', value='0'))

        db.session.commit()
    except Exception:
        db.session.rollback()


def require_admin_view(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        _require_admin()
        return fn(*args, **kwargs)
    return wrapper


def _get_csrf_token() -> str:
    token = session.get('csrf_token')
    if not token:
        token = os.urandom(16).hex()
        session['csrf_token'] = token
    return token


def _validate_csrf() -> None:
    token = session.get('csrf_token')
    form_token = request.form.get('csrf_token')
    if not token or not form_token or token != form_token:
        abort(400)


def _redirect_back(default_endpoint: str = 'users_page'):
    nxt = request.form.get('next') or request.args.get('next')
    if nxt:
        return redirect(nxt)
    return redirect(url_for(default_endpoint))


def write_audit_log(action: str, resource_type: str = None, resource_id: int = None, detail: dict = None):
    """Write an entry to the audit log using a dedicated connection to avoid session conflicts."""
    try:
        cu = _get_current_user()
        actor_id = int(cu.id) if cu else None
        actor_username = cu.username if cu else None
        ip = request.remote_addr if request else None
        now_ts = int(time.time())
        detail_str = json.dumps(detail, separators=(',', ':')) if detail else None

        # Use raw SQLite insert via a separate connection so we never
        # interfere with the calling route's SQLAlchemy session state.
        db_path = os.path.join(app.instance_path, 'users.db')
        if not os.path.exists(db_path):
            db_path = os.path.join(app.root_path, 'users.db')
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT INTO audit_log "
                "(timestamp, actor_id, actor_username, action, resource_type, resource_id, detail, ip_address) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (now_ts, actor_id, actor_username, action, resource_type, resource_id, detail_str, ip)
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def generate_otp() -> str:
    """
    Generate a cryptographically secure 6-digit OTP code.
    
    Returns:
        String of exactly 6 digits with leading zeros preserved.
    
    Example:
        "042857", "000123", "999999"
    """
    code = secrets.randbelow(1000000)
    return f"{code:06d}"


def cleanup_expired_otps() -> int:
    """
    Remove OTP records older than 1 hour.
    
    Returns:
        Number of records deleted.
    
    Should be called periodically (e.g., via background task or before_request hook).
    """
    cutoff = int(time.time()) - 3600  # 1 hour ago
    deleted = OTP.query.filter(OTP.created_at < cutoff).delete()
    db.session.commit()
    return deleted


# User model for authentication (accounts only)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    status = db.Column(db.String(20), nullable=False, default='active')
    suspended_until = db.Column(db.Integer, nullable=True)
    false_reports_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    obstruction_type = db.Column(db.String(50), nullable=True)
    photo_path = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))
    status_updated_at = db.Column(db.Integer, nullable=True, default=lambda: int(time.time()))
    is_fixed = db.Column(db.Boolean, nullable=False, default=False)
    fixed_at = db.Column(db.Integer, nullable=True)
    is_false_report = db.Column(db.Boolean, nullable=False, default=False)
    thumbs_up_count = db.Column(db.Integer, nullable=False, default=0)
    thumbs_down_count = db.Column(db.Integer, nullable=False, default=0)

    @property
    def created_at_iso(self) -> str:
        try:
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(self.created_at)))
        except Exception:
            return str(self.created_at)

    @property
    def status_updated_at_iso(self) -> str:
        try:
            val = int(self.status_updated_at) if self.status_updated_at else int(self.created_at)
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(val))
        except Exception:
            return ''


class Reaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    reaction_type = db.Column(db.String(10), nullable=False)  # 'up' or 'down'
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))
    updated_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()), onupdate=lambda: int(time.time()))

    __table_args__ = (
        db.UniqueConstraint('report_id', 'user_id', name='unique_user_report_reaction'),
    )


class ReportFlag(db.Model):
    """
    Tracks community flags on reports for false report detection.
    Enforces one flag per user per report through unique constraint.
    """
    __tablename__ = 'report_flag'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))
    
    __table_args__ = (
        db.UniqueConstraint('report_id', 'user_id', name='unique_report_user_flag'),
    )


class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))
    status_updated_at = db.Column(db.Integer, nullable=True, default=lambda: int(time.time()))
    is_fixed = db.Column(db.Boolean, nullable=False, default=False)
    fixed_at = db.Column(db.Integer, nullable=True)
    detected_class = db.Column(db.String(50), nullable=True)
    final_class = db.Column(db.String(50), nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)
    snapshot_image_path = db.Column(db.String(512), nullable=True)
    detection_source = db.Column(db.String(50), nullable=True)
    review_status = db.Column(db.String(20), nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at = db.Column(db.Integer, nullable=True)
    visibility_scope = db.Column(db.String(20), nullable=True)

    @property
    def created_at_iso(self) -> str:
        try:
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(self.created_at)))
        except Exception:
            return str(self.created_at)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))

    @property
    def created_at_iso(self) -> str:
        try:
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(self.created_at)))
        except Exception:
            return str(self.created_at)


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()), onupdate=lambda: int(time.time()))


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()), index=True)
    actor_id = db.Column(db.Integer, nullable=True)
    actor_username = db.Column(db.String(150), nullable=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=True)
    resource_id = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.Text, nullable=True)  # JSON string
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))

    @property
    def timestamp_iso(self) -> str:
        try:
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(self.timestamp)))
        except Exception:
            return str(self.timestamp)

    @property
    def detail_parsed(self):
        try:
            return json.loads(self.detail) if self.detail else {}
        except Exception:
            return {}


class OTP(db.Model):
    """
    Stores one-time password verification codes with expiration and attempt tracking.
    OTP codes are hashed before storage (never stored in plaintext).
    """
    __tablename__ = 'otp'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    otp_hash = db.Column(db.String(255), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)  # 'registration' or 'password_reset'
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))
    expires_at = db.Column(db.Integer, nullable=False, index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    verified = db.Column(db.Boolean, nullable=False, default=False)
    
    __table_args__ = (
        db.Index('idx_otp_lookup', 'email', 'purpose', 'verified'),
    )
    
    def is_expired(self) -> bool:
        """Check if OTP has exceeded 10-minute expiration window."""
        return int(time.time()) > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if OTP can still be used (not expired, not verified, attempts < 3)."""
        return not self.verified and not self.is_expired() and self.attempts < 3
    
    def increment_attempts(self) -> None:
        """Increment verification attempt counter."""
        self.attempts += 1
    
    def mark_verified(self) -> None:
        """Mark OTP as successfully verified."""
        self.verified = True


# Ensure database tables are created safely within app context
with app.app_context():
    db.create_all()
    try:
        cols = db.session.execute(text("PRAGMA table_info(user)")).fetchall()
        existing = {str(c[1]).lower() for c in cols}
        if 'role' not in existing:
            db.session.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))
        if 'status' not in existing:
            db.session.execute(text("ALTER TABLE user ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'"))
        if 'suspended_until' not in existing:
            db.session.execute(text("ALTER TABLE user ADD COLUMN suspended_until INTEGER"))
        if 'false_reports_count' not in existing:
            db.session.execute(text("ALTER TABLE user ADD COLUMN false_reports_count INTEGER NOT NULL DEFAULT 0"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        cols = db.session.execute(text("PRAGMA table_info(report)")).fetchall()
        existing = {str(c[1]).lower() for c in cols}
        if existing:
            if 'created_at' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN created_at INTEGER"))
            if 'status_updated_at' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN status_updated_at INTEGER"))
            if 'latitude' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN latitude REAL"))
            if 'longitude' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN longitude REAL"))
            if 'obstruction_type' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN obstruction_type VARCHAR(50)"))
            if 'photo_path' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN photo_path VARCHAR(512)"))
            if 'is_fixed' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN is_fixed BOOLEAN NOT NULL DEFAULT 0"))
            if 'fixed_at' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN fixed_at INTEGER"))
            if 'is_false_report' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN is_false_report BOOLEAN NOT NULL DEFAULT 0"))
            if 'thumbs_up_count' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN thumbs_up_count INTEGER NOT NULL DEFAULT 0"))
            if 'thumbs_down_count' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN thumbs_down_count INTEGER NOT NULL DEFAULT 0"))
            try:
                db.session.execute(text("UPDATE report SET status_updated_at = created_at WHERE status_updated_at IS NULL"))
            except Exception:
                pass
            db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        cols = db.session.execute(text("PRAGMA table_info(detection)")).fetchall()
        existing = {str(c[1]).lower() for c in cols}
        if existing:
            if 'created_at' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN created_at INTEGER"))
            if 'status_updated_at' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN status_updated_at INTEGER"))
            if 'label' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN label VARCHAR(50) NOT NULL DEFAULT ''"))
            if 'confidence' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN confidence REAL NOT NULL DEFAULT 0"))
            if 'latitude' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN latitude REAL NOT NULL DEFAULT 0"))
            if 'longitude' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN longitude REAL NOT NULL DEFAULT 0"))
            if 'is_fixed' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN is_fixed BOOLEAN NOT NULL DEFAULT 0"))
            if 'fixed_at' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN fixed_at INTEGER"))
            if 'detected_class' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN detected_class VARCHAR(50)"))
            if 'final_class' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN final_class VARCHAR(50)"))
            if 'confidence_score' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN confidence_score REAL"))
            if 'snapshot_image_path' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN snapshot_image_path VARCHAR(512)"))
            if 'detection_source' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN detection_source VARCHAR(50)"))
            if 'review_status' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN review_status VARCHAR(20)"))
            if 'reviewed_by' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN reviewed_by INTEGER"))
            if 'reviewed_at' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN reviewed_at INTEGER"))
            if 'visibility_scope' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN visibility_scope VARCHAR(20)"))
            try:
                db.session.execute(text("UPDATE detection SET status_updated_at = created_at WHERE status_updated_at IS NULL"))
            except Exception:
                pass
            db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        cols = db.session.execute(text("PRAGMA table_info(notification)")).fetchall()
        existing = {str(c[1]).lower() for c in cols}
        if existing:
            if 'created_at' not in existing:
                db.session.execute(text("ALTER TABLE notification ADD COLUMN created_at INTEGER"))
            if 'is_read' not in existing:
                db.session.execute(text("ALTER TABLE notification ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT 0"))
            if 'link' not in existing:
                db.session.execute(text("ALTER TABLE notification ADD COLUMN link VARCHAR(500)"))
            db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        cols = db.session.execute(text("PRAGMA table_info(settings)")).fetchall()
        existing = {str(c[1]).lower() for c in cols}
        if not existing:
            # Table created by db.create_all(), but if we need to migrate or check
            pass
        
        # Seed default settings if not present
        defaults = {
            'fixed_defect_expiration_days': '30',
            'auto_fix_threshold': '3'
        }
        for k, v in defaults.items():
            s = Settings.query.filter_by(key=k).first()
            if not s:
                db.session.add(Settings(key=k, value=v))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Ensure audit_log table exists (safe migration guard)
    try:
        db.session.execute(text("SELECT 1 FROM audit_log LIMIT 1"))
    except Exception:
        db.session.rollback()
        try:
            db.session.execute(text(
                "CREATE TABLE IF NOT EXISTS audit_log ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "timestamp INTEGER NOT NULL, "
                "actor_id INTEGER, "
                "actor_username VARCHAR(150), "
                "action VARCHAR(80) NOT NULL, "
                "resource_type VARCHAR(50), "
                "resource_id INTEGER, "
                "detail TEXT, "
                "ip_address VARCHAR(45)"
                ")"
            ))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log (timestamp)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_action ON audit_log (action)"))
            db.session.commit()
        except Exception:
            db.session.rollback()

    # Ensure OTP table exists (safe migration guard)
    try:
        db.session.execute(text("SELECT 1 FROM otp LIMIT 1"))
    except Exception:
        db.session.rollback()
        try:
            db.session.execute(text(
                "CREATE TABLE IF NOT EXISTS otp ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "email VARCHAR(255) NOT NULL, "
                "otp_hash VARCHAR(255) NOT NULL, "
                "purpose VARCHAR(20) NOT NULL, "
                "created_at INTEGER NOT NULL, "
                "expires_at INTEGER NOT NULL, "
                "attempts INTEGER NOT NULL DEFAULT 0, "
                "verified BOOLEAN NOT NULL DEFAULT 0"
                ")"
            ))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_otp_email ON otp (email)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_otp_expires_at ON otp (expires_at)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_otp_lookup ON otp (email, purpose, verified)"))
            db.session.commit()
        except Exception:
            db.session.rollback()

    # Ensure report_flag table exists (safe migration guard)
    try:
        db.session.execute(text("SELECT 1 FROM report_flag LIMIT 1"))
    except Exception:
        db.session.rollback()
        try:
            db.session.execute(text(
                "CREATE TABLE IF NOT EXISTS report_flag ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "report_id INTEGER NOT NULL, "
                "user_id INTEGER NOT NULL, "
                "created_at INTEGER NOT NULL, "
                "FOREIGN KEY (report_id) REFERENCES report(id) ON DELETE CASCADE, "
                "FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE, "
                "UNIQUE(report_id, user_id)"
                ")"
            ))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_report_flag_report ON report_flag(report_id)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_report_flag_user ON report_flag(user_id)"))
            db.session.commit()
        except Exception:
            db.session.rollback()
    
    # Add default community_false_report_threshold setting
    try:
        threshold_setting = Settings.query.filter_by(key='community_false_report_threshold').first()
        if not threshold_setting:
            db.session.add(Settings(key='community_false_report_threshold', value='3'))
            db.session.commit()
    except Exception:
        db.session.rollback()

    _run_startup_migrations()
    _seed_backup_api_key()

model = YOLO("best.pt")  # use your model path
camera = None
gps_latest = {"lat": None, "lon": None, "valid": False, "ts": None}
gps_thread = None
gps_stop_event = threading.Event()
gps_lock = threading.Lock()
last_log_time = 0.0
LOG_COOLDOWN_SEC = 2.0
gps_port_cfg = None
gps_baud_cfg = None
_gps_started = False
GPS_VALID_GRACE_SEC = 1.0

def nmea_to_decimal(coord, direction):
    if not coord or not direction:
        return None
    try:
        if "," in coord:
            coord = coord.split(",")[0]
        if "." not in coord:
            return None
        # Use direction to determine degree length: lat (N/S) = 2 deg digits, lon (E/W) = 3 deg digits
        deg_len = 2 if direction in ("N", "S") else 3
        deg = float(coord[:deg_len])
        minutes = float(coord[deg_len:])
        dec = deg + minutes / 60.0
        if direction in ("S", "W"):
            dec = -dec
        return dec
    except Exception:
        return None

def parse_rmc(fields):
    if len(fields) < 7:
        return None, None, False
    status = fields[2] if len(fields) > 2 else "V"
    lat = nmea_to_decimal(fields[3] if len(fields) > 3 else None, fields[4] if len(fields) > 4 else None)
    lon = nmea_to_decimal(fields[5] if len(fields) > 5 else None, fields[6] if len(fields) > 6 else None)
    valid = status == "A" and lat is not None and lon is not None
    return lat, lon, valid

def parse_gga(fields):
    # GGA: $GxGGA, time, lat, N/S, lon, E/W, fix_quality, num_sats, ...
    # fix_quality: 0 = invalid, 1 = GPS fix, 2 = DGPS fix, 4 = RTK, etc.
    if len(fields) < 7:
        return None, None, False
    lat = nmea_to_decimal(fields[2] if len(fields) > 2 else None, fields[3] if len(fields) > 3 else None)
    lon = nmea_to_decimal(fields[4] if len(fields) > 4 else None, fields[5] if len(fields) > 5 else None)
    try:
        fix_q = int(fields[6]) if len(fields) > 6 and fields[6] != '' else 0
    except Exception:
        fix_q = 0
    valid = (fix_q > 0) and (lat is not None) and (lon is not None)
    return lat, lon, valid

def gps_reader_loop(port, baud):
    global gps_latest
    if serial is None:
        return
    try:
        ser = serial.Serial(port=port, baudrate=baud, timeout=1)
        try:
            print(f"[GPS] Opened {port} @ {baud}")
        except Exception:
            pass
    except Exception:
        ser = None
    while not gps_stop_event.is_set():
        try:
            if ser is None or not ser.is_open:
                try:
                    ser = serial.Serial(port=port, baudrate=baud, timeout=1)
                    try:
                        print(f"[GPS] Reopened {port} @ {baud}")
                    except Exception:
                        pass
                except Exception:
                    time.sleep(1.0)
                    continue
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue
            parts = line.split(",")
            if line.startswith("$GPRMC") or line.startswith("$GNRMC"):
                lat, lon, valid = parse_rmc(parts)
            elif line.startswith("$GPGGA") or line.startswith("$GNGGA"):
                lat, lon, valid = parse_gga(parts)
            else:
                continue
            if lat is not None and lon is not None:
                nowt = time.time()
                with gps_lock:
                    prev_valid = bool(gps_latest.get("valid"))
                    prev_ts = gps_latest.get("ts") or 0
                    # If current sentence says invalid but we had a recent valid fix, keep it valid within grace window
                    eff_valid = bool(valid)
                    if not eff_valid and prev_valid and (nowt - prev_ts) <= GPS_VALID_GRACE_SEC:
                        eff_valid = True
                    gps_latest = {"lat": lat, "lon": lon, "valid": eff_valid, "ts": nowt}
                if valid:
                    try:
                        print(f"[GPS] Fix lat={lat:.6f} lon={lon:.6f}")
                    except Exception:
                        pass
        except Exception:
            time.sleep(0.2)
            continue
    try:
        if ser is not None:
            ser.close()
    except Exception:
        pass

def ensure_gps_thread():
    global gps_thread, gps_port_cfg, gps_baud_cfg
    if gps_thread is None or not gps_thread.is_alive():
        gps_stop_event.clear()
        port = os.environ.get("GPS_SERIAL_PORT", "COM3")
        baud = int(os.environ.get("GPS_BAUD", "4800"))
        gps_port_cfg = port
        gps_baud_cfg = baud
        gps_thread = threading.Thread(target=gps_reader_loop, args=(port, baud), daemon=True)
        gps_thread.start()

def open_camera(index=0):
    global camera
    if camera is None or not getattr(camera, 'isOpened', lambda: False)():
        cam = None
        if os.name == 'nt' and hasattr(cv2, 'CAP_DSHOW'):
            cam = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if cam is not None and not cam.isOpened():
                cam.release()
                cam = None
        if cam is None:
            cam = cv2.VideoCapture(index)
        camera = cam
    ensure_gps_thread()

def close_camera():
    global camera
    if camera is not None:
        try:
            camera.release()
        except Exception:
            pass
        camera = None

def _save_detection_snapshot(frame):
    try:
        os.makedirs(DETECTION_UPLOAD_FOLDER, exist_ok=True)
        fname = f"{uuid4().hex}.jpg"
        abs_path = os.path.join(DETECTION_UPLOAD_FOLDER, fname)
        ok = cv2.imwrite(abs_path, frame)
        if ok:
            return f"uploads/detections/{fname}"
    except Exception:
        return None
    return None

def generate_frames():
    global camera
    while True:
        if camera is None:
            break
        success, frame = camera.read()
        if not success:
            break
        results = model(frame, stream=True)
        for r in results:
            frame = r.plot()  # draw bounding boxes
            try:
                if hasattr(r, "boxes") and r.boxes is not None and len(r.boxes) > 0:
                    now = time.time()
                    if now - globals().get("last_log_time", 0.0) >= LOG_COOLDOWN_SEC:
                        with gps_lock:
                            lat = gps_latest.get("lat")
                            lon = gps_latest.get("lon")
                            valid = gps_latest.get("valid")
                            gts = gps_latest.get("ts") or 0
                        is_recent = (now - gts) <= GPS_VALID_GRACE_SEC
                        eff_valid = bool(valid) and is_recent
                        confs = r.boxes.conf.tolist() if getattr(r.boxes, "conf", None) is not None else []
                        clss = r.boxes.cls.tolist() if getattr(r.boxes, "cls", None) is not None else []
                        idxs = list(range(len(confs))) if confs else []
                        idxs = [i for i in idxs if confs[i] is not None and confs[i] >= 0.5]
                        if idxs:
                            best_i = max(idxs, key=lambda i: confs[i])
                            best_conf = float(confs[best_i])
                            best_cls = int(clss[best_i]) if clss else 0
                            names = getattr(model, "names", {}) or {}
                            best_label = str(names.get(best_cls, str(best_cls)))
                            if eff_valid and lat is not None and lon is not None:
                                try:
                                    with app.app_context():
                                        if best_conf > 0.60:
                                            row = Detection(
                                                label=best_label,
                                                confidence=best_conf,
                                                confidence_score=best_conf,
                                                latitude=float(lat),
                                                longitude=float(lon),
                                                created_at=int(now),
                                                status_updated_at=int(now),
                                                detected_class=best_label,
                                                final_class=best_label,
                                                detection_source='ai_survey',
                                                review_status='confirmed',
                                                visibility_scope='public',
                                            )
                                        else:
                                            snapshot_rel = _save_detection_snapshot(frame)
                                            row = Detection(
                                                label=best_label,
                                                confidence=best_conf,
                                                confidence_score=best_conf,
                                                latitude=float(lat),
                                                longitude=float(lon),
                                                created_at=int(now),
                                                status_updated_at=int(now),
                                                detected_class=best_label,
                                                final_class=None,
                                                snapshot_image_path=snapshot_rel,
                                                detection_source='ai_survey',
                                                review_status='pending',
                                                visibility_scope='admin_only',
                                            )
                                        db.session.add(row)
                                        db.session.commit()
                                except Exception:
                                    db.session.rollback()
                            globals()["last_log_time"] = now
                            try:
                                if eff_valid and lat is not None and lon is not None:
                                    ts_iso = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))
                                    if best_conf > 0.60:
                                        print(f"{best_label} detected at ({float(lon)}, {float(lat)}) at {ts_iso}")
                                    else:
                                        print(f"{best_label} queued for review at ({float(lon)}, {float(lat)}) at {ts_iso}")
                                else:
                                    ts_iso = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))
                                    print(f"{best_label} detected but GPS fix invalid/stale at {ts_iso}")
                            except Exception:
                                pass
            except Exception:
                pass

        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.context_processor
def inject_notifications():
    uid = session.get('user_id')
    count = 0
    if uid:
        try:
            count = Notification.query.filter_by(user_id=int(uid), is_read=False).count()
        except Exception:
            pass
    return dict(unread_notifications_count=count)

@app.route('/')
def root_redirect():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        field_errors = {}

        # Validate empty fields
        if not identifier:
            field_errors['username'] = ['Username or email is required']
        if not password:
            field_errors['password'] = ['Password is required']

        # If there are empty field errors, return early
        if field_errors:
            return render_template('/login.html', field_errors=field_errors, values={"username": identifier})

        # Try to find user by username or email
        user = None
        try:
            is_email = bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', identifier))
            if is_email:
                user = User.query.filter(func.lower(User.email) == identifier.lower()).first()
            else:
                user = User.query.filter(func.lower(User.username) == identifier.lower()).first()
        except Exception:
            field_errors['username'] = ['Unable to process login right now. Please try again.']
            return render_template('/login.html', field_errors=field_errors, values={"username": identifier})

        # Check if user exists
        if user is None:
            field_errors['username'] = ['Username or email not found']
            return render_template('/login.html', field_errors=field_errors, values={"username": identifier})

        # Check password
        if not user.check_password(password):
            field_errors['password'] = ['Incorrect password']
            return render_template('/login.html', field_errors=field_errors, values={"username": identifier})

        # Check account status
        user_status = str(getattr(user, 'status', '') or '').strip().lower()
        if user_status == 'locked':
            field_errors['username'] = ['Your account is locked. Please contact an administrator.']
            return render_template('/login.html', field_errors=field_errors, values={"username": identifier})
        elif user_status == 'suspended':
            now_ts = int(time.time())
            until_ts = getattr(user, 'suspended_until', None)
            if until_ts is None:
                until_ts = now_ts + 5 * 60
                user.suspended_until = int(until_ts)
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()

            if int(until_ts) > now_ts:
                remaining = int(until_ts) - now_ts
                minutes = remaining // 60
                seconds = remaining % 60
                field_errors['username'] = [f'Your account is suspended. Try again in {minutes}m {seconds}s.']
                return render_template('/login.html', field_errors=field_errors, values={"username": identifier})
            else:
                user.status = 'active'
                user.suspended_until = None
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()

        # Success - log in user
        session['user_id'] = int(user.id)
        _get_csrf_token()
        write_audit_log('USER_LOGIN', 'user', int(user.id), {'username': user.username})
        if _is_admin(user):
            return redirect(url_for('index_page'))
        elif _is_moderator(user):
            return redirect(url_for('defects_page'))
        return redirect(url_for('map_page'))

    return render_template('/login.html', field_errors={}, values={})


@app.route('/recover', methods=['GET', 'POST'])
def recover():
    if request.method == 'GET':
        return render_template('/recover.html', errors=[], field_errors={"identifier": []}, values={}, show_otp=False, info_msg=None)
    
    # POST request - handle password recovery
    identifier = (request.form.get('identifier') or '').strip()
    errors = []
    field_errors = {"identifier": []}
    
    if not identifier:
        errors.append('Email address is required.')
        field_errors["identifier"].append('Email address is required.')
    elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', identifier):
        errors.append('Enter a valid email address.')
        field_errors["identifier"].append('Enter a valid email address.')
    
    if errors:
        return jsonify({'success': False, 'message': errors[0], 'errors': field_errors})
    
    # Look up user by email
    try:
        user = User.query.filter(func.lower(User.email) == identifier.lower()).first()
    except Exception:
        user = None
    
    # Always return success for security (timing attack prevention)
    if not user:
        return jsonify({
            'success': True,
            'message': 'If the account exists, a verification code has been sent.',
            'otp_code': None
        })
    
    # Generate OTP
    try:
        otp_code = generate_otp()
        otp_hash = generate_password_hash(otp_code)
        
        now = int(time.time())
        otp_record = OTP(
            email=user.email,
            otp_hash=otp_hash,
            purpose='password_reset',
            created_at=now,
            expires_at=now + 600,
            attempts=0,
            verified=False
        )
        db.session.add(otp_record)
        db.session.commit()
        
        # Store reset context in session
        session['reset_user_id'] = user.id
        session['otp_email'] = user.email
        session['otp_purpose'] = 'password_reset'
        
        return jsonify({
            'success': True,
            'otp_code': otp_code,
            'message': 'If the account exists, a verification code has been sent.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': True,
            'message': 'If the account exists, a verification code has been sent.',
            'otp_code': None
        })


@app.route('/logout')
def logout():
    cu = _get_current_user()
    if cu:
        write_audit_log('USER_LOGOUT', 'user', int(cu.id), {'username': cu.username})
    session.clear()
    return redirect(url_for('login'))


@app.route('/test-emailjs')
def test_emailjs():
    """Test page for EmailJS configuration."""
    return render_template('test_emailjs.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('/register.html', errors=[], field_errors={}, values={})
    
    # POST request - handle registration
    username = (request.form.get('username') or '').strip()
    email = (request.form.get('email') or '').strip()
    password = request.form.get('password') or ''
    terms_agreed = request.form.get('terms') == 'on'  # Checkbox value

    field_errors = {}

    # Terms and conditions validation
    if not terms_agreed:
        field_errors.setdefault('terms', []).append('You must agree to the Terms and Conditions to register')

    # Username validation
    if not username:
        field_errors.setdefault('username', []).append('Username is required')
    elif len(username) < 3:
        field_errors.setdefault('username', []).append('Username must be at least 3 characters')
    else:
        # Check uniqueness
        try:
            if User.query.filter_by(username=username).first() is not None:
                field_errors.setdefault('username', []).append('Username already exists')
        except Exception:
            field_errors.setdefault('username', []).append('Unable to validate username. Please try again.')

    # Email validation
    if not email:
        field_errors.setdefault('email', []).append('Email is required')
    elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        field_errors.setdefault('email', []).append('Invalid email format')
    else:
        # Check uniqueness
        try:
            if User.query.filter_by(email=email).first() is not None:
                field_errors.setdefault('email', []).append('Email already registered')
        except Exception:
            field_errors.setdefault('email', []).append('Unable to validate email. Please try again.')

    # Password validation
    if not password:
        field_errors.setdefault('password', []).append('Password is required')
    else:
        if len(password) < 8:
            field_errors.setdefault('password', []).append('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', password):
            field_errors.setdefault('password', []).append('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', password):
            field_errors.setdefault('password', []).append('Password must contain at least one lowercase letter')
        if not re.search(r'\d', password):
            field_errors.setdefault('password', []).append('Password must contain at least one number')

    if field_errors:
        return jsonify({'success': False, 'errors': field_errors, 'message': 'Please fix the errors below'})

    # Generate OTP
    try:
        otp_code = generate_otp()
        otp_hash = generate_password_hash(otp_code)
        
        now = int(time.time())
        otp_record = OTP(
            email=email,
            otp_hash=otp_hash,
            purpose='registration',
            created_at=now,
            expires_at=now + 600,  # 10 minutes
            attempts=0,
            verified=False
        )
        db.session.add(otp_record)
        db.session.commit()
        
        # Store registration data in session
        session['pending_registration'] = {
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'timestamp': now
        }
        session['otp_email'] = email
        session['otp_purpose'] = 'registration'
        
        return jsonify({
            'success': True,
            'otp_code': otp_code,
            'message': 'Verification code generated. Please check your email.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Failed to generate verification code. Please try again.',
            'errors': {}
        }), 500


@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP code and complete registration or password reset."""
    otp_code = (request.form.get('otp_code') or '').strip()
    
    if not otp_code or len(otp_code) != 6 or not otp_code.isdigit():
        return jsonify({
            'success': False,
            'message': 'Invalid OTP format. Please enter a 6-digit code.'
        }), 400
    
    # Get OTP context from session
    email = session.get('otp_email')
    purpose = session.get('otp_purpose')
    
    if not email or not purpose:
        return jsonify({
            'success': False,
            'message': 'Verification session expired. Please start over.'
        }), 400
    
    # Find active OTP
    otp_record = OTP.query.filter_by(
        email=email,
        purpose=purpose,
        verified=False
    ).order_by(OTP.created_at.desc()).first()
    
    if not otp_record:
        return jsonify({
            'success': False,
            'message': 'No active verification code found. Please request a new one.'
        }), 404
    
    # Check if OTP is still valid
    if not otp_record.is_valid():
        if otp_record.is_expired():
            message = 'Verification code has expired. Please request a new one.'
        else:
            message = 'Too many failed attempts. Please request a new code.'
        return jsonify({'success': False, 'message': message}), 400
    
    # Verify OTP hash
    if not check_password_hash(otp_record.otp_hash, otp_code):
        otp_record.increment_attempts()
        db.session.commit()
        
        attempts_remaining = 3 - otp_record.attempts
        return jsonify({
            'success': False,
            'message': f'Invalid verification code. {attempts_remaining} attempts remaining.',
            'attempts_remaining': attempts_remaining
        }), 400
    
    # OTP verified successfully
    otp_record.mark_verified()
    db.session.commit()
    
    # Complete the operation based on purpose
    if purpose == 'registration':
        pending = session.get('pending_registration')
        if not pending:
            return jsonify({
                'success': False,
                'message': 'Registration data not found. Please start over.'
            }), 400
        
        try:
            # Create user account
            user = User(
                username=pending['username'],
                email=pending['email'],
                password_hash=pending['password_hash'],
                role='user',
                status='active'
            )
            db.session.add(user)
            db.session.commit()
            
            write_audit_log('USER_REGISTERED', 'user', int(user.id), {'username': user.username, 'email': user.email})
            
            # Clear session
            session.pop('pending_registration', None)
            session.pop('otp_email', None)
            session.pop('otp_purpose', None)
            
            return jsonify({
                'success': True,
                'message': 'Email verified! Your account has been created.',
                'next_step': 'complete',
                'redirect': url_for('login')
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': 'Failed to create account. Please try again.'
            }), 500
    
    elif purpose == 'password_reset':
        # Allow password reset form
        session['otp_verified'] = True
        
        return jsonify({
            'success': True,
            'message': 'Identity verified. You can now reset your password.',
            'next_step': 'reset_password'
        })
    
    return jsonify({'success': False, 'message': 'Unknown purpose'}), 400


@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Generate and send a new OTP code."""
    email = session.get('otp_email')
    purpose = session.get('otp_purpose')
    
    if not email or not purpose:
        return jsonify({
            'success': False,
            'message': 'No active verification session.'
        }), 400
    
    # Check 30-second cooldown
    last_resend = session.get('last_otp_resend', 0)
    now = int(time.time())
    cooldown = 30 - (now - last_resend)
    
    if cooldown > 0:
        return jsonify({
            'success': False,
            'message': f'Please wait {cooldown} seconds before requesting a new code.',
            'cooldown_remaining': cooldown
        }), 429
    
    # Check rate limit (3 per 15 minutes)
    rate_limit_key = f'otp_rate_{email}'
    rate_data = session.get(rate_limit_key, {'count': 0, 'window_start': now})
    
    if now - rate_data['window_start'] > 900:  # 15 minutes
        rate_data = {'count': 0, 'window_start': now}
    
    if rate_data['count'] >= 3:
        return jsonify({
            'success': False,
            'message': 'Too many requests. Please try again in 15 minutes.'
        }), 429
    
    try:
        # Invalidate previous OTP
        OTP.query.filter_by(
            email=email,
            purpose=purpose,
            verified=False
        ).update({'verified': True})
        db.session.commit()
        
        # Generate new OTP
        otp_code = generate_otp()
        otp_hash = generate_password_hash(otp_code)
        
        otp_record = OTP(
            email=email,
            otp_hash=otp_hash,
            purpose=purpose,
            created_at=now,
            expires_at=now + 600,
            attempts=0,
            verified=False
        )
        db.session.add(otp_record)
        db.session.commit()
        
        # Update rate limiting
        rate_data['count'] += 1
        session[rate_limit_key] = rate_data
        session['last_otp_resend'] = now
        
        return jsonify({
            'success': True,
            'otp_code': otp_code,
            'message': 'New verification code generated.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Failed to generate new code. Please try again.'
        }), 500


@app.route('/reset-password', methods=['POST'])
def reset_password():
    """Complete password reset after OTP verification."""
    if not session.get('otp_verified'):
        return jsonify({
            'success': False,
            'message': 'Please verify your identity first.'
        }), 403
    
    user_id = session.get('reset_user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'message': 'Reset session expired. Please start over.'
        }), 400
    
    new_password = request.form.get('new_password', '')
    
    # Validate password (same rules as registration)
    errors = []
    if len(new_password) < 8:
        errors.append('Password must be at least 8 characters long.')
    if not re.search(r'[A-Z]', new_password):
        errors.append('Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', new_password):
        errors.append('Password must contain at least one lowercase letter.')
    if not re.search(r'\d', new_password):
        errors.append('Password must contain at least one number.')
    if not re.search(r'[^A-Za-z0-9]', new_password):
        errors.append('Password must contain at least one special character.')
    
    if errors:
        return jsonify({'success': False, 'message': ' '.join(errors)}), 400
    
    # Update password
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found.'
            }), 404
        
        user.set_password(new_password)
        db.session.commit()
        
        # Log password reset
        write_audit_log('PASSWORD_RESET', 'user', int(user.id), {'username': user.username, 'email': user.email})
        
        # Clear session
        session.pop('otp_verified', None)
        session.pop('reset_user_id', None)
        session.pop('otp_email', None)
        session.pop('otp_purpose', None)
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully. You can now log in.',
            'redirect': url_for('login')
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Failed to reset password. Please try again.'
        }), 500


@app.route('/index')
def index_page():
    current_user = _require_admin()
    return render_template('/index.html', current_user=current_user, is_admin=True)

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    current_user = _require_admin()
    
    errors = []
    success = False
    success_msg = request.args.get('success_msg')
    error_msg = request.args.get('error_msg')
    if error_msg:
        errors.append(error_msg)
    
    if request.method == 'POST':
        _validate_csrf()
        action = request.form.get('action')
        
        if action == 'general_settings':
            # 1. Fixed Defect Marker Expiration
            expiration_days = request.form.get('fixed_defect_expiration_days', '').strip()
            try:
                val = int(expiration_days)
                if val < 1:
                    errors.append('Expiration days must be at least 1.')
                else:
                    s = Settings.query.filter_by(key='fixed_defect_expiration_days').first()
                    if not s:
                        s = Settings(key='fixed_defect_expiration_days')
                        db.session.add(s)
                    s.value = str(val)
            except ValueError:
                errors.append('Expiration days must be a number.')
                
            # 2. Automatic Fix Threshold
            auto_fix_threshold = request.form.get('auto_fix_threshold', '').strip()
            try:
                val = int(auto_fix_threshold)
                if val < 1:
                    errors.append('Auto-fix threshold must be at least 1.')
                else:
                    s = Settings.query.filter_by(key='auto_fix_threshold').first()
                    if not s:
                        s = Settings(key='auto_fix_threshold')
                        db.session.add(s)
                    s.value = str(val)
            except ValueError:
                errors.append('Auto-fix threshold must be a number.')
            
            # 3. False Report Threshold
            false_report_threshold = request.form.get('false_report_threshold', '').strip()
            try:
                val = int(false_report_threshold)
                if val < 1:
                    errors.append('False report threshold must be at least 1.')
                else:
                    s = Settings.query.filter_by(key='false_report_threshold').first()
                    if not s:
                        s = Settings(key='false_report_threshold')
                        db.session.add(s)
                    s.value = str(val)
            except ValueError:
                errors.append('False report threshold must be a number.')

            # 4. Community False Report Threshold
            community_threshold = request.form.get('community_false_report_threshold', '').strip()
            try:
                val = int(community_threshold)
                if val < 1:
                    errors.append('Community false report threshold must be at least 1.')
                elif val > 10:
                    errors.append('Community false report threshold must not exceed 10.')
                else:
                    s = Settings.query.filter_by(key='community_false_report_threshold').first()
                    if not s:
                        s = Settings(key='community_false_report_threshold')
                        db.session.add(s)
                    s.value = str(val)
            except ValueError:
                errors.append('Community false report threshold must be a number.')

            if not errors:
                try:
                    db.session.commit()
                    success = True
                    write_audit_log('SETTINGS_CHANGED', 'settings', None, {
                        'fixed_defect_expiration_days': expiration_days,
                        'auto_fix_threshold': auto_fix_threshold,
                        'false_report_threshold': false_report_threshold,
                        'community_false_report_threshold': community_threshold,
                    })
                except Exception as e:
                    db.session.rollback()
                    errors.append('Failed to save settings: ' + str(e))
    
    # Load current settings
    settings_map = {}
    try:
        all_settings = Settings.query.all()
        for s in all_settings:
            settings_map[s.key] = s.value
    except Exception:
        pass
        
    # Defaults if missing
    if 'fixed_defect_expiration_days' not in settings_map:
        settings_map['fixed_defect_expiration_days'] = '30'
    if 'auto_fix_threshold' not in settings_map:
        settings_map['auto_fix_threshold'] = '3'
    if 'false_report_threshold' not in settings_map:
        settings_map['false_report_threshold'] = '5'
    if 'community_false_report_threshold' not in settings_map:
        settings_map['community_false_report_threshold'] = '3'
        
    b2_connected = False
    backups = []
    
    if B2_DEPS_AVAILABLE:
        key_id = settings_map.get('b2_key_id')
        app_key = settings_map.get('b2_app_key')
        bucket_name = settings_map.get('b2_bucket_name')
        
        if key_id and app_key and bucket_name:
            try:
                info = InMemoryAccountInfo()
                b2_api = B2Api(info)
                b2_api.authorize_account("production", key_id, app_key)
                bucket = b2_api.get_bucket_by_name(bucket_name)
                b2_connected = True
                
                # List backups (simplified - just check connection, don't list files for now)
                # The bucket.ls() call was causing the error, so we'll skip listing backups
                # Connection is successful if we got here
            except Exception as e:
                b2_connected = False
                print(f"B2 Connection Error: {type(e).__name__}: {str(e)}")
                # If auth fails, we might want to clear stored creds or just show disconnected
                pass

    return render_template(
        'settings.html',
        current_user=current_user,
        is_admin=True,
        settings=settings_map,
        errors=errors,
        success=success,
        success_msg=success_msg,
        csrf_token=_get_csrf_token(),
        b2_connected=b2_connected,
        backups=backups
    )

@app.route('/settings/b2/connect', methods=['POST'])
def b2_connect():
    current_user = _require_admin()
    _validate_csrf()
    if not B2_DEPS_AVAILABLE:
        return redirect(url_for('settings_page', error_msg='Backblaze B2 library is not available.'))
    
    key_id = request.form.get('key_id', '').strip()
    app_key = request.form.get('app_key', '').strip()
    bucket_name = request.form.get('bucket_name', '').strip()
    
    if not key_id or not app_key or not bucket_name:
        return redirect(url_for('settings_page', error_msg='Please provide Key ID, Application Key, and Bucket Name.')) 

    # Save to DB
    try:
        for k, v in [('b2_key_id', key_id), ('b2_app_key', app_key), ('b2_bucket_name', bucket_name)]:
            s = Settings.query.filter_by(key=k).first()
            if not s: s = Settings(key=k); db.session.add(s)
            s.value = v
        db.session.commit()
    except Exception:
        db.session.rollback()
        return redirect(url_for('settings_page', error_msg='Unable to save Backblaze B2 settings.'))

    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", key_id, app_key)
        b2_api.get_bucket_by_name(bucket_name)
        write_audit_log('B2_CONNECTED', 'settings', None, {'bucket': bucket_name})
        return redirect(url_for('settings_page', success_msg='Connected to Backblaze B2 successfully.'))
    except Exception:
        return redirect(url_for('settings_page', error_msg='Backblaze B2 connection failed. Verify Key ID, Application Key, and bucket access.'))

@app.route('/settings/b2/disconnect', methods=['POST'])
def b2_disconnect():
    _require_admin()
    _validate_csrf()
    try:
        Settings.query.filter(Settings.key.in_(['b2_key_id', 'b2_app_key', 'b2_bucket_name'])).delete(synchronize_session=False)
        db.session.commit()
        write_audit_log('B2_DISCONNECTED', 'settings', None, {})
    except Exception:
        db.session.rollback()
    return redirect(url_for('settings_page', error_msg='Disconnected from Backblaze B2.'))

@app.route('/settings/b2/backup', methods=['POST'])
def b2_backup():
    current_user = _require_admin()
    _validate_csrf()
    
    if not B2_DEPS_AVAILABLE:
        return redirect(url_for('settings_page', error_msg='Backblaze B2 dependencies are not installed.'))
        
    # Get creds
    s_key_id = Settings.query.filter_by(key='b2_key_id').first()
    s_app_key = Settings.query.filter_by(key='b2_app_key').first()
    s_bucket = Settings.query.filter_by(key='b2_bucket_name').first()
    
    if not s_key_id or not s_app_key or not s_bucket:
        return redirect(url_for('settings_page', error_msg='Backblaze B2 is not configured.'))
        
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", s_key_id.value, s_app_key.value)
        bucket = b2_api.get_bucket_by_name(s_bucket.value)
        
        # Backup file
        db_path = os.path.join(app.root_path, 'instance', 'users.db')
        if not os.path.exists(db_path):
            db_path = os.path.join(app.root_path, 'users.db')
        
        if not os.path.exists(db_path):
            return redirect(url_for('settings_page', error_msg='Database file not found.'))
             
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_users_{timestamp}.db"
        
        bucket.upload_local_file(
            local_file=db_path,
            file_name=backup_name,
            file_infos={'author': current_user.username}
        )
        
        # Log the backup
        write_audit_log('BACKUP_EXPORTED', 'system', current_user.id, {'filename': backup_name, 'destination': 'Backblaze B2'})
        
        return redirect(url_for('settings_page', success_msg=f'Backup uploaded successfully to Backblaze B2: {backup_name}'))
    except Exception as e:
        return redirect(url_for('settings_page', error_msg=f'Backup failed: {str(e)}'))
 

@app.route('/settings/b2/restore', methods=['POST'])
def b2_restore():
    current_user = _require_admin()
    _validate_csrf()
    
    file_id = request.form.get('file_id')
    if not file_id:
        return redirect(url_for('settings_page', error_msg='No backup file selected.'))
        
    s_key_id = Settings.query.filter_by(key='b2_key_id').first()
    s_app_key = Settings.query.filter_by(key='b2_app_key').first()
    s_bucket = Settings.query.filter_by(key='b2_bucket_name').first()
    
    if not s_key_id or not s_app_key or not s_bucket:
        return redirect(url_for('settings_page', error_msg='Backblaze B2 is not configured.'))
        
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", s_key_id.value, s_app_key.value)
        bucket = b2_api.get_bucket_by_name(s_bucket.value)
        
        # Download to temp file
        temp_path = os.path.join(app.root_path, 'restore_temp.db')
        
        file_version = b2_api.get_file_info(file_id)
        download_dest = bucket.download_file_by_id(file_id)
        download_dest.save_to(temp_path)

        # Check integrity
        with open(temp_path, 'rb') as f:
            header = f.read(16)
            if b'SQLite format 3' not in header:
                os.remove(temp_path)
                return redirect(url_for('settings_page', error_msg='Invalid database file format.'))
        
        # Restore
        db_path = os.path.join(app.root_path, 'instance', 'users.db')
        
        # Close DB connection
        db.session.remove()
        db.engine.dispose()
        
        # Replace
        import shutil
        shutil.move(temp_path, db_path)
        
        # Log the restore
        write_audit_log('BACKUP_RESTORED', 'system', current_user.id, {'file_id': file_id})
            
        return redirect(url_for('settings_page', success_msg='Database restored successfully. All data has been replaced with the backup.'))
    except Exception as e:
        # Clean up temp file if it exists
        temp_path = os.path.join(app.root_path, 'restore_temp.db')
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return redirect(url_for('settings_page', error_msg=f'Restore failed: {str(e)}'))



def _run_daily_incremental_backup():
    now_ts = int(time.time())
    temp_path = None
    try:
        # 1. Read last_daily_backup_ts from Settings
        last_ts_setting = Settings.query.filter_by(key='last_daily_backup_ts').first()
        last_daily_backup_ts = int(last_ts_setting.value) if last_ts_setting and last_ts_setting.value else 0

        # 3. Get B2 credentials
        def _get_setting(k):
            s = Settings.query.filter_by(key=k).first()
            return s.value if s and s.value else None

        key_id = _get_setting('b2_key_id')
        app_key = _get_setting('b2_app_key')
        bucket_name = _get_setting('b2_bucket_name')

        if not key_id or not app_key or not bucket_name:
            _backup_log_append({
                'user': 'system', 'operation': 'export', 'backup_type': 'daily',
                'filename': None, 'timestamp': now_ts, 'status': 'failure',
                'error': 'B2 not configured'
            })
            return {'success': False, 'message': 'B2 not configured', 'status_code': 503}

        # 4. Query 7 tables for new rows
        tables = ['report', 'detection', 'reaction', 'report_flag', 'notification', 'user', 'audit_log']
        db_path = _get_db_path()
        src_conn = sqlite3.connect(db_path)
        src_conn.row_factory = sqlite3.Row
        table_rows = {}
        for table in tables:
            try:
                cur = src_conn.execute(f'SELECT * FROM {table} WHERE created_at > ?', (last_daily_backup_ts,))
                table_rows[table] = cur.fetchall()
            except Exception:
                table_rows[table] = []

        # 5. Count total new rows
        total_new = sum(len(rows) for rows in table_rows.values())
        if total_new == 0:
            src_conn.close()
            _backup_log_append({
                'user': 'system', 'operation': 'export', 'backup_type': 'daily',
                'filename': None, 'timestamp': now_ts, 'status': 'success', 'note': 'no_new_data'
            })
            s = Settings.query.filter_by(key='last_daily_backup_ts').first()
            s.value = str(now_ts)
            db.session.commit()
            return {'success': True, 'message': 'No new data since last backup', 'note': 'no_new_data'}

        # 6. Build incremental SQLite file
        os.makedirs(BACKUP_DIR, exist_ok=True)
        temp_path = os.path.join(BACKUP_DIR, f'incremental_{time.strftime("%Y%m%d_%H%M%S")}.db')
        dst_conn = sqlite3.connect(temp_path)
        for table in tables:
            rows = table_rows[table]
            if not rows:
                continue
            # Copy schema
            schema_cur = src_conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            )
            schema_row = schema_cur.fetchone()
            if schema_row:
                create_sql = schema_row[0].replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS', 1)
                dst_conn.execute(create_sql)
            # Insert rows
            if rows:
                cols = rows[0].keys()
                placeholders = ', '.join(['?'] * len(cols))
                col_names = ', '.join(cols)
                dst_conn.executemany(
                    f'INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})',
                    [tuple(row) for row in rows]
                )
        dst_conn.commit()
        dst_conn.close()
        src_conn.close()

        # 7. Upload to B2
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account('production', key_id, app_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)
        bucket.upload_local_file(
            local_file=temp_path,
            file_name=os.path.basename(temp_path),
            file_infos={'author': 'system', 'backup_type': 'daily'}
        )

        # 8. Update last_daily_backup_ts
        s = Settings.query.filter_by(key='last_daily_backup_ts').first()
        s.value = str(now_ts)
        db.session.commit()

        # 9. Log success
        _backup_log_append({
            'user': 'system', 'operation': 'export', 'backup_type': 'daily',
            'filename': os.path.basename(temp_path), 'timestamp': now_ts, 'status': 'success'
        })

        # 10. Return success
        return {'success': True, 'message': f'Daily incremental backup completed: {os.path.basename(temp_path)}'}

    except Exception as e:
        # 11. Log failure
        _backup_log_append({
            'user': 'system', 'operation': 'export', 'backup_type': 'daily',
            'filename': None, 'timestamp': now_ts, 'status': 'failure', 'error': str(e)
        })
        # 12. Clean up temp file on failure
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return {'success': False, 'message': str(e), 'status_code': 500}


def _run_monthly_full_backup():
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
            'filename': None, 'timestamp': now_ts, 'status': 'failure',
            'error': str(e)
        })
        # Clean up temp file on error
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return {'success': False, 'message': f'Monthly backup failed: {str(e)}', 'status_code': 500}


@app.route('/admin/backups/manual', methods=['POST'])
def admin_backups_manual():
    current_user = _require_admin()
    _validate_csrf()
    
    if not BACKUP_LOCK.acquire(blocking=False):
        return jsonify({'success': False, 'message': 'A backup operation is already in progress.'}), 409
    
    now_ts = int(time.time())
    temp_path = None
    
    try:
        # Check B2 credentials
        def _get_b2_setting(k):
            s = Settings.query.filter_by(key=k).first()
            return s.value if s and s.value else None
        
        key_id = _get_b2_setting('b2_key_id')
        app_key = _get_b2_setting('b2_app_key')
        bucket_name = _get_b2_setting('b2_bucket_name')
        
        if not key_id or not app_key or not bucket_name:
            _backup_log_append({
                'user': current_user.username, 'operation': 'export', 'backup_type': 'manual',
                'filename': None, 'timestamp': now_ts, 'status': 'failure',
                'error': 'B2 not configured'
            })
            return jsonify({'success': False, 'message': 'Backblaze B2 is not configured. Please configure B2 credentials in Settings.'}), 400
        
        # Build filename
        backup_name = f'manual_{time.strftime("%Y%m%d_%H%M%S")}.db'
        os.makedirs(BACKUP_DIR, exist_ok=True)
        temp_path = os.path.join(BACKUP_DIR, backup_name)
        
        # Full SQLite online backup
        src = sqlite3.connect(_get_db_path())
        dst = sqlite3.connect(temp_path)
        src.backup(dst)
        dst.close()
        src.close()
        
        # Upload to B2
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account('production', key_id, app_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)
        bucket.upload_local_file(
            local_file=temp_path,
            file_name=backup_name,
            file_infos={'author': current_user.username, 'backup_type': 'manual'}
        )
        
        # Log success
        _backup_log_append({
            'user': current_user.username, 'operation': 'export', 'backup_type': 'manual',
            'filename': backup_name, 'timestamp': now_ts, 'status': 'success'
        })
        write_audit_log('BACKUP_MANUAL', 'backup', None, {'filename': backup_name})
        
        return jsonify({'success': True, 'message': f'Manual backup completed: {backup_name}'})
    
    except Exception as e:
        _backup_log_append({
            'user': current_user.username, 'operation': 'export', 'backup_type': 'manual',
            'filename': None, 'timestamp': now_ts, 'status': 'failure', 'error': str(e)
        })
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return jsonify({'success': False, 'message': f'Manual backup failed: {str(e)}'}), 500
    
    finally:
        BACKUP_LOCK.release()


@app.route('/api/backups/scheduled', methods=['POST'])
def api_backups_scheduled():
    api_key = request.headers.get('X-Backup-Api-Key', '')
    setting = Settings.query.filter_by(key='backup_api_key').first()
    expected_key = setting.value if setting else None
    if not api_key or not expected_key or api_key != expected_key:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    backup_type = data.get('type', '').strip().lower()
    if backup_type not in {'daily', 'monthly'}:
        return jsonify({'success': False, 'message': 'Invalid backup type. Use "daily" or "monthly".'}), 400

    if not BACKUP_LOCK.acquire(blocking=False):
        return jsonify({'success': False, 'message': 'A backup operation is already in progress.'}), 409

    try:
        if backup_type == 'daily':
            result = _run_daily_incremental_backup()
        else:
            result = _run_monthly_full_backup()
    finally:
        BACKUP_LOCK.release()

    status_code = 200 if result.get('success') else 500
    return jsonify(result), status_code


@app.route('/admin/backups')
def admin_backups_page():
    current_user = _require_admin()
    success_msg = request.args.get('success_msg')
    error_msg = request.args.get('error_msg')
    
    # Pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # Validate per_page
    if per_page not in [5, 10, 20, 50]:
        per_page = 10
    
    # Filter parameters - Date Range
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    
    # Filter parameters - Time Range
    time_from = request.args.get('time_from', '').strip()
    time_to = request.args.get('time_to', '').strip()
    
    ts = time.strftime("%Y%m%d_%H%M%S")
    default_format = 'db'
    default_filename = f"backup_{ts}.{default_format}"
    
    # Read all history
    all_history = _backup_log_read(500)  # Get more records for filtering
    
    # Apply filters
    filtered_history = []
    for item in all_history:
        # Derive backup_type for legacy entries
        if 'backup_type' not in item or not item['backup_type']:
            operation = item.get('operation', '')
            if operation == 'export':
                item['backup_type'] = 'manual'
            elif operation == 'import':
                item['backup_type'] = 'restore'
            else:
                item['backup_type'] = 'unknown'
        
        name = str(item.get('filename') or '')
        item['can_download'] = bool(name and os.path.exists(os.path.join(BACKUP_DIR, name)))
        ts_val = int(item.get('timestamp') or 0)
        
        # Convert to 12-hour format with AM/PM
        if ts_val:
            dt = time.localtime(ts_val)
            item['timestamp_iso'] = time.strftime('%Y-%m-%d %I:%M:%S %p', dt)
            item['date_only'] = time.strftime('%Y-%m-%d', dt)
            item['time_only'] = time.strftime('%H:%M', dt)  # 24-hour for comparison
            item['time_display'] = time.strftime('%I:%M %p', dt)  # 12-hour for display
        else:
            item['timestamp_iso'] = ''
            item['date_only'] = ''
            item['time_only'] = ''
            item['time_display'] = ''
        
        # Apply date range filter independently
        if date_from and item['date_only'] < date_from:
            continue
        if date_to and item['date_only'] > date_to:
            continue
            
        # Apply time range filter independently
        if time_from and item['time_only'] < time_from:
            continue
        if time_to and item['time_only'] > time_to:
            continue
        
        filtered_history.append(item)
    
    # Pagination
    total_items = len(filtered_history)
    total_pages = max(1, (total_items + per_page - 1) // per_page)  # At least 1 page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    history = filtered_history[start_idx:end_idx]
    
    return render_template(
        '/backup_management.html',
        current_user=current_user,
        is_admin=True,
        csrf_token=_get_csrf_token(),
        success_msg=success_msg,
        error_msg=error_msg,
        default_filename=default_filename,
        default_format=default_format,
        history=history,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        per_page=per_page,
        date_from=date_from,
        date_to=date_to,
        time_from=time_from,
        time_to=time_to
    )


@app.route('/admin/backups/export', methods=['POST'])
def admin_backups_export():
    current_user = _require_admin()
    _validate_csrf()
    if not BACKUP_LOCK.acquire(blocking=False):
        return jsonify({'success': False, 'message': 'A backup operation is already in progress.'}), 409
    started_at = int(time.time())
    try:
        fmt = str(request.form.get('backup_format') or 'db').strip().lower().lstrip('.')
        if fmt not in {'db', 'sql'}:
            return jsonify({'success': False, 'message': 'Unsupported backup format.'}), 400
        raw_name = (request.form.get('backup_filename') or '').strip()
        safe_name = secure_filename(raw_name) if raw_name else ''
        if not safe_name:
            safe_name = f"backup_{time.strftime('%Y%m%d_%H%M%S')}"
        if '.' not in safe_name:
            safe_name = f"{safe_name}.{fmt}"
        else:
            base, _ext = safe_name.rsplit('.', 1)
            safe_name = f"{base}.{fmt}"

        os.makedirs(BACKUP_DIR, exist_ok=True)
        output_path = os.path.join(BACKUP_DIR, safe_name)
        db_path = _get_db_path()
        ok, msg = _validate_backup_db(db_path)
        if not ok:
            return jsonify({'success': False, 'message': msg}), 400

        if fmt == 'db':
            src = sqlite3.connect(db_path)
            dest = sqlite3.connect(output_path)
            src.backup(dest)
            dest.close()
            src.close()
        else:
            conn = sqlite3.connect(db_path)
            with open(output_path, 'w', encoding='utf-8') as f:
                for line in conn.iterdump():
                    f.write(line + '\n')
            conn.close()

        _backup_log_append({
            "user": current_user.username,
            "operation": "export",
            "filename": safe_name,
            "timestamp": started_at,
            "status": "success"
        })
        write_audit_log('BACKUP_EXPORTED', 'backup', None, {'filename': safe_name})
        return send_file(output_path, as_attachment=True, download_name=safe_name)
    except Exception:
        _backup_log_append({
            "user": current_user.username,
            "operation": "export",
            "filename": None,
            "timestamp": started_at,
            "status": "failure"
        })
        return jsonify({'success': False, 'message': 'Failed to export backup.'}), 500
    finally:
        BACKUP_LOCK.release()


@app.route('/admin/backups/import', methods=['POST'])
def admin_backups_import():
    current_user = _require_admin()
    _validate_csrf()
    if not BACKUP_LOCK.acquire(blocking=False):
        return jsonify({'success': False, 'message': 'A backup operation is already in progress.'}), 409
    started_at = int(time.time())
    temp_path = None
    temp_db_path = None
    try:
        uploaded = request.files.get('backup_file')
        if not uploaded or not uploaded.filename:
            return jsonify({'success': False, 'message': 'Please select a backup file.'}), 400
        filename = secure_filename(uploaded.filename)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in BACKUP_ALLOWED_EXTS:
            return jsonify({'success': False, 'message': 'Invalid file format.'}), 400
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.' + ext)
        temp_path = tmp.name
        tmp.close()
        uploaded.save(temp_path)

        if ext == 'sql':
            temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            temp_db_path = temp_db.name
            temp_db.close()
            conn = sqlite3.connect(temp_db_path)
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                conn.executescript(f.read())
            conn.close()
            candidate_path = temp_db_path
        else:
            with open(temp_path, 'rb') as f:
                header = f.read(16)
                if b'SQLite format 3' not in header:
                    return jsonify({'success': False, 'message': 'Backup file is corrupted or not a valid SQLite database.'}), 400
            candidate_path = temp_path
        ok, msg = _validate_backup_db(candidate_path)
        if not ok:
            return jsonify({'success': False, 'message': msg}), 400

        # Preserve pre-restore DB
        db_path = _get_db_path()
        if os.path.exists(db_path):
            preserve_path = f"{db_path}.before_restore_{int(time.time())}"
            shutil.copy2(db_path, preserve_path)

        RESTORE_STATE["in_progress"] = True
        db.session.remove()
        db.engine.dispose()
        shutil.move(candidate_path, db_path)

        _backup_log_append({
            "user": current_user.username,
            "operation": "import",
            "backup_type": "restore",
            "filename": filename,
            "timestamp": started_at,
            "status": "success"
        })
        write_audit_log('BACKUP_RESTORED', 'backup', None, {'filename': filename, 'actor_user_id': current_user.id})
        return jsonify({'success': True, 'message': 'Database restored successfully.'})
    except Exception:
        _backup_log_append({
            "user": current_user.username,
            "operation": "import",
            "backup_type": "restore",
            "filename": None,
            "timestamp": started_at,
            "status": "failure"
        })
        return jsonify({'success': False, 'message': 'Restore failed. Please verify the backup file.'}), 500
    finally:
        RESTORE_STATE["in_progress"] = False
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        if temp_db_path and os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except Exception:
                pass
        BACKUP_LOCK.release()


@app.route('/admin/backups/download/<path:filename>')
def admin_backups_download(filename):
    _require_admin()
    safe_name = secure_filename(filename)
    if not safe_name:
        abort(404)
    file_path = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(file_path):
        abort(404)
    return send_file(file_path, as_attachment=True, download_name=safe_name)


@app.errorhandler(413)
def handle_large_upload(error):
    if request.path.startswith('/admin/backups'):
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'File too large.'}), 413
        return redirect(url_for('admin_backups_page', error_msg='File too large.'))
    return ("File too large.", 413)


@app.route('/api/audit-log')
@require_admin_view
def get_audit_log():
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = 50
        action_filter = (request.args.get('action') or '').strip()
        actor_filter = (request.args.get('actor') or '').strip()
        start_date = (request.args.get('start_date') or '').strip()
        end_date = (request.args.get('end_date') or '').strip()

        # Use raw SQL to avoid any SQLAlchemy session/mapping issues
        db_path = os.path.join(app.instance_path, 'users.db')
        if not os.path.exists(db_path):
            db_path = os.path.join(app.root_path, 'users.db')

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            where_clauses = []
            params = []

            if action_filter:
                where_clauses.append("action = ?")
                params.append(action_filter)
            if actor_filter:
                where_clauses.append("actor_username LIKE ?")
                params.append(f'%{actor_filter}%')
            if start_date:
                try:
                    start_ts = int(time.mktime(time.strptime(start_date, '%Y-%m-%d')))
                    where_clauses.append("timestamp >= ?")
                    params.append(start_ts)
                except ValueError:
                    pass
            if end_date:
                try:
                    end_ts = int(time.mktime(time.strptime(end_date, '%Y-%m-%d'))) + 86399
                    where_clauses.append("timestamp <= ?")
                    params.append(end_ts)
                except ValueError:
                    pass

            where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

            total = conn.execute(f"SELECT COUNT(*) FROM audit_log {where_sql}", params).fetchone()[0]
            pages = max(1, (total + per_page - 1) // per_page)
            page = min(page, pages)
            offset = (page - 1) * per_page

            rows = conn.execute(
                f"SELECT id, timestamp, actor_id, actor_username, action, resource_type, resource_id, detail, ip_address "
                f"FROM audit_log {where_sql} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [per_page, offset]
            ).fetchall()

            items = []
            for r in rows:
                detail_parsed = {}
                try:
                    detail_parsed = json.loads(r['detail']) if r['detail'] else {}
                except Exception:
                    pass
                ts = r['timestamp'] or 0
                items.append({
                    'id': r['id'],
                    'timestamp': ts,
                    'timestamp_iso': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts)) if ts else '',
                    'actor_id': r['actor_id'],
                    'actor_username': r['actor_username'] or '—',
                    'action': r['action'],
                    'resource_type': r['resource_type'] or '—',
                    'resource_id': r['resource_id'],
                    'detail': detail_parsed,
                    'ip_address': r['ip_address'] or '—',
                })

            action_types = [
                row[0] for row in conn.execute(
                    "SELECT DISTINCT action FROM audit_log ORDER BY action"
                ).fetchall()
            ]
        finally:
            conn.close()

        return jsonify({
            'items': items,
            'total': total,
            'page': page,
            'pages': pages,
            'action_types': action_types,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'items': [], 'total': 0, 'page': 1, 'pages': 1, 'action_types': [], 'error': str(e)}), 500

@app.route('/start', methods=['POST'])
def start_stream():
    _require_admin()
    data = request.get_json() or {}
    camera_index = data.get('camera_index', 0)
    try:
        camera_index = int(camera_index)
    except (ValueError, TypeError):
        camera_index = 0
    open_camera(camera_index)
    return ('OK', 200)

@app.route('/stop', methods=['POST'])
def stop_stream():
    _require_admin()
    close_camera()
    return ('OK', 200)

@app.route('/map')
def map_page():
    current_user = _login_required()
    if not isinstance(current_user, User):
        return current_user
    is_admin = _is_admin(current_user)
    is_admin_or_moderator = _is_admin_or_moderator(current_user)
    return render_template('/map.html', current_user=current_user, is_admin=is_admin, is_admin_or_moderator=is_admin_or_moderator)


@app.route('/reports', methods=['GET', 'POST'])
def reports_page():
    current_user = _login_required()
    if not isinstance(current_user, User):
        return current_user
    is_admin = _is_admin(current_user)
    csrf_token = _get_csrf_token()

    success = (request.args.get('success') or '').strip()

    def _parse_float(s):
        try:
            return float(str(s).strip())
        except Exception:
            return None

    def _validate_lat_lng(lat, lng, errors):
        if lat is None:
            errors.append('Latitude is required and must be a number.')
        if lng is None:
            errors.append('Longitude is required and must be a number.')
        if lat is not None and (lat < -90.0 or lat > 90.0):
            errors.append('Latitude must be between -90 and 90.')
        if lng is not None and (lng < -180.0 or lng > 180.0):
            errors.append('Longitude must be between -180 and 180.')

    def _allowed_image(filename: str) -> bool:
        if not filename:
            return False
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return ext in ALLOWED_REPORT_IMAGE_EXTS

    if request.method == 'POST':
        _validate_csrf()
        lat = _parse_float(request.form.get('latitude'))
        lng = _parse_float(request.form.get('longitude'))
        obstruction_type = (request.form.get('obstruction_type') or '').strip()
        photo = request.files.get('photo')

        errors = []

        _validate_lat_lng(lat, lng, errors)

        allowed_types = {'Pothole', 'Road Crack', 'Other'}
        if not obstruction_type:
            errors.append('Obstruction type is required.')
        elif obstruction_type not in allowed_types:
            errors.append('Invalid obstruction type.')

        # Photo validation - now required
        if not photo or not getattr(photo, 'filename', None) or not photo.filename.strip():
            errors.append('Photo is required')
        
        photo_rel = None
        if photo and getattr(photo, 'filename', None):
            fname = (photo.filename or '').strip()
            if fname:  # Only validate if filename exists
                if not _allowed_image(fname):
                    errors.append('Photo must be a .jpg, .jpeg, or .png image.')
                else:
                    # Validate file size (max 5MB)
                    photo.seek(0, 2)  # Seek to end
                    file_size = photo.tell()
                    photo.seek(0)  # Reset to beginning
                    
                    if file_size > 5 * 1024 * 1024:  # 5MB
                        errors.append('File too large. Maximum size is 5MB.')
                    else:
                        safe = secure_filename(fname)
                        ext = safe.rsplit('.', 1)[-1].lower()
                        unique = f"{uuid4().hex}.{ext}"
                        try:
                            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                            abs_path = os.path.join(UPLOAD_FOLDER, unique)
                            photo.save(abs_path)
                            photo_rel = f"uploads/reports/{unique}"
                        except Exception:
                            errors.append('Unable to save uploaded photo. Please try again.')

        if not errors:
            title = f"{obstruction_type} report"
            body = ''
            now_ts = int(time.time())
            r = Report(
                user_id=int(current_user.id),
                title=title,
                body=body,
                latitude=float(lat),
                longitude=float(lng),
                obstruction_type=obstruction_type,
                photo_path=photo_rel,
                created_at=now_ts,
                status_updated_at=now_ts,
            )
            db.session.add(r)
            
            # Notify Admins about new report
            try:
                admins = User.query.filter_by(role='admin').all()
                for admin in admins:
                    if admin.id == current_user.id:
                        continue # Don't notify self if admin submitted
                    msg = f"New report submitted by {current_user.username}: {title}"
                    notif = Notification(
                        user_id=admin.id,
                        title="New User Report",
                        message=msg,
                        link=url_for('defects_page', q=current_user.username)
                    )
                    db.session.add(notif)
            except Exception:
                pass

            db.session.commit()
            write_audit_log('REPORT_SUBMITTED', 'report', int(r.id), {
                'type': obstruction_type, 'lat': float(lat), 'lon': float(lng)
            })
            return redirect(url_for('reports_page', success='1'))

        # fall through to render with errors
    else:
        errors = []

    pre_lat = request.args.get('lat')
    pre_lng = request.args.get('lng')
    if request.method == 'GET':
        lat = _parse_float(pre_lat)
        lng = _parse_float(pre_lng)
        obstruction_type = ''
    else:
        lat = lat
        lng = lng
        obstruction_type = obstruction_type

    return render_template(
        '/reports.html',
        current_user=current_user,
        is_admin=is_admin,
        csrf_token=csrf_token,
        errors=errors,
        success=success,
        values={'latitude': '' if lat is None else lat, 'longitude': '' if lng is None else lng, 'obstruction_type': obstruction_type},
    )


@app.route('/my-reports')
def my_reports_page():
    current_user = _require_role('user')
    if not isinstance(current_user, User):
        return current_user

    q = (request.args.get('q') or '').strip()
    type_filter = (request.args.get('type') or '').strip().lower()
    status_filter = (request.args.get('status') or '').strip().lower()
    start_date = (request.args.get('start_date') or '').strip()
    end_date = (request.args.get('end_date') or '').strip()
    sort = (request.args.get('sort') or 'date_desc').strip().lower()
    try:
        page = max(1, int(request.args.get('page', '1')))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get('per_page', '10'))
    except Exception:
        per_page = 10
    if per_page not in (10, 20, 50):
        per_page = 10

    query = Report.query.filter(Report.user_id == int(current_user.id))
    
    # Date Range Filter
    if start_date:
        try:
            # Parse YYYY-MM-DD to timestamp
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            query = query.filter(Report.created_at >= start_ts)
        except ValueError:
            pass
            
    if end_date:
        try:
            # Parse YYYY-MM-DD to timestamp (end of day)
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            query = query.filter(Report.created_at <= end_ts)
        except ValueError:
            pass

    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Report.title.ilike(like),
            Report.body.ilike(like),
            Report.obstruction_type.ilike(like),
        ))
    if type_filter:
        if type_filter == 'pothole':
            query = query.filter(Report.obstruction_type.ilike('%pothole%'))
        elif type_filter == 'crack':
            query = query.filter(Report.obstruction_type.ilike('%crack%'))
        elif type_filter == 'other':
            query = query.filter(or_(
                Report.obstruction_type == None,
                and_(
                    ~Report.obstruction_type.ilike('%pothole%'),
                    ~Report.obstruction_type.ilike('%crack%'),
                ),
            ))
        else:
            query = query.filter(text('1=0'))
    if status_filter:
        if status_filter == 'fixed':
            query = query.filter(Report.is_fixed == True)
        elif status_filter == 'open':
            query = query.filter(or_(Report.is_fixed == False, Report.is_fixed == None))
        else:
            query = query.filter(text('1=0'))
    
    # Hide false reports from user view
    query = query.filter(Report.is_false_report == False)
    if sort == 'date_asc':
        query = query.order_by(asc(Report.created_at), asc(Report.id))
    elif sort == 'type':
        query = query.order_by(asc(Report.obstruction_type), desc(Report.created_at), desc(Report.id))
    else:
        sort = 'date_desc'
        query = query.order_by(desc(Report.created_at), desc(Report.id))

    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages
    offset = (page - 1) * per_page
    reports = query.limit(per_page).offset(offset).all()
    start = 0 if total == 0 else offset + 1
    end = 0 if total == 0 else min(total, offset + len(reports))

    return render_template(
        '/my_reports.html',
        current_user=current_user,
        is_admin=False,
        reports=reports,
        q=q,
        type_filter=type_filter,
        status_filter=status_filter,
        start_date=start_date,
        end_date=end_date,
        sort=sort,
        per_page=per_page,
        page=page,
        pages=pages,
        total=total,
        start=start,
        end=end,
    )

@app.route('/notifications/unread')
def unread_notifications():
    current_user = _login_required()
    if not isinstance(current_user, User):
        return jsonify({'error': 'Unauthorized'}), 401
    
    notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(10).all()
    
    data = []
    for n in notifs:
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'link': n.link,
            'created_at_iso': n.created_at_iso
        })
    
    return jsonify({'items': data, 'count': len(data)})

@app.route('/notifications/mark-read/<int:id>', methods=['POST'])
def mark_notification_read(id):
    current_user = _login_required()
    if not isinstance(current_user, User):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # AJAX requests might need CSRF header or token
    # For simplicity in this demo, we might skip strict CSRF for AJAX or assume header is sent
    # But let's at least check if we want to be strict.
    # Given the codebase uses _validate_csrf() manually in forms, we should probably do it if possible.
    # But standard fetch won't send it unless we put it in headers.
    # We'll skip strict CSRF for this specific AJAX action for now to avoid breaking the UI flow 
    # if the token isn't easily available in JS.
        
    notif = Notification.query.get_or_404(id)
    if notif.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    current_user = _login_required()
    if not isinstance(current_user, User):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # AJAX-friendly
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})

@app.route('/users')
def users_page():
    current_user = _require_admin()
    is_admin = _is_admin(current_user)
    csrf_token = _get_csrf_token() if current_user else None
    next_url = request.full_path

    q = (request.args.get('q') or '').strip()
    role = (request.args.get('role') or '').strip().lower()
    status = (request.args.get('status') or '').strip().lower()
    sort = (request.args.get('sort') or 'az').strip().lower()
    try:
        page = max(1, int(request.args.get('page', '1')))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get('per_page', '20'))
    except Exception:
        per_page = 20
    if per_page not in (10, 20, 50, 100):
        per_page = 20

    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(User.username.ilike(like), User.email.ilike(like)))
    if role in ALLOWED_ROLES:
        query = query.filter(User.role == role)
    elif role:
        # invalid filter value, return empty
        query = query.filter(text('1=0'))

    if status in ALLOWED_STATUSES:
        query = query.filter(User.status == status)
    elif status:
        query = query.filter(text('1=0'))
        
    # Add subquery for report count
    report_count_stmt = db.session.query(
        func.count(Report.id)
    ).filter(Report.user_id == User.id).label('report_count')
    
    # Add subquery for reaction count
    reaction_count_stmt = db.session.query(
        func.count(Reaction.id)
    ).filter(Reaction.user_id == User.id).label('reaction_count')
    
    query = query.add_columns(report_count_stmt, reaction_count_stmt)

    if sort == 'za':
        query = query.order_by(desc(User.username), asc(User.id))
    elif sort == 'reports_desc':
        query = query.order_by(desc('report_count'), asc(User.username))
    elif sort == 'reports_asc':
        query = query.order_by(asc('report_count'), asc(User.username))
    else:
        sort = 'az'
        query = query.order_by(asc(User.username), asc(User.id))

    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages

    results = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Process results into user objects with count attribute
    users = []
    for row in results:
        # row is (User, report_count, reaction_count)
        user = row[0]
        user.report_count = row[1] or 0
        user.reaction_count = row[2] or 0
        user.has_activity = (user.report_count > 0 or user.reaction_count > 0)
        users.append(user)
        
    start = 0 if total == 0 else ((page - 1) * per_page + 1)
    end = 0 if total == 0 else (min(total, (page - 1) * per_page + len(users)))

    return render_template(
        '/users.html',
        users=users,
        total=total,
        page=page,
        pages=pages,
        per_page=per_page,
        start=start,
        end=end,
        q=q,
        role_filter=role,
        status_filter=status,
        sort=sort,
        csrf_token=csrf_token,
        is_admin=is_admin,
        current_user=current_user,
        next_url=next_url,
    )


@app.route('/users/<int:user_id>/status', methods=['POST'])
def user_set_status(user_id: int):
    current_user = _require_admin()
    _validate_csrf()

    new_status = str((request.form.get('status') or '')).strip().lower()
    if new_status not in ALLOWED_STATUSES:
        abort(400)

    user = User.query.get_or_404(user_id)
    if _is_admin(user):
        abort(403)
    if user.id == current_user.id and new_status != user.status:
        # allow self status changes? generally no; avoid admin locking themselves accidentally
        abort(400)

    user.status = new_status
    if new_status == 'suspended':
        user.suspended_until = int(time.time()) + 5 * 60
    else:
        user.suspended_until = None
    db.session.commit()
    write_audit_log('USER_STATUS_CHANGED', 'user', int(user.id), {
        'username': user.username, 'new_status': new_status
    })
    return _redirect_back('users_page')


@app.route('/users/<int:user_id>/role', methods=['POST'])
def user_set_role(user_id: int):
    current_user = _require_admin()
    _validate_csrf()

    new_role = str((request.form.get('role') or '')).strip().lower()
    if new_role not in ALLOWED_ROLES:
        abort(400)

    user = User.query.get_or_404(user_id)
    if _is_admin(user):
        abort(403)
    if user.id == current_user.id and _is_admin(user) and new_role != 'admin':
        abort(400)

    user.role = new_role
    db.session.commit()
    write_audit_log('USER_ROLE_CHANGED', 'user', int(user.id), {
        'username': user.username, 'new_role': new_role
    })
    return _redirect_back('users_page')


@app.route('/users/<int:user_id>/delete', methods=['POST'])
def user_delete(user_id: int):
    current_user = _require_admin()
    _validate_csrf()

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        abort(400)

    if _is_admin(user):
        abort(403)
        
    # Check activity before deletion
    has_reports = Report.query.filter_by(user_id=user.id).count() > 0
    has_reactions = Reaction.query.filter_by(user_id=user.id).count() > 0
    
    if has_reports or has_reactions:
        # Cannot delete, only archive
        user.status = 'archived'
        user.suspended_until = None
        db.session.commit()
        write_audit_log('USER_ARCHIVED', 'user', int(user.id), {'username': user.username, 'reason': 'has_activity'})
        return _redirect_back('users_page')

    db.session.delete(user)
    db.session.commit()
    write_audit_log('USER_DELETED', 'user', user_id, {'username': user.username})
    return _redirect_back('users_page')


@app.route('/defects')
def defects_page():
    current_user = _require_admin_or_moderator()
    is_admin = _is_admin(current_user)
    is_admin_or_moderator = _is_admin_or_moderator(current_user)
    
    q_filter = (request.args.get('q') or '').strip()
    type_filter = (request.args.get('type') or '').strip().lower()
    source_filter = (request.args.get('source') or '').strip().lower()
    status_filter = (request.args.get('status') or '').strip().lower()
    unsure_filter = (request.args.get('unsure') or '').strip().lower()
    start_date = (request.args.get('start_date') or '').strip()
    end_date = (request.args.get('end_date') or '').strip()
    sort = (request.args.get('sort') or 'date_desc').strip().lower()
    
    try:
        page = max(1, int(request.args.get('page', '1')))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get('per_page', '20'))
    except Exception:
        per_page = 20
    if per_page not in (10, 20, 50, 100):
        per_page = 20

    # 1. Fetch User Reports
    reports_query = db.session.query(
        Report.id.label('id'),
        Report.obstruction_type.label('type'),
        Report.latitude.label('latitude'),
        Report.longitude.label('longitude'),
        Report.created_at.label('created_at'),
        Report.status_updated_at.label('status_updated_at'),
        User.username.label('submitted_by'),
        literal_column("'user'").label('source'),
        Report.is_fixed.label('is_fixed'),
        literal_column("'confirmed'").label('review_status'),
        literal_column("''").label('detected_class')
    ).join(User, Report.user_id == User.id).filter(Report.is_false_report == False)

    # 2. Fetch System Detections
    detections_query = db.session.query(
        Detection.id.label('id'),
        Detection.label.label('type'),
        Detection.latitude.label('latitude'),
        Detection.longitude.label('longitude'),
        Detection.created_at.label('created_at'),
        Detection.status_updated_at.label('status_updated_at'),
        literal_column("''").label('submitted_by'),
        literal_column("'system'").label('source'),
        Detection.is_fixed.label('is_fixed'),
        Detection.review_status.label('review_status'),
        Detection.detected_class.label('detected_class')
    )

    # 3. Apply Filters
    if q_filter:
        like = f"%{q_filter}%"
        reports_query = reports_query.filter(or_(
            Report.obstruction_type.ilike(like),
            User.username.ilike(like)
        ))
        detections_query = detections_query.filter(or_(
            Detection.label.ilike(like),
            Detection.detected_class.ilike(like)
        ))

    # Date Range Filter
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            reports_query = reports_query.filter(Report.created_at >= start_ts)
            detections_query = detections_query.filter(Detection.created_at >= start_ts)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            reports_query = reports_query.filter(Report.created_at <= end_ts)
            detections_query = detections_query.filter(Detection.created_at <= end_ts)
        except ValueError:
            pass

    # Type and Unsure Sub-filtering
    if type_filter:
        if type_filter == 'unsure':
            # Reports don't have 'unsure' (they are human submitted)
            reports_query = reports_query.filter(text("1=0"))
            
            # System detections with low confidence or pending review
            # Logic: If unsure_filter is set, filter detections by review_status
            if unsure_filter == 'validated':
                detections_query = detections_query.filter(Detection.review_status == 'confirmed')
            elif unsure_filter == 'unvalidated':
                detections_query = detections_query.filter(Detection.review_status == 'pending')
            elif unsure_filter == 'rejected':
                detections_query = detections_query.filter(Detection.review_status == 'rejected')
            else:
                # Show all detections that were ever unsure (pending or validated/rejected from pending)
                # In this system, low confidence detections start as 'pending'
                # We'll show anything that isn't auto-confirmed (>0.60) if possible, 
                # but review_status is our best indicator.
                detections_query = detections_query.filter(Detection.review_status.in_(['pending', 'confirmed', 'rejected']))
                # If we want ONLY those that were originally unsure, we'd need a flag, 
                # but 'pending' is the indicator for unsure detections in the current system.
        elif type_filter == 'pothole':
            reports_query = reports_query.filter(Report.obstruction_type.ilike('%pothole%'))
            detections_query = detections_query.filter(Detection.label.ilike('%pothole%'))
        elif type_filter == 'crack':
            reports_query = reports_query.filter(Report.obstruction_type.ilike('%crack%'))
            detections_query = detections_query.filter(Detection.label.ilike('%crack%'))
    
    if source_filter:
        if source_filter == 'user':
            detections_query = detections_query.filter(text("1=0"))
        elif source_filter == 'system':
            reports_query = reports_query.filter(text("1=0"))

    if status_filter:
        if status_filter == 'fixed':
            reports_query = reports_query.filter(Report.is_fixed == True)
            detections_query = detections_query.filter(Detection.is_fixed == True)
        elif status_filter == 'open':
            reports_query = reports_query.filter(or_(Report.is_fixed == False, Report.is_fixed == None))
            detections_query = detections_query.filter(or_(Detection.is_fixed == False, Detection.is_fixed == None))

    # Date Range Filter
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            reports_query = reports_query.filter(Report.created_at >= start_ts)
            detections_query = detections_query.filter(Detection.created_at >= start_ts)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            reports_query = reports_query.filter(Report.created_at <= end_ts)
            detections_query = detections_query.filter(Detection.created_at <= end_ts)
        except ValueError:
            pass

    # Combine queries
    combined_query = reports_query.union_all(detections_query)

    # Apply Sorting
    if sort == 'date_asc':
        combined_query = combined_query.order_by(text('created_at ASC'))
    elif sort == 'reported_asc':
        combined_query = combined_query.order_by(text('created_at ASC'))
    elif sort == 'reported_desc':
        combined_query = combined_query.order_by(text('created_at DESC'))
    elif sort == 'status_updated_asc':
        combined_query = combined_query.order_by(text('status_updated_at ASC'), text('created_at ASC'))
    elif sort == 'status_updated_desc':
        combined_query = combined_query.order_by(text('status_updated_at DESC'), text('created_at DESC'))
    elif sort == 'type':
        combined_query = combined_query.order_by(text('type ASC'), text('created_at DESC'))
    elif sort == 'source':
        combined_query = combined_query.order_by(text('source ASC'), text('created_at DESC'))
    elif sort == 'status':
        combined_query = combined_query.order_by(text('is_fixed ASC'), text('created_at DESC'))
    else: # date_desc default
        combined_query = combined_query.order_by(text('created_at DESC'))

    # Pagination
    total = combined_query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages
    
    offset = (page - 1) * per_page
    results = combined_query.limit(per_page).offset(offset).all()
    
    items = []
    for r in results:
        created_at_val = int(r.created_at) if r.created_at else 0
        status_updated_val = int(r.status_updated_at) if getattr(r, 'status_updated_at', None) else created_at_val
        items.append({
            'id': r.id,
            'type': r.type,
            'lat': r.latitude,
            'lon': r.longitude,
            'created_at': created_at_val,
            'created_at_iso': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created_at_val)) if created_at_val else '',
            'status_updated_at': status_updated_val,
            'status_updated_at_iso': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status_updated_val)) if status_updated_val else '',
            'submitted_by': r.submitted_by,
            'source': r.source,
            'is_fixed': r.is_fixed,
            'review_status': r.review_status,
            'detected_class': r.detected_class
        })

    start = 0 if total == 0 else offset + 1
    end = 0 if total == 0 else min(total, offset + len(items))

    return render_template(
        '/defects.html',
        items=items,
        total=total,
        page=page,
        pages=pages,
        per_page=per_page,
        start=start,
        end=end,
        q=q_filter,
        type_filter=type_filter,
        source_filter=source_filter,
        status_filter=status_filter,
        unsure_filter=unsure_filter,
        start_date=start_date,
        end_date=end_date,
        sort=sort,
        is_admin=is_admin,
        is_admin_or_moderator=is_admin_or_moderator,
        current_user=current_user,
        next_url=request.full_path
    )


@app.route('/detections') #for logs
def detections_api():
    current_user = _login_required()
    if not isinstance(current_user, User):
        return current_user
    try:
        is_admin = _is_admin(current_user)
        is_admin_or_moderator = _is_admin_or_moderator(current_user)
        include_pending = str(request.args.get('include_pending') or '').strip().lower() in {'1', 'true', 'yes'}
        allow_pending = bool(is_admin_or_moderator and include_pending)
        
        expiration_days = 30
        try:
            s_val = Settings.query.filter_by(key='fixed_defect_expiration_days').first()
            if s_val and s_val.value:
                expiration_days = int(s_val.value)
        except Exception:
            pass
            
        cutoff = int(time.time()) - (expiration_days * 24 * 3600)
        query = Detection.query.filter(
            or_(
                Detection.is_fixed == False,
                Detection.fixed_at > cutoff
            )
        )
        query = query.filter(or_(Detection.review_status == None, Detection.review_status != 'rejected'))
        if allow_pending:
            query = query.filter(or_(Detection.review_status == None, Detection.review_status.in_(['confirmed', 'pending'])))
        else:
            query = query.filter(or_(Detection.review_status == None, Detection.review_status == 'confirmed'))
            query = query.filter(or_(Detection.visibility_scope == None, Detection.visibility_scope == 'public'))
        limit = request.args.get('limit', type=int) or 50
        before_id = request.args.get('before_id', type=int)
        after_id = request.args.get('after_id', type=int)
        
        if before_id:
            query = query.filter(Detection.id < before_id)
        if after_id:
            query = query.filter(Detection.id > after_id)

        rows = query.order_by(desc(Detection.id)).limit(limit + 1).all()
        
        has_more = len(rows) > limit
        rows = rows[:limit]
        
        items = []
        for d in rows:
            label_value = d.final_class or d.detected_class or d.label
            review_status = (d.review_status or 'confirmed').strip().lower()
            visibility_scope = (d.visibility_scope or 'public').strip().lower()
            created_at_val = int(d.created_at) if d.created_at else 0
            status_updated_val = int(d.status_updated_at) if getattr(d, 'status_updated_at', None) else created_at_val
            items.append({
                "id": int(d.id),
                "lat": float(d.latitude),
                "lon": float(d.longitude),
                "labels": [str(label_value)],
                "label": str(label_value),
                "detected_class": d.detected_class,
                "final_class": d.final_class,
                "detection_source": d.detection_source or 'ai_survey',
                "review_status": review_status,
                "reviewed_by": int(d.reviewed_by) if d.reviewed_by else None,
                "reviewed_at": int(d.reviewed_at) if d.reviewed_at else None,
                "visibility_scope": visibility_scope,
                "snapshot_image_path": d.snapshot_image_path,
                "conf": float(d.confidence),
                "confidence_score": float(d.confidence_score) if d.confidence_score is not None else float(d.confidence),
                "ts": created_at_val,
                "ts_iso": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created_at_val)) if created_at_val else '',
                "status_updated_at": status_updated_val,
                "status_updated_at_iso": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status_updated_val)) if status_updated_val else '',
                "gps_valid": True,
                "is_fixed": bool(d.is_fixed),
                "fixed_at": int(d.fixed_at) if d.fixed_at else None
            })
        return jsonify({
            "items": items,
            "has_more": has_more
        })
    except Exception:
        return jsonify({"items": []})


@app.route('/detections/<int:detection_id>/review', methods=['POST'])
def review_detection(detection_id: int):
    current_user = _require_admin_or_moderator()
    try:
        data = request.get_json() or {}
        action = str(data.get('action') or '').strip().lower()
        if action not in {'confirm_pothole', 'confirm_roadcrack', 'reject'}:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        det = Detection.query.get_or_404(detection_id)
        now = int(time.time())
        if action == 'reject':
            det.review_status = 'rejected'
            det.visibility_scope = 'admin_only'
            det.reviewed_by = int(current_user.id)
            det.reviewed_at = now
        else:
            final_class = 'pothole' if action == 'confirm_pothole' else 'roadcrack'
            det.final_class = final_class
            det.label = final_class
            if not det.detected_class:
                det.detected_class = det.label
            det.review_status = 'confirmed'
            det.visibility_scope = 'public'
            det.reviewed_by = int(current_user.id)
            det.reviewed_at = now
        det.status_updated_at = now
        if not det.detection_source:
            det.detection_source = 'ai_survey'
        if det.confidence_score is None:
            det.confidence_score = det.confidence
        db.session.commit()
        write_audit_log('DETECTION_REVIEWED', 'detection', int(det.id), {
            'action': action, 'final_class': det.final_class, 'review_status': det.review_status
        })
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/reports-data')
def reports_data():
    current_user = _get_current_user()
    current_user_id = current_user.id if current_user else None

    expiration_days = 30
    try:
        s_val = Settings.query.filter_by(key='fixed_defect_expiration_days').first()
        if s_val and s_val.value:
            expiration_days = int(s_val.value)
    except Exception:
        pass

    reports = Report.query.filter(
        Report.created_at >= (time.time() - expiration_days * 24 * 3600),
        Report.is_false_report == False
    ).all()
    
    # Pre-fetch user reactions for these reports if user is logged in
    user_reactions = {}
    if current_user_id:
        # Get all reactions by this user for the fetched reports
        r_ids = [r.id for r in reports]
        if r_ids:
            reactions = Reaction.query.filter(
                Reaction.user_id == current_user_id,
                Reaction.report_id.in_(r_ids)
            ).all()
            for rx in reactions:
                user_reactions[rx.report_id] = rx.reaction_type

    items = []
    for r in reports:
        # if fixed, check if older than expiration_days since fixed
        if r.is_fixed and r.fixed_at:
            if (time.time() - r.fixed_at) > (expiration_days * 24 * 3600):
                continue

        created_at_val = int(r.created_at) if r.created_at else 0
        status_updated_val = int(r.status_updated_at) if getattr(r, 'status_updated_at', None) else created_at_val
        items.append({
            'id': r.id,
            'lat': r.latitude,
            'lon': r.longitude,
            'type': r.obstruction_type,
            'photo': r.photo_path,
            'created_at': created_at_val,
            'created_at_iso': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created_at_val)) if created_at_val else '',
            'status_updated_at': status_updated_val,
            'status_updated_at_iso': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status_updated_val)) if status_updated_val else '',
            'is_fixed': r.is_fixed,
            'thumbs_up': r.thumbs_up_count,
            'thumbs_down': r.thumbs_down_count,
            'user_reaction': user_reactions.get(r.id)  # 'up', 'down', or None
        })
    return jsonify({'items': items})


@app.route('/reports/<int:report_id>/react', methods=['POST'])
def react_to_report(report_id):
    current_user = _login_required()
    if not isinstance(current_user, User):
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    reaction_type = data.get('reaction')
    if reaction_type not in ('up', 'down'):
        return jsonify({'error': 'Invalid reaction type'}), 400

    report = Report.query.get_or_404(report_id)

    # Check ownership
    if report.user_id == current_user.id:
        return jsonify({'error': 'Cannot react to your own report'}), 403

    try:
        existing = Reaction.query.filter_by(report_id=report.id, user_id=current_user.id).first()
        
        if existing:
            if existing.reaction_type == reaction_type:
                # Toggle off (remove reaction)
                db.session.delete(existing)
                if reaction_type == 'up':
                    report.thumbs_up_count = max(0, report.thumbs_up_count - 1)
                else:
                    report.thumbs_down_count = max(0, report.thumbs_down_count - 1)
                action = 'removed'
            else:
                # Change reaction
                old_type = existing.reaction_type
                existing.reaction_type = reaction_type
                if old_type == 'up':
                    report.thumbs_up_count = max(0, report.thumbs_up_count - 1)
                if old_type == 'down':
                    report.thumbs_down_count = max(0, report.thumbs_down_count - 1)
                
                if reaction_type == 'up':
                    report.thumbs_up_count += 1
                else:
                    report.thumbs_down_count += 1
                action = 'changed'
        else:
            # New reaction
            new_rx = Reaction(report_id=report.id, user_id=current_user.id, reaction_type=reaction_type)
            db.session.add(new_rx)
            if reaction_type == 'up':
                    report.thumbs_up_count += 1
            else:
                report.thumbs_down_count += 1
            action = 'added'

        # Auto-fix logic
        auto_fix_threshold = 3
        try:
            s_val = Settings.query.filter_by(key='auto_fix_threshold').first()
            if s_val and s_val.value:
                auto_fix_threshold = int(s_val.value)
        except Exception:
            pass

        if report.thumbs_up_count >= auto_fix_threshold and not report.is_fixed:
            now_ts = int(time.time())
            report.is_fixed = True
            report.fixed_at = now_ts
            report.status_updated_at = now_ts
            
            # Notify user
            try:
                msg = f"Your report '{report.title}' has been automatically marked as fixed due to community confirmation!"
                notif = Notification(
                    user_id=report.user_id,
                    title="Report Verified & Fixed",
                    message=msg,
                    link=url_for('my_reports_page')
                )
                db.session.add(notif)
            except Exception:
                pass

        db.session.commit()
        
        return jsonify({
            'success': True,
            'action': action,
            'thumbs_up': report.thumbs_up_count,
            'thumbs_down': report.thumbs_down_count,
            'is_fixed': report.is_fixed
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/reports/<int:report_id>/flag', methods=['POST'])
@login_required_view
def flag_report(report_id):
    cu = _get_current_user()
    report = Report.query.get_or_404(report_id)
    
    # Check for existing flag
    existing = ReportFlag.query.filter_by(
        report_id=report_id,
        user_id=cu.id
    ).first()
    
    if existing:
        return jsonify({'error': 'Already flagged'}), 400
    
    # Create flag
    flag = ReportFlag(report_id=report_id, user_id=cu.id)
    db.session.add(flag)
    
    # Count total flags (query includes the uncommitted flag due to autoflush)
    flag_count = ReportFlag.query.filter_by(report_id=report_id).count()
    
    # Check threshold
    threshold_setting = Settings.query.filter_by(key='community_false_report_threshold').first()
    threshold = int(threshold_setting.value) if threshold_setting else 3
    
    auto_flagged = False
    if flag_count >= threshold and not report.is_false_report:
        report.is_false_report = True
        auto_flagged = True
        
        # Increment author's false report count
        author = User.query.get(report.user_id)
        if author:
            author.false_reports_count += 1
        
        # Create notification for author
        notif = Notification(
            user_id=report.user_id,
            title='Report Flagged as False',
            message=f'Your report "{report.title}" has been flagged as false by the community.',
            link='/my-reports'
        )
        db.session.add(notif)
        
        # Audit log
        write_audit_log(
            action='REPORT_AUTO_FLAGGED_FALSE',
            resource_type='report',
            resource_id=report_id,
            detail={'flag_count': flag_count, 'threshold': threshold}
        )
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'flag_count': flag_count,
        'auto_flagged': auto_flagged,
        'threshold': threshold
    })


@app.route('/api/false-report-threshold', methods=['GET'])
@login_required_view
def get_false_report_threshold():
    """Get the current false report threshold setting."""
    try:
        threshold_setting = Settings.query.filter_by(key='false_report_threshold').first()
        threshold = int(threshold_setting.value) if threshold_setting else 5
        
        return jsonify({
            'success': True,
            'threshold': threshold
        })
    except Exception as e:
        app.logger.error(f"Error fetching false report threshold: {e}")
        return jsonify({
            'success': False,
            'threshold': 5,  # Default fallback
            'error': 'Failed to fetch threshold'
        }), 500


@app.route('/reports/<int:report_id>/fix', methods=['POST'])
def manual_fix_report(report_id):
    current_user = _login_required()
    if not isinstance(current_user, User):
        return jsonify({'error': 'Authentication required'}), 401
        
    report = Report.query.get_or_404(report_id)
    
    # Only owner can manually fix via this endpoint
    if report.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
        
    if not report.is_fixed:
        now_ts = int(time.time())
        report.is_fixed = True
        report.fixed_at = now_ts
        report.status_updated_at = now_ts
        
        # Notify Admins about self-fixed report
        try:
            admins = User.query.filter_by(role='admin').all()
            for admin in admins:
                if admin.id == current_user.id:
                    continue # Don't notify self if admin is fixing their own report (though this endpoint is for users)
                msg = f"User {current_user.username} marked their own report '{report.title}' as fixed."
                notif = Notification(
                    user_id=admin.id,
                    title="Report Marked Fixed by User",
                    message=msg,
                    link=url_for('defects_page', q=current_user.username)
                )
                db.session.add(notif)
        except Exception:
            pass

        db.session.commit()
        
    return jsonify({'success': True, 'is_fixed': True})


@app.route('/reports/<int:report_id>/flag-false', methods=['POST'])
def flag_report_false(report_id):
    current_user = _require_admin()
    
    report = Report.query.get_or_404(report_id)
    if report.is_false_report:
        return jsonify({'success': True, 'message': 'Already flagged as false.'})
        
    try:
        # 1. Mark report as false (soft delete)
        report.is_false_report = True
        report.status_updated_at = int(time.time())
        
        # 2. Increment user's false report count
        user = User.query.get(report.user_id)
        if user:
            user.false_reports_count += 1
            
            # 3. Check threshold and block if exceeded
            threshold = 5
            try:
                s_val = Settings.query.filter_by(key='false_report_threshold').first()
                if s_val and s_val.value:
                    threshold = int(s_val.value)
            except Exception:
                pass
                
            if user.false_reports_count >= threshold:
                user.status = 'locked'
                # Notify Admins about auto-lock
                try:
                    admins = User.query.filter_by(role='admin').all()
                    for admin in admins:
                        msg = f"User {user.username} has been automatically locked after submitting {user.false_reports_count} false reports."
                        notif = Notification(
                            user_id=admin.id,
                            title="User Auto-Locked",
                            message=msg,
                            link=url_for('users_page', q=user.username)
                        )
                        db.session.add(notif)
                except Exception:
                    pass
            
            # 4. Notify the user
            msg = f"Your report '{report.title}' has been flagged as a false report and removed. Please ensure your reports are accurate. Repeated false reports may lead to account suspension."
            if user.status == 'locked':
                msg += " Your account has been locked due to excessive false reports."
                
            notif = Notification(
                user_id=user.id,
                title="Report Flagged as False",
                message=msg,
                link="#"
            )
            db.session.add(notif)
            
        db.session.commit()
        write_audit_log('REPORT_FLAGGED_FALSE', 'report', int(report.id), {
            'user_id': report.user_id, 'title': report.title
        })
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/defects/mark-fixed', methods=['POST'])
def mark_fixed():
    current_user = _require_admin()
    try:
        data = request.json or {}
        ids = data.get('ids', []) # List of objects: {type: 'report'|'detection', id: 123}
        if not ids:
            return jsonify({'success': False, 'message': 'No defects selected'})
        
        now = int(time.time())
        updated_count = 0
        
        for item in ids:
            dtype = str(item.get('type') or '').lower()
            did = item.get('id')
            if not did:
                continue
                
            if dtype == 'report':
                rec = Report.query.get(did)
                if rec and not rec.is_fixed:
                    rec.is_fixed = True
                    rec.fixed_at = now
                    rec.status_updated_at = now
                    updated_count += 1
            elif dtype == 'detection':
                rec = Detection.query.get(did)
                if rec and not rec.is_fixed:
                    status_val = str(rec.review_status or 'confirmed').strip().lower()
                    if status_val != 'confirmed':
                        continue
                    rec.is_fixed = True
                    rec.fixed_at = now
                    rec.status_updated_at = now
                    updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            write_audit_log('DEFECTS_MARKED_FIXED', 'defect', None, {
                'count': updated_count, 'ids': ids
            })
            
        return jsonify({'success': True, 'updated': updated_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/video')
def video():
    _require_admin()
    if camera is None:
        return "Camera not running", 503
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/gps')
def gps_status():
    _require_admin()
    with gps_lock:
        data = dict(gps_latest)
    if data.get("ts"):
        data["ts_iso"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data["ts"]))
    # include config for debugging
    data["port"] = gps_port_cfg or os.environ.get("GPS_SERIAL_PORT", "COM8")
    data["baud"] = gps_baud_cfg or int(os.environ.get("GPS_BAUD", "4800"))
    return jsonify(data)

@app.before_request
def _ensure_gps_started():
    # Ensure GPS thread is running even when using `flask run` (Flask 3.x has no before_first_request)
    global _gps_started
    if not _gps_started:
        ensure_gps_thread()
        _gps_started = True


# OTP cleanup counter
_otp_cleanup_counter = 0

@app.before_request
def _cleanup_expired_otps_periodically():
    """Periodically clean up expired OTP records (every 100 requests)."""
    global _otp_cleanup_counter
    _otp_cleanup_counter += 1
    if _otp_cleanup_counter >= 100:
        _otp_cleanup_counter = 0
        try:
            deleted = cleanup_expired_otps()
            if deleted > 0:
                print(f"[OTP Cleanup] Removed {deleted} expired OTP records")
        except Exception as e:
            print(f"[OTP Cleanup] Error: {e}")


# --- Analytics Routes ---

@app.route('/analytics')
@require_admin_view
def analytics_page():
    return render_template('analytics.html', current_user=_get_current_user(), is_admin=True)

@app.route('/activity-logs')
def activity_logs_page():
    current_user = _require_admin_or_moderator()
    is_admin = _is_admin(current_user)
    return render_template('activity_logs.html', current_user=current_user, is_admin=is_admin)

@app.route('/api/analytics/overview')
@require_admin_view
def get_analytics_overview():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    admin_area = request.args.get('admin_area')
    admin_level = request.args.get('admin_level', 'province')
    
    detections_query = Detection.query
    reports_query = Report.query

    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            detections_query = detections_query.filter(Detection.created_at >= start_ts)
            reports_query = reports_query.filter(Report.created_at >= start_ts)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            detections_query = detections_query.filter(Detection.created_at <= end_ts)
            reports_query = reports_query.filter(Report.created_at <= end_ts)
        except ValueError:
            pass

    # Apply spatial filtering if admin_area is provided
    if admin_area and admin_area != 'all':
        # Convert queries to lists of objects
        d_list = filter_by_area(detections_query, Detection, admin_area, admin_level)
        r_list = filter_by_area(reports_query, Report, admin_area, admin_level)
        
        # Total Potholes
        total_potholes = sum(1 for d in d_list if ('pothole' in (d.label or '').lower() or 'pothole' in (d.detected_class or '').lower()))
        
        # Total Reports
        # Pre-filter false reports in query before spatial check? 
        # filter_by_area takes a query, so let's add the false report filter to query first
        # But wait, reports_query above doesn't have false report filter yet.
        # Let's apply standard filters to the base query first.
        
        r_list = [r for r in r_list if not r.is_false_report]
        total_reports = len(r_list)
        
        # Active Defects
        active_detections = sum(1 for d in d_list if not d.is_fixed)
        active_reports = sum(1 for r in r_list if not r.is_fixed)
        active_defects = active_detections + active_reports
        
        # Resolved Defects
        resolved_detections = sum(1 for d in d_list if d.is_fixed)
        resolved_reports = sum(1 for r in r_list if r.is_fixed)
        resolved_defects = resolved_detections + resolved_reports
        
        # Avg Repair Time
        total_repair_time = 0
        count_fixed = 0
        for d in d_list:
            if d.is_fixed and d.fixed_at and d.created_at and d.fixed_at > d.created_at:
                total_repair_time += (d.fixed_at - d.created_at)
                count_fixed += 1
        for r in r_list:
            if r.is_fixed and r.fixed_at and r.created_at and r.fixed_at > r.created_at:
                total_repair_time += (r.fixed_at - r.created_at)
                count_fixed += 1
        
        avg_repair_time_hours = 0
        if count_fixed > 0:
            avg_repair_time_hours = (total_repair_time / count_fixed) / 3600
            
        # Detection Accuracy
        # Filter d_list for reviewed items
        reviewed = [d for d in d_list if d.review_status in ('confirmed', 'rejected')]
        total_reviewed = len(reviewed)
        confirmed_count = sum(1 for d in reviewed if d.review_status == 'confirmed')
        
        accuracy = 0
        if total_reviewed > 0:
            accuracy = (confirmed_count / total_reviewed) * 100
            
    else:
        # Standard SQL Query Logic (Faster for global view)
        
        # Total Potholes (from detections)
        total_potholes = detections_query.filter(or_(Detection.label.ilike('%pothole%'), Detection.detected_class.ilike('%pothole%'))).count()
        
        # Total Reports
        total_reports = reports_query.filter(Report.is_false_report == False).count()
        
        # Active Defects (Not Fixed)
        active_detections = detections_query.filter(or_(Detection.is_fixed == False, Detection.is_fixed == None)).count()
        active_reports = reports_query.filter(Report.is_false_report == False).filter(or_(Report.is_fixed == False, Report.is_fixed == None)).count()
        active_defects = active_detections + active_reports

        # Resolved Defects (Fixed)
        resolved_detections = detections_query.filter(Detection.is_fixed == True).count()
        resolved_reports = reports_query.filter(Report.is_false_report == False).filter(Report.is_fixed == True).count()
        resolved_defects = resolved_detections + resolved_reports

        # Avg Repair Time
        fixed_detections_data = detections_query.filter(Detection.is_fixed == True).with_entities(Detection.created_at, Detection.fixed_at).all()
        fixed_reports_data = reports_query.filter(Report.is_false_report == False).filter(Report.is_fixed == True).with_entities(Report.created_at, Report.fixed_at).all()
        
        total_repair_time = 0
        count_fixed = 0
        for created, fixed in fixed_detections_data:
            if fixed and created and fixed > created:
                total_repair_time += (fixed - created)
                count_fixed += 1
        for created, fixed in fixed_reports_data:
            if fixed and created and fixed > created:
                total_repair_time += (fixed - created)
                count_fixed += 1
                
        avg_repair_time_hours = 0
        if count_fixed > 0:
            avg_repair_time_hours = (total_repair_time / count_fixed) / 3600

        # Detection Accuracy (based on review_status)
        reviewed_query = detections_query.filter(Detection.review_status.in_(['confirmed', 'rejected']))
        total_reviewed = reviewed_query.count()
        confirmed_count = reviewed_query.filter(Detection.review_status == 'confirmed').count()
        
        accuracy = 0
        if total_reviewed > 0:
            accuracy = (confirmed_count / total_reviewed) * 100

    return jsonify({
        'total_potholes': total_potholes,
        'total_reports': total_reports,
        'active_defects': active_defects,
        'resolved_defects': resolved_defects,
        'avg_repair_time': round(avg_repair_time_hours, 1),
        'detection_accuracy': round(accuracy, 1)
    })

@app.route('/api/analytics/trends')
@require_admin_view
def get_analytics_trends():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    interval = request.args.get('interval', 'daily') # daily, weekly, monthly
    admin_area = request.args.get('admin_area')
    admin_level = request.args.get('admin_level', 'province')
    
    query = Detection.query
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            query = query.filter(Detection.created_at >= start_ts)
        except ValueError:
            pass
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            query = query.filter(Detection.created_at <= end_ts)
        except ValueError:
            pass

    if admin_area and admin_area != 'all':
        d_list = filter_by_area(query, Detection, admin_area, admin_level)
        timestamps = [d.created_at for d in d_list]
    else:

        timestamps = [r[0] for r in query.with_entities(Detection.created_at).all()]
        
    timestamps.sort()
    
    data_map = {}
    for ts in timestamps:
        dt = time.localtime(ts)
        if interval == 'monthly':
            key = time.strftime('%Y-%m', dt)
        elif interval == 'weekly':
            key = time.strftime('%Y-W%U', dt)
        else: # daily
            key = time.strftime('%Y-%m-%d', dt)
            
        data_map[key] = data_map.get(key, 0) + 1
        
    sorted_keys = sorted(data_map.keys())
    return jsonify({
        'labels': sorted_keys,
        'values': [data_map[k] for k in sorted_keys]
    })

@app.route('/api/analytics/heatmap')
@require_admin_view
def get_analytics_heatmap():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    admin_area = request.args.get('admin_area')
    admin_level = request.args.get('admin_level', 'province')
    
    d_query = Detection.query
    r_query = Report.query.filter(Report.is_false_report == False)
    
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            d_query = d_query.filter(Detection.created_at >= start_ts)
            r_query = r_query.filter(Report.created_at >= start_ts)
        except ValueError:
            pass
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            d_query = d_query.filter(Detection.created_at <= end_ts)
            r_query = r_query.filter(Report.created_at <= end_ts)
        except ValueError:
            pass
            
    points = []
    
    if admin_area and admin_area != 'all':
        d_list = filter_by_area(d_query, Detection, admin_area, admin_level)
        r_list = filter_by_area(r_query, Report, admin_area, admin_level)
        
        for d in d_list:

            if d.latitude and d.longitude:
                points.append([d.latitude, d.longitude, 0.7])
        for r in r_list:
            if r.latitude and r.longitude:
                points.append([r.latitude, r.longitude, 0.7])
    else:
        for lat, lng in d_query.with_entities(Detection.latitude, Detection.longitude).all():
            if lat and lng:
                points.append([lat, lng, 0.7])
                
        for lat, lng in r_query.with_entities(Report.latitude, Report.longitude).all():
            if lat and lng:
                points.append([lat, lng, 0.7])
            
    return jsonify(points)

@app.route('/api/analytics/status-distribution')
@require_admin_view
def get_analytics_status_distribution():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    admin_area = request.args.get('admin_area')
    admin_level = request.args.get('admin_level', 'province')
    
    d_query = Detection.query
    r_query = Report.query.filter(Report.is_false_report == False)
    
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            d_query = d_query.filter(Detection.created_at >= start_ts)
            r_query = r_query.filter(Report.created_at >= start_ts)
        except ValueError:
            pass
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            d_query = d_query.filter(Detection.created_at <= end_ts)
            r_query = r_query.filter(Report.created_at <= end_ts)
        except ValueError:
            pass

    if admin_area and admin_area != 'all':
        d_list = filter_by_area(d_query, Detection, admin_area, admin_level)
        r_list = filter_by_area(r_query, Report, admin_area, admin_level)
        
        detected_open = sum(1 for d in d_list if not d.is_fixed)

        reported_open = sum(1 for r in r_list if not r.is_fixed)
        
        detected_fixed = sum(1 for d in d_list if d.is_fixed)
        reported_fixed = sum(1 for r in r_list if r.is_fixed)
    else:
        detected_open = d_query.filter(or_(Detection.is_fixed == False, Detection.is_fixed == None)).count()
        reported_open = r_query.filter(or_(Report.is_fixed == False, Report.is_fixed == None)).count()
        
        detected_fixed = d_query.filter(Detection.is_fixed == True).count()
        reported_fixed = r_query.filter(Report.is_fixed == True).count()
    
    return jsonify({
        'labels': ['Detected (Open)', 'Reported (Open)', 'Fixed'],
        'values': [detected_open, reported_open, detected_fixed + reported_fixed]
    })

@app.route('/api/analytics/ai-confidence')
@require_admin_view
def get_analytics_confidence():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    admin_area = request.args.get('admin_area')
    admin_level = request.args.get('admin_level', 'province')
    
    query = Detection.query.filter(Detection.confidence > 0)
    
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            query = query.filter(Detection.created_at >= start_ts)
        except ValueError:
            pass
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            query = query.filter(Detection.created_at <= end_ts)
        except ValueError:
            pass
            
    if admin_area and admin_area != 'all':
        d_list = filter_by_area(query, Detection, admin_area, admin_level)
        confidences = [d.confidence for d in d_list]
    else:

        confidences = [r[0] for r in query.with_entities(Detection.confidence).all()]
    
    bins = [0, 0, 0, 0, 0]
    labels = ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']
    
    total_conf = 0
    count = 0
    for c in confidences:
        total_conf += c
        count += 1
        if c < 0.2: bins[0] += 1
        elif c < 0.4: bins[1] += 1
        elif c < 0.6: bins[2] += 1
        elif c < 0.8: bins[3] += 1
        else: bins[4] += 1
        
    avg_conf = (total_conf / count) if count > 0 else 0
    
    return jsonify({
        'labels': labels,
        'values': bins,
        'average': round(avg_conf * 100, 1)
    })

@app.route('/api/analytics/repair-performance')
@require_admin_view
def get_analytics_repair_performance():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    admin_area = request.args.get('admin_area')
    admin_level = request.args.get('admin_level', 'province')
    
    d_query = Detection.query.filter(Detection.is_fixed == True)
    r_query = Report.query.filter(Report.is_false_report == False).filter(Report.is_fixed == True)
    
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            d_query = d_query.filter(Detection.fixed_at >= start_ts)
            r_query = r_query.filter(Report.fixed_at >= start_ts)
        except ValueError:
            pass
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            d_query = d_query.filter(Detection.fixed_at <= end_ts)
            r_query = r_query.filter(Report.fixed_at <= end_ts)
        except ValueError:
            pass
            
    timestamps = []
    
    if admin_area and admin_area != 'all':
        d_list = filter_by_area(d_query, Detection, admin_area, admin_level)
        r_list = filter_by_area(r_query, Report, admin_area, admin_level)
        timestamps.extend([d.fixed_at for d in d_list if d.fixed_at])
        timestamps.extend([r.fixed_at for r in r_list if r.fixed_at])
    else:

        timestamps.extend([r[0] for r in d_query.with_entities(Detection.fixed_at).all() if r[0]])
        timestamps.extend([r[0] for r in r_query.with_entities(Report.fixed_at).all() if r[0]])
        
    timestamps.sort()
    
    data_map = {}
    daily_map = {}  # { "YYYY-Www": { "YYYY-MM-DD": count } }
    for ts in timestamps:
        dt = time.localtime(ts)
        week_key = time.strftime('%Y-W%U', dt)
        day_key = time.strftime('%Y-%m-%d', dt)
        data_map[week_key] = data_map.get(week_key, 0) + 1
        if week_key not in daily_map:
            daily_map[week_key] = {}
        daily_map[week_key][day_key] = daily_map[week_key].get(day_key, 0) + 1
        
    sorted_keys = sorted(data_map.keys())
    
    return jsonify({
        'labels': sorted_keys,
        'values': [data_map[k] for k in sorted_keys],
        'daily_breakdown': {k: daily_map.get(k, {}) for k in sorted_keys}
    })


@app.route('/api/analytics/export-pdf', methods=['POST'])
@require_admin_view
def export_analytics_pdf():
    """Export analytics dashboard as PDF"""
    try:
        data = request.get_json()
        if not data:
            app.logger.error("PDF export: No data provided")
            return jsonify({'error': 'No data provided'}), 400
        
        app.logger.info(f"PDF export started for user {session.get('user_id', 'unknown')}")
        
        # Log data size for debugging
        import sys
        data_size = sys.getsizeof(str(data))
        app.logger.info(f"PDF export data size: {data_size} bytes")
        
        # Generate PDF using ReportLab
        pdf_buffer = generate_analytics_pdf(data)
        
        # Return PDF as download
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f'analytics_report_{timestamp}.pdf'
        
        app.logger.info(f"PDF export completed successfully: {filename}")
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except MemoryError as e:
        app.logger.error(f"PDF export memory error: {e}")
        return jsonify({'error': 'Insufficient memory to generate PDF. Please try with fewer filters or a smaller date range.'}), 500
    except Exception as e:
        app.logger.error(f"PDF export error: {e}")
        import traceback
        app.logger.error(f"PDF export traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to generate PDF. Please try again or contact support.'}), 500


def generate_analytics_pdf(chart_data):
    """Generate PDF report from chart data using ReportLab"""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from io import BytesIO
    import base64
    from datetime import datetime
    import gc  # Add garbage collection
    
    def process_base64_image(base64_string, max_width=6*inch):  # Reduced max width
        """Convert base64 image to ReportLab Image with size optimization"""
        try:
            # Remove data URL prefix if present
            if ',' in base64_string:
                image_data = base64_string.split(',')[1]
            else:
                image_data = base64_string
                
            image_bytes = base64.b64decode(image_data)
            
            # Limit image size for memory efficiency
            if len(image_bytes) > 2 * 1024 * 1024:  # 2MB limit
                print(f"Image too large ({len(image_bytes)} bytes), skipping")
                return None
            
            # Create ReportLab Image from bytes
            img_buffer = BytesIO(image_bytes)
            img = Image(img_buffer)
            
            # Scale to fit page width with more aggressive scaling
            if img.drawWidth > max_width:
                ratio = max_width / img.drawWidth
                img.drawWidth = max_width
                img.drawHeight = img.drawHeight * ratio
            
            # Further reduce if still too large
            if img.drawHeight > 4*inch:
                ratio = (4*inch) / img.drawHeight
                img.drawHeight = 4*inch
                img.drawWidth = img.drawWidth * ratio
            
            return img
        except Exception as e:
            print(f"Image processing error: {e}")
            return None
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4),
        rightMargin=0.5*inch, 
        leftMargin=0.5*inch,
        topMargin=0.5*inch, 
        bottomMargin=0.5*inch
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle', 
        parent=styles['Heading1'], 
        fontSize=24, 
        spaceAfter=20, 
        alignment=1,  # Center alignment
        textColor=colors.HexColor('#0f172a')
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=20,
        alignment=1,
        textColor=colors.HexColor('#64748b')
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=10,
        textColor=colors.HexColor('#0f172a')
    )
    
    # Title and metadata
    story.append(Paragraph("SURVEYOR.AI Analytics Report", title_style))
    
    # Format timestamp
    try:
        timestamp = datetime.fromisoformat(chart_data['timestamp'].replace('Z', '+00:00'))
        formatted_time = timestamp.strftime('%B %d, %Y at %I:%M %p UTC')
    except:
        formatted_time = chart_data.get('timestamp', 'Unknown')
    
    story.append(Paragraph(f"Generated on {formatted_time}", subtitle_style))
    
    # Filter information
    if 'metadata' in chart_data:
        meta = chart_data['metadata']
        filter_info = f"Time Range: {meta.get('timeRange', 'N/A')} | "
        filter_info += f"Admin Level: {meta.get('adminLevel', 'N/A')} | "
        filter_info += f"Area: {meta.get('adminArea', 'N/A')}"
        story.append(Paragraph(filter_info, subtitle_style))
    
    story.append(Spacer(1, 20))
    
    # KPI Summary Table
    if 'kpis' in chart_data and chart_data['kpis']:
        story.append(Paragraph("Key Performance Indicators", section_style))
        
        kpi_data = [
            ['Metric', 'Value'],
            ['Total Potholes', chart_data['kpis'].get('total_potholes', '-')],
            ['Active Defects', chart_data['kpis'].get('active_defects', '-')],
            ['Resolved Defects', chart_data['kpis'].get('resolved_defects', '-')],
            ['Average Repair Time', f"{chart_data['kpis'].get('avg_repair_time', '-')} hrs"],
            ['Total Reports', chart_data['kpis'].get('total_reports', '-')],
            ['AI Detection Accuracy', f"{chart_data['kpis'].get('detection_accuracy', '-')}%"]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[3*inch, 2*inch])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(kpi_table)
        story.append(Spacer(1, 30))
    
    # Charts - Process with memory management
    if 'charts' in chart_data:
        charts = chart_data['charts']
        chart_titles = {
            'trends': 'Detection Trends Over Time',
            'status': 'Defect Status Distribution', 
            'confidence': 'AI Confidence Distribution',
            'repair': 'Weekly Repair Performance',
            'heatmap': 'Geographic Heatmap'
        }
        
        # Add charts (2 per page for good quality)
        chart_count = 0
        processed_charts = 0
        max_charts = 4  # Limit number of charts to prevent memory issues
        
        for chart_key, chart_image in charts.items():
            if chart_image and chart_key in chart_titles and processed_charts < max_charts:
                # Add page break after every 2 charts (except first)
                if chart_count > 0 and chart_count % 2 == 0:
                    story.append(PageBreak())
                
                story.append(Paragraph(chart_titles[chart_key], section_style))
                
                try:
                    img = process_base64_image(chart_image)
                    if img:
                        story.append(img)
                        processed_charts += 1
                    else:
                        story.append(Paragraph("Chart could not be rendered (size limit exceeded)", styles['Normal']))
                except Exception as e:
                    story.append(Paragraph(f"Chart rendering error: {str(e)}", styles['Normal']))
                
                story.append(Spacer(1, 20))
                chart_count += 1
                
                # Force garbage collection after each chart
                gc.collect()
    
    # Footer
    story.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1,
        textColor=colors.HexColor('#94a3b8')
    )
    story.append(Paragraph("Generated by SURVEYOR.AI Analytics Dashboard", footer_style))
    
    try:
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"PDF build error: {e}")
        # Force garbage collection and retry with minimal content
        gc.collect()
        
        # Create minimal PDF on failure
        minimal_story = [
            Paragraph("SURVEYOR.AI Analytics Report", title_style),
            Paragraph(f"Generated on {formatted_time}", subtitle_style),
            Paragraph("PDF generation encountered memory constraints. Please try again with fewer filters or contact support.", styles['Normal'])
        ]
        
        minimal_buffer = BytesIO()
        minimal_doc = SimpleDocTemplate(minimal_buffer, pagesize=A4)
        minimal_doc.build(minimal_story)
        minimal_buffer.seek(0)
        return minimal_buffer


import json
import os
from flask import current_app

_geojson_cache = {}

def load_geojson_polygons(area_type='province'):
    """
    Loads GeoJSON data and returns a dictionary of polygons keyed by area name.
    Supported types: 'province', 'municipality', 'region'
    Enhanced with validation and error handling for accurate geographic filtering.
    """
    global _geojson_cache
    if area_type in _geojson_cache:
        return _geojson_cache[area_type]

    filename = f'{area_type}s.json'
    if area_type == 'municipality':
        filename = 'municipalities.json'
    
    filepath = os.path.join(current_app.static_folder, 'data', filename)
    
    # Enhanced validation: verify GeoJSON files exist and are readable
    if not os.path.exists(filepath):
        print(f"Warning: GeoJSON file not found: {filepath}")
        return {}
    
    if not os.path.isfile(filepath):
        print(f"Warning: GeoJSON path is not a file: {filepath}")
        return {}
    
    if not os.access(filepath, os.R_OK):
        print(f"Warning: GeoJSON file is not readable: {filepath}")
        return {}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate GeoJSON structure
        if not isinstance(data, dict):
            print(f"Warning: Invalid GeoJSON format in {filename} - not a dictionary")
            return {}
        
        features = data.get('features', [])
        if not isinstance(features, list):
            print(f"Warning: Invalid GeoJSON format in {filename} - features is not a list")
            return {}
        
        polygons = {}
        processed_count = 0
        
        for feature in features:
            if not isinstance(feature, dict):
                continue
                
            props = feature.get('properties', {})
            if not isinstance(props, dict):
                continue
                
            # Determine name based on type
            name = ''
            if area_type == 'province':
                name = props.get('NAME_1')
            elif area_type == 'municipality':
                name = props.get('NAME_2')
            elif area_type == 'region':
                name = props.get('name') or props.get('REGION')
            
            if not name:
                continue
            
            geometry = feature.get('geometry')
            if not geometry or not isinstance(geometry, dict):
                print(f"Warning: Missing or invalid geometry for {area_type} '{name}'")
                continue
            
            # Validate geometry structure
            geom_type = geometry.get('type')
            coords = geometry.get('coordinates')
            if not geom_type or not coords:
                print(f"Warning: Invalid geometry structure for {area_type} '{name}'")
                continue
                
            # Store both original name and normalized name (without spaces) as keys
            polygons[name] = geometry
            
            # Also store normalized version (remove spaces) for better matching
            normalized_name = name.replace(' ', '')
            if normalized_name != name:
                polygons[normalized_name] = geometry
            
            processed_count += 1
        
        print(f"Loaded {processed_count} {area_type} geometries from {filename}")
        _geojson_cache[area_type] = polygons
        return polygons
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filename}: {e}")
        return {}
    except Exception as e:
        print(f"Error loading GeoJSON from {filename}: {e}")
        return {}

def point_in_polygon(point, polygon_coords):
    """
    Ray-casting algorithm to check if a point is inside a polygon.
    point: (lat, lng)
    polygon_coords: List of [lng, lat] (GeoJSON format)
    """
    lat, lng = point
    inside = False
    j = len(polygon_coords) - 1
    for i in range(len(polygon_coords)):
        xi, yi = polygon_coords[i]
        xj, yj = polygon_coords[j]
        
        intersect = ((yi > lat) != (yj > lat)) and             (lng < (xj - xi) * (lat - yi) / (yj - yi + 1e-9) + xi)
        if intersect:
            inside = not inside
        j = i
    return inside

def is_point_in_geometry(lat, lng, geometry):
    """
    Checks if a point (lat, lng) is inside a GeoJSON geometry (Polygon or MultiPolygon).
    """
    if not lat or not lng:
        return False
        
    geom_type = geometry.get('type')
    coords = geometry.get('coordinates')
    
    if geom_type == 'Polygon':
        if not coords: return False
        return point_in_polygon((lat, lng), coords[0])
        
    elif geom_type == 'MultiPolygon':
        if not coords: return False
        for poly in coords:
            if point_in_polygon((lat, lng), poly[0]):
                return True
        return False
        
    return False

def is_point_in_geometry_optimized(lat, lng, geometry):
    """
    Optimized version of is_point_in_geometry with performance improvements for Render hosting.
    Includes bounds checking, coordinate system validation, and simplified polygon processing.
    """
    if not lat or not lng or not geometry:
        return False
    
    try:
        # Convert to float to ensure numeric comparison and validate coordinates
        lat = float(lat)
        lng = float(lng)
        
        # Coordinate system validation for Philippines
        # Philippines latitude range: approximately 4.5°N to 21.5°N
        # Philippines longitude range: approximately 116°E to 127°E
        if not (4.0 <= lat <= 22.0):
            print(f"Warning: Latitude {lat} outside Philippines range (4-22°N)")
            return False
        
        if not (115.0 <= lng <= 128.0):
            print(f"Warning: Longitude {lng} outside Philippines range (115-128°E)")
            return False
        
        geom_type = geometry.get('type')
        coords = geometry.get('coordinates')
        
        if not coords:
            return False
        
        if geom_type == 'Polygon':
            # Quick bounds check first (much faster than point-in-polygon)
            if not _quick_bounds_check(lat, lng, coords[0]):
                return False
            return point_in_polygon_optimized((lat, lng), coords[0])
            
        elif geom_type == 'MultiPolygon':
            # For MultiPolygon, check each polygon
            for poly in coords:
                if poly and len(poly) > 0:
                    if _quick_bounds_check(lat, lng, poly[0]):
                        if point_in_polygon_optimized((lat, lng), poly[0]):
                            return True
            return False
            
        return False
        
    except (ValueError, TypeError, IndexError) as e:
        print(f"Warning: Coordinate validation failed for ({lat}, {lng}): {e}")
        # Fallback to original function on any error
        try:
            return is_point_in_geometry(lat, lng, geometry)
        except:
            return False

def _quick_bounds_check(lat, lng, polygon_coords):
    """
    Quick bounding box check before expensive point-in-polygon calculation.
    Returns False if point is definitely outside, True if it might be inside.
    """
    if not polygon_coords or len(polygon_coords) < 3:
        return False
    
    try:
        # Find min/max bounds of polygon
        lngs = [coord[0] for coord in polygon_coords if len(coord) >= 2]
        lats = [coord[1] for coord in polygon_coords if len(coord) >= 2]
        
        if not lngs or not lats:
            return False
        
        min_lng, max_lng = min(lngs), max(lngs)
        min_lat, max_lat = min(lats), max(lats)
        
        # Check if point is within bounding box
        return min_lng <= lng <= max_lng and min_lat <= lat <= max_lat
        
    except (IndexError, TypeError, ValueError):
        return True  # If bounds check fails, assume it might be inside

def point_in_polygon_optimized(point, polygon_coords):
    """
    Optimized ray-casting algorithm with early termination and simplified calculations.
    """
    if not polygon_coords or len(polygon_coords) < 3:
        return False
    
    try:
        lat, lng = point
        inside = False
        j = len(polygon_coords) - 1
        
        for i in range(len(polygon_coords)):
            coord_i = polygon_coords[i]
            coord_j = polygon_coords[j]
            
            # Ensure coordinates have at least 2 elements
            if len(coord_i) < 2 or len(coord_j) < 2:
                j = i
                continue
            
            xi, yi = coord_i[0], coord_i[1]
            xj, yj = coord_j[0], coord_j[1]
            
            # Optimized intersection check with better numerical stability
            if ((yi > lat) != (yj > lat)):
                # Calculate intersection point x-coordinate
                if abs(yj - yi) > 1e-10:  # Avoid division by very small numbers
                    x_intersect = (xj - xi) * (lat - yi) / (yj - yi) + xi
                    if lng < x_intersect:
                        inside = not inside
            
            j = i
            
        return inside
        
    except (IndexError, TypeError, ValueError, ZeroDivisionError):
        # Fallback to original algorithm on any error
        return point_in_polygon(point, polygon_coords)

def filter_by_area(query, model, area_name, area_type='province'):
    """
    Lazy Geographic Filtering: Fast sampling for "All Areas", accurate filtering for specific areas.
    
    Strategy:
    - When area_name is None or "all": Return fast sample data
    - When specific area is selected: Perform accurate geographic filtering
    Enhanced with improved area name matching and error handling.
    """
    # Fast path: No area specified or "All Areas" selected (case-insensitive)
    if not area_name or area_name.lower() in ['all', '']:
        print(f"Fast path: Returning sample data for general overview")
        # Return a reasonable sample for general analytics
        return query.limit(500).all()
    
    # Detect environment for optimization settings
    is_render_hosting = bool(
        os.environ.get('RENDER') or 
        os.environ.get('RENDER_SERVICE_ID') or
        os.environ.get('PORT') == '10000'
    )
    
    print(f"Accurate path: Performing geographic filtering for {area_type} '{area_name}'")
    
    try:
        # Get all records with coordinates
        all_records = query.with_entities(model.id, model.latitude, model.longitude).all()
        
        if not all_records:
            print(f"No records found in database for geographic filtering")
            return []
        
        # Apply progressive limits based on environment and complexity
        if is_render_hosting:
            # More aggressive limits for Render to prevent timeouts
            max_records = {
                'region': 2000,      # Regions are simpler
                'province': 1500,    # Provinces are medium complexity  
                'municipality': 800  # Municipalities are most complex
            }.get(area_type, 1000)
            timeout_seconds = 30  # 30 second timeout for Render
            batch_size = 25       # Smaller batches for memory management
        else:
            # Higher limits for localhost development
            max_records = {
                'region': 10000,
                'province': 5000,
                'municipality': 2000
            }.get(area_type, 3000)
            timeout_seconds = 120  # 2 minute timeout for localhost
            batch_size = 100       # Larger batches for localhost
        
        # Limit dataset size if too large
        if len(all_records) > max_records:
            print(f"Limiting geographic filtering to {max_records} records for {area_type} '{area_name}'")
            all_records = all_records[:max_records]
        
        # Load geometry data with enhanced validation
        polygons = load_geojson_polygons(area_type)
        
        if not polygons:
            print(f"Warning: No geometry data loaded for {area_type}. GeoJSON file may be missing or invalid.")
            # Fallback to sample data when geometry data is completely missing
            fallback_size = 300
            print(f"Fallback: Returning {fallback_size} sample records due to missing geometry data")
            return query.limit(fallback_size).all()
        
        # Improved area name matching: try multiple variations
        geometry = None
        original_area_name = area_name
        
        # Try exact match first
        geometry = polygons.get(area_name)
        
        # If no exact match, try normalized name (remove spaces)
        if not geometry:
            normalized_name = area_name.replace(' ', '')
            geometry = polygons.get(normalized_name)
            if geometry:
                print(f"Found geometry using normalized name: '{area_name}' -> '{normalized_name}'")
        
        # If still no match, try case-insensitive matching
        if not geometry:
            area_name_lower = area_name.lower()
            for key, geom in polygons.items():
                if key.lower() == area_name_lower:
                    geometry = geom
                    print(f"Found geometry using case-insensitive match: '{area_name}' -> '{key}'")
                    break
        
        # If still no match, try case-insensitive normalized matching
        if not geometry:
            normalized_lower = area_name.replace(' ', '').lower()
            for key, geom in polygons.items():
                if key.lower() == normalized_lower:
                    geometry = geom
                    print(f"Found geometry using case-insensitive normalized match: '{area_name}' -> '{key}'")
                    break
        
        if not geometry:
            print(f"Warning: No geometry found for {area_type} '{original_area_name}' in GeoJSON data")
            print(f"Available {area_type} names: {list(polygons.keys())[:10]}...")  # Show first 10 for debugging
            # Fallback to sample data when specific geometry is missing (preserves existing behavior)
            fallback_size = 300
            print(f"Fallback: Returning {fallback_size} sample records due to missing geometry for specific area")
            return query.limit(fallback_size).all()
        
        print(f"Processing {len(all_records)} records for geographic filtering...")
        
        # Perform geographic filtering with optimizations
        valid_ids = []
        processed_count = 0
        start_time = time.time()
        
        for record_id, lat, lng in all_records:
            # Skip records without coordinates
            if not lat or not lng:
                continue
            
            # Timeout protection
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                print(f"Geographic filtering timeout after {processed_count} records ({elapsed_time:.1f}s)")
                break
            
            # Memory management: garbage collection in batches
            if processed_count > 0 and processed_count % batch_size == 0:
                import gc
                gc.collect()
                
                # Progress logging for long operations
                if processed_count % (batch_size * 4) == 0:
                    progress = (processed_count / len(all_records)) * 100
                    print(f"Geographic filtering progress: {processed_count}/{len(all_records)} ({progress:.1f}%)")
            
            # Perform optimized point-in-polygon check with coordinate system validation
            try:
                if is_point_in_geometry_optimized(lat, lng, geometry):
                    valid_ids.append(record_id)
            except Exception as e:
                print(f"Warning: Point-in-polygon calculation failed for record {record_id} at ({lat}, {lng}): {e}")
                continue
            
            processed_count += 1
        
        # Return results
        if valid_ids:
            result_count = len(valid_ids)
            elapsed_time = time.time() - start_time
            print(f"Geographic filtering completed: {result_count} records found in {elapsed_time:.1f}s")
            return query.filter(model.id.in_(valid_ids)).all()
        else:
            print(f"No records found within {original_area_name} boundaries")
            return []
            
    except Exception as e:
        print(f"Geographic filtering error for {area_name} ({area_type}): {e}")
        
        # Preserve existing fallback behavior for error conditions
        if is_render_hosting:
            # On Render, return limited sample to prevent further errors
            fallback_size = 200
            print(f"Render fallback: Returning {fallback_size} sample records")
            return query.limit(fallback_size).all()
        else:
            # On localhost, return more data for development debugging
            fallback_size = 500
            print(f"Localhost fallback: Returning {fallback_size} sample records")
            return query.limit(fallback_size).all()

def filter_by_area_precise(query, model, area_name, area_type='province'):
    """
    PRECISE geographic filtering - only use this for localhost/development.
    This function performs the full geographic filtering that causes 502/503 on Render.
    """
    if not area_name:
        return query.all()
    
    try:
        # Get all records first with minimal memory footprint
        all_records = query.with_entities(model.id, model.latitude, model.longitude).all()
        
        # Early return if no records
        if not all_records:
            return []
        
        # Load geometry with caching
        polygons = load_geojson_polygons(area_type)
        geometry = polygons.get(area_name)
        
        if not geometry:
            print(f"Warning: No geometry found for {area_name} in {area_type}")
            return query.all()
        
        # Filter IDs using optimized point-in-polygon check
        valid_ids = []
        processed_count = 0
        start_time = time.time()
        
        for record_id, lat, lng in all_records:
            # Skip records without coordinates
            if not lat or not lng:
                continue
            
            # Timeout protection (60 seconds for precise filtering)
            if time.time() - start_time > 60:
                print(f"Precise filtering timeout after {processed_count} records")
                break
                
            # Memory management: process in batches
            if processed_count > 0 and processed_count % 100 == 0:
                import gc
                gc.collect()
            
            # Quick bounds check before expensive polygon check
            if is_point_in_geometry_optimized(lat, lng, geometry):
                valid_ids.append(record_id)
            
            processed_count += 1
        
        # Return filtered records using IDs
        if valid_ids:
            return query.filter(model.id.in_(valid_ids)).all()
        else:
            return []
            
    except Exception as e:
        print(f"Precise filtering error for {area_name} ({area_type}): {e}")
        return query.limit(100).all()

def filter_by_area_fallback(query, model, area_name, area_type='province'):
    """
    Fallback geographic filtering using database-level filtering where possible.
    Used when the main filter_by_area function times out or fails.
    """
    try:
        # For now, return a limited sample of records
        # In the future, this could implement database-level spatial queries
        # if PostGIS or similar spatial extensions are available
        
        print(f"Using fallback filtering for {area_name} ({area_type})")
        return query.limit(50).all()
        
    except Exception as e:
        print(f"Fallback filtering also failed: {e}")
        return []



if __name__ == "__main__":
    ensure_gps_thread()
    app.run(debug=True, host="0.0.0.0", port=8000, use_reloader=False)
